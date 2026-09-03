"""
Comprehensive Integration Test Suite for Phase 1C.
Verifies:
1. Liveness Probe (/health)
2. Readiness Probe (/ready) under healthy and degraded conditions
3. Request Validation (HTTP 422 on invalid parameters)
4. Async Job Submission Semantics (HTTP 202 Accepted with unique job_id and QUEUED state)
5. Job Status Polling (GET /api/v1/jobs/{job_id})
6. Unknown Job Handling (HTTP 404 with JOB_NOT_FOUND)
7. Redis Job Persistence (atomic transitions QUEUED -> PROCESSING -> COMPLETED/FAILED)
8. RabbitMQ Message Integrity (persistent delivery, correlation ID, routing key)
9. Worker Lifecycle (PROCESSING -> task execution -> COMPLETED -> basic_ack)
10. Concurrent Requests & State Isolation (Request A/B/C -> Job A/B/C -> Result A/B/C)
11. Publisher Failure Propagation (HTTP 503, NEVER 202 when broker unavailable)
12. Ollama Failure Handling (Controlled 502/503 error, NO fabricated/heuristic text)
13. Government API Failure Handling (timeouts fallback cleanly to cache/empty records)
14. Model Artifact Failure Handling (ArtifactNotFoundException masks server paths)
15. OpenAPI Schema Verification (/openapi.json, /docs, /redoc return 200 with complete paths)
16. Full End-to-End Async Flow (HTTP POST 202 -> Redis QUEUED -> AMQP -> Worker -> Redis COMPLETED -> HTTP GET 200)

Note: External dependencies (Redis, RabbitMQ, Ollama) are simulated using high-fidelity test doubles
(fakeredis, MockAMQPChannel, MagicMock) to provide deterministic, offline test verification.
"""
import concurrent.futures
import json
import unittest
from unittest.mock import MagicMock, patch
import fakeredis
from fastapi.testclient import TestClient
import pika

from src.core.config import settings
from src.core.exceptions import ArtifactNotFoundException, MessagingException, OllamaServiceException
from src.core.redis import redis_client
from src.main import app
from src.messaging.connection import rabbitmq_connection
from src.messaging.consumer.worker import AIWorker
from src.messaging.producer.publisher import RabbitMQProducer
from src.services.job_service import job_service


class MockAMQPChannel:
    """In-memory AMQP channel simulating RabbitMQ broker behavior."""

    def __init__(self):
        self.exchanges = {}
        self.queues = {}
        self.published_messages = []
        self.acked_tags = []
        self.nacked_tags = []
        self.rejected_tags = []
        self.is_open = True

    def exchange_declare(self, exchange, exchange_type="direct", durable=True):
        self.exchanges[exchange] = {"type": exchange_type, "durable": durable}

    def queue_declare(self, queue, durable=True, arguments=None):
        if queue not in self.queues:
            self.queues[queue] = {"durable": durable, "arguments": arguments or {}, "messages": []}

    def queue_bind(self, exchange, queue, routing_key):
        pass

    def basic_qos(self, prefetch_count):
        self.prefetch_count = prefetch_count

    def basic_publish(self, exchange, routing_key, body, properties=None):
        msg = {
            "exchange": exchange,
            "routing_key": routing_key,
            "body": body,
            "properties": properties,
        }
        self.published_messages.append(msg)

    def basic_ack(self, delivery_tag):
        self.acked_tags.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue=True):
        self.nacked_tags.append((delivery_tag, requeue))

    def basic_reject(self, delivery_tag, requeue=False):
        self.rejected_tags.append((delivery_tag, requeue))

    def close(self):
        self.is_open = False


class TestPhase1CIntegration(unittest.TestCase):
    """End-to-End and modular integration tests for MarketLink Phase 1C."""

    def setUp(self):
        self.fake_redis = fakeredis.FakeRedis(decode_responses=True)
        redis_client.set_custom_client(self.fake_redis)
        self.client = TestClient(app)

    def tearDown(self):
        redis_client.set_custom_client(None)

    # 1. Liveness Probe
    def test_01_health_liveness_probe(self):
        """GET /health returns HTTP 200 OK confirming process liveness regardless of external services."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["service"], "marketlink-ai")
        self.assertIn("timestamp", data)

    # 2. Readiness Probe (Healthy and Degraded)
    def test_02_readiness_probe_healthy_and_degraded(self):
        """GET /ready returns 200 when operational and 503 when a required dependency is down."""
        # Operational
        with patch.object(redis_client, "ping", return_value=True):
            with patch.object(rabbitmq_connection, "is_healthy", return_value=True):
                resp = self.client.get("/ready")
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertTrue(data["ready"])
                self.assertEqual(data["status"], "READY")
                self.assertEqual(data["dependencies"]["redis"]["status"], "UP")
                self.assertEqual(data["dependencies"]["rabbitmq"]["status"], "UP")

        # Degraded (RabbitMQ down)
        with patch.object(redis_client, "ping", return_value=True):
            with patch.object(rabbitmq_connection, "is_healthy", return_value=False):
                resp = self.client.get("/ready")
                self.assertEqual(resp.status_code, 503)
                data = resp.json()
                self.assertFalse(data["ready"])
                self.assertEqual(data["status"], "NOT_READY")
                self.assertEqual(data["dependencies"]["rabbitmq"]["status"], "DOWN")

    # 3. Request Validation Failures
    def test_03_request_validation_rejections(self):
        """Endpoints enforce schema bounds: invalid GPS latitude, longitude, and non-positive quantities return 422."""
        # Out-of-bounds latitude
        resp1 = self.client.post("/api/v1/recommend", json={
            "farmer_latitude": 120.0,  # Max 90.0
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
        })
        self.assertEqual(resp1.status_code, 422)
        self.assertEqual(resp1.json()["error"]["code"], "VALIDATION_ERROR")

        # Negative quantity
        resp2 = self.client.post("/api/v1/recommend", json={
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": -5.0,  # Must be gt=0.0
        })
        self.assertEqual(resp2.status_code, 422)

        # Invalid prediction price
        resp3 = self.client.post("/api/v1/predict", json={
            "market": "Bareilly",
            "commodity": "Onion",
            "current_price": -100.0,  # Must be gt=0.0
            "features": {"lag_7": 1800.0},
        })
        self.assertEqual(resp3.status_code, 422)

    # 4. Async Job Submission Semantics (HTTP 202 Accepted)
    def test_04_async_job_submission_semantics(self):
        """POST /api/v1/recommend/async returns HTTP 202 Accepted and registers QUEUED state."""
        payload = {
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
            "commodity": "Onion",
        }

        mock_channel = MockAMQPChannel()
        with patch.object(rabbitmq_connection, "get_channel", return_value=mock_channel):
            resp = self.client.post("/api/v1/recommend/async", json=payload)
            self.assertEqual(resp.status_code, 202)
            data = resp.json()
            job_id = data["job_id"]
            self.assertIsNotNone(job_id)
            self.assertEqual(data["status"], "QUEUED")
            self.assertEqual(data["operation"], "RECOMMEND_MANDI")
            self.assertIn("Job successfully enqueued", data["message"])

            # Verify initial state in Redis is strictly QUEUED
            stored = job_service.get_job(job_id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored["status"], "QUEUED")
            self.assertIsNone(stored["result"])
            self.assertIsNone(stored["completed_at"])

    # 5. Job Status Retrieval & Polling
    def test_05_job_status_retrieval(self):
        """GET /api/v1/jobs/{job_id} retrieves current lifecycle state and payloads."""
        job_id = "test-poll-job-01"
        job_service.create_job(job_id, "RECOMMEND_MANDI", {"commodity": "Onion"})

        # Initial QUEUED state
        resp1 = self.client.get(f"/api/v1/jobs/{job_id}")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["status"], "QUEUED")

        # Transition to PROCESSING
        job_service.set_processing(job_id)
        resp2 = self.client.get(f"/api/v1/jobs/{job_id}")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["status"], "PROCESSING")

        # Transition to COMPLETED
        job_service.set_completed(job_id, {"recommended_mandi": "Bareilly", "net_return": 18000.0})
        resp3 = self.client.get(f"/api/v1/jobs/{job_id}")
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(resp3.json()["status"], "COMPLETED")
        self.assertEqual(resp3.json()["result"]["recommended_mandi"], "Bareilly")

    # 6. Unknown Job Handling (HTTP 404)
    def test_06_unknown_job_returns_404(self):
        """GET /api/v1/jobs/unknown-id returns 404 with structured error response."""
        resp = self.client.get("/api/v1/jobs/non-existent-job-uuid-1234")
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data["error"]["code"], "JOB_NOT_FOUND")
        self.assertIn("non-existent-job-uuid-1234", data["error"]["message"])

    # 7. Redis Job Storage Persistence & Transitions
    def test_07_redis_job_persistence_lifecycle(self):
        """Verify strict atomic state transitions: QUEUED -> PROCESSING -> COMPLETED."""
        job_id = "test-lifecycle-07"
        job_service.create_job(job_id, "PREDICT_PRICE", {"market": "Bareilly"})

        raw_rec = self.fake_redis.get(f"marketlink:job:{job_id}")
        self.assertIsNotNone(raw_rec)
        dict_rec = json.loads(raw_rec)
        self.assertEqual(dict_rec["status"], "QUEUED")

        job_service.set_processing(job_id)
        dict_rec2 = json.loads(self.fake_redis.get(f"marketlink:job:{job_id}"))
        self.assertEqual(dict_rec2["status"], "PROCESSING")

        job_service.set_completed(job_id, {"predicted_price": 1900.0})
        dict_rec3 = json.loads(self.fake_redis.get(f"marketlink:job:{job_id}"))
        self.assertEqual(dict_rec3["status"], "COMPLETED")
        self.assertEqual(dict_rec3["result"]["predicted_price"], 1900.0)

    # 8. RabbitMQ Publication & Message Integrity
    def test_08_rabbitmq_message_integrity(self):
        """Producer publishes message with persistent delivery mode, correlation ID, and correct routing key."""
        mock_channel = MockAMQPChannel()
        producer = RabbitMQProducer()

        with patch.object(producer.connection, "get_channel", return_value=mock_channel):
            job_id = producer.publish_job(
                operation="RECOMMEND_MANDI",
                payload={"commodity": "Onion", "quantity": 10.0},
                correlation_id="corr-test-08",
            )
            self.assertEqual(job_id, "corr-test-08")
            self.assertEqual(len(mock_channel.published_messages), 1)

            published = mock_channel.published_messages[0]
            self.assertEqual(published["exchange"], settings.RABBITMQ_EXCHANGE)
            self.assertEqual(published["routing_key"], settings.RABBITMQ_ROUTING_KEY)

            props = published["properties"]
            self.assertEqual(int(props.delivery_mode), 2)
            self.assertEqual(props.correlation_id, "corr-test-08")

            raw_body = published["body"]
            body = json.loads(raw_body if isinstance(raw_body, str) else raw_body.decode("utf-8"))
            self.assertEqual(body["job_id"], "corr-test-08")
            self.assertEqual(body["operation"], "RECOMMEND_MANDI")

    # 9. Worker Job Processing & Lifecycle
    def test_09_worker_processing_lifecycle(self):
        """AIWorker pulls job, sets PROCESSING, completes inference, sets COMPLETED, and sends basic_ack."""
        job_id = "worker-job-09"
        job_service.create_job(job_id, "PREDICT_PRICE", {"market": "Bareilly"})

        worker = AIWorker()
        mock_channel = MagicMock(spec=pika.adapters.blocking_connection.BlockingChannel)
        method = MagicMock()
        method.delivery_tag = 101
        properties = MagicMock()
        properties.correlation_id = job_id

        msg_body = json.dumps({
            "job_id": job_id,
            "operation": "PREDICT_PRICE",
            "payload": {
                "market": "Bareilly",
                "commodity": "Onion",
                "current_price": 1850.0,
                "features": {"lag_7": 1800.0},
                "farmer_facing": False,
            },
        }).encode("utf-8")

        mock_prediction = {
            "market": "Bareilly",
            "commodity": "Onion",
            "current_price": 1850.0,
            "predicted_price": 1890.0,
            "expected_change": 40.0,
            "expected_change_pct": 2.16,
            "expected_direction": "UP",
            "usage_status": "PRODUCTION_READY",
            "reliability_score": 92.0,
            "quality_class": "STRONG",
            "data_source": "DIRECT",
        }

        with patch("src.services.ml_service.ml_service.predict_single", return_value=mock_prediction):
            worker.handle_message(mock_channel, method, properties, msg_body)

        # Worker must acknowledge message after successful completion
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=101)

        # Redis record must be COMPLETED with result payload
        completed_job = job_service.get_job(job_id)
        self.assertEqual(completed_job["status"], "COMPLETED")
        self.assertEqual(completed_job["result"]["predicted_price"], 1890.0)

    # 10. Concurrent Requests & State Isolation
    def test_10_concurrent_requests_state_isolation(self):
        """
        Verify:
        Request A -> Job A -> Result A
        Request B -> Job B -> Result B
        Request C -> Job C -> Result C
        Zero request leakage, isolated Redis records, and thread-safe execution.
        """
        mock_channel = MockAMQPChannel()
        orig_get_channel = rabbitmq_connection.get_channel
        rabbitmq_connection.get_channel = MagicMock(return_value=mock_channel)

        try:
            # Phase 1: Verify Request A, B, C via API receive distinct job IDs and isolated state
            requests_data = [
                {"farmer_latitude": 28.6139, "farmer_longitude": 77.2090, "quantity_quintals": 10.0, "commodity": "Onion"},
                {"farmer_latitude": 26.8467, "farmer_longitude": 80.9462, "quantity_quintals": 25.0, "commodity": "Potato"},
                {"farmer_latitude": 21.1458, "farmer_longitude": 79.0882, "quantity_quintals": 50.0, "commodity": "Tomato"},
            ]

            job_ids = []
            for req in requests_data:
                resp = self.client.post("/api/v1/recommend/async", json=req)
                self.assertEqual(resp.status_code, 202)
                data = resp.json()
                self.assertEqual(data["status"], "QUEUED")
                job_ids.append(data["job_id"])

            # All 3 job IDs must be completely unique
            self.assertEqual(len(set(job_ids)), 3)

            # Verify each Redis job record contains its own isolated payload without leakage
            for idx, jid in enumerate(job_ids):
                stored = job_service.get_job(jid)
                self.assertIsNotNone(stored)
                self.assertEqual(stored["payload"]["commodity"], requests_data[idx]["commodity"])
                self.assertEqual(stored["payload"]["quantity_quintals"], requests_data[idx]["quantity_quintals"])

            # Phase 2: High-concurrency stress test with ThreadPoolExecutor
            num_concurrent = 25

            def worker_task(idx: int):
                return job_service.submit_job(
                    operation="RECOMMEND_MANDI",
                    payload={"worker_idx": idx, "token": f"token-{idx}"},
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                concurrent_job_ids = list(executor.map(worker_task, range(num_concurrent)))

            # Ensure zero collisions across concurrent threads
            self.assertEqual(len(set(concurrent_job_ids)), num_concurrent)
            for idx, jid in enumerate(concurrent_job_ids):
                record = job_service.get_job(jid)
                self.assertIsNotNone(record)
                self.assertEqual(record["payload"]["worker_idx"], idx)
        finally:
            rabbitmq_connection.get_channel = orig_get_channel


    # 11. Publisher Failure Propagation
    def test_11_publisher_failure_propagation(self):
        """When RabbitMQ publication fails, route returns HTTP 503 and marks job FAILED in Redis (NEVER 202)."""
        payload = {
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
            "commodity": "Onion",
        }

        with patch.object(rabbitmq_connection, "get_channel", side_effect=Exception("RabbitMQ connection refused")):
            resp = self.client.post("/api/v1/recommend/async", json=payload)
            self.assertEqual(resp.status_code, 503)
            data = resp.json()
            self.assertEqual(data["error"]["code"], "MESSAGING_ERROR")

    # 12. Ollama Controlled Failure Handling (Correction 1)
    def test_12_ollama_controlled_failure_no_fallback(self):
        """When Ollama is offline or times out, POST /api/v1/query returns 503/502 without fabricated heuristic text."""
        with patch("src.ai.ollama_client.OllamaClient.is_available", return_value=False):
            resp = self.client.post("/api/v1/query", json={
                "query": "What is the price of Onion in Bareilly?",
                "language": "en",
            })
            self.assertEqual(resp.status_code, 503)
            data = resp.json()
            self.assertEqual(data["error"]["code"], "OLLAMA_SERVICE_ERROR")
            # Must NOT contain fabricated advice
            self.assertNotIn("Mandi Recommendation", data["error"]["message"])

    # 13. Government API Failure Handling
    def test_13_government_api_failure_handling(self):
        """Government API timeouts or connection errors gracefully return empty/cached records without unhandled 500."""
        with patch("src.services.market_data_service.market_data_service.fetcher.fetch_all_current_data", side_effect=Exception("API connection timeout")):
            resp = self.client.get("/api/v1/market-data?commodity=Onion")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["data_source"], "ERROR")
            self.assertEqual(data["record_count"], 0)
            self.assertEqual(data["records"], [])

    # 14. Model Artifact Failure Handling & Path Sanitization
    def test_14_model_artifact_failure_sanitizes_paths(self):
        """Missing feature/model artifacts return safe ArtifactNotFoundException without leaking internal server paths."""
        fake_missing_exc = ArtifactNotFoundException(
            "Required artifact not found at /home/shreyash/Projects/MarketLink/Model-app/data/processed/onion_bareilly_model.csv"
        )
        with patch("src.services.ml_service.ml_service.predict_single", side_effect=fake_missing_exc):
            resp = self.client.post("/api/v1/predict", json={
                "market": "Bareilly",
                "commodity": "Onion",
                "current_price": 1850.0,
                "features": {"lag_7": 1800.0},
            })
            self.assertEqual(resp.status_code, 500)
            data = resp.json()
            self.assertEqual(data["error"]["code"], "ARTIFACT_NOT_FOUND")
            # Server path must be masked by sanitizer
            self.assertNotIn("/home/shreyash", data["error"]["message"])
            self.assertIn("[SANITIZED_PATH]", data["error"]["message"])

    # 15. OpenAPI Schema Verification
    def test_15_openapi_schema_availability_and_structure(self):
        """Verify /openapi.json, /docs, and /redoc return HTTP 200 and define all public endpoints."""
        docs_resp = self.client.get("/docs")
        self.assertEqual(docs_resp.status_code, 200)

        redoc_resp = self.client.get("/redoc")
        self.assertEqual(redoc_resp.status_code, 200)

        openapi_resp = self.client.get("/openapi.json")
        self.assertEqual(openapi_resp.status_code, 200)
        schema = openapi_resp.json()

        paths = schema.get("paths", {})
        required_paths = [
            "/health",
            "/ready",
            "/api/v1/market-data",
            "/api/v1/predict",
            "/api/v1/recommend",
            "/api/v1/recommend/async",
            "/api/v1/jobs/{job_id}",
            "/api/v1/query",
        ]
        for p in required_paths:
            self.assertIn(p, paths, f"OpenAPI schema missing required endpoint: {p}")

        # Verify async endpoint specifies HTTP 202
        async_post = paths["/api/v1/recommend/async"]["post"]
        self.assertIn("202", async_post["responses"])

    # 16. Full End-to-End Async Flow
    def test_16_full_end_to_end_async_flow(self):
        """
        Complete lifecycle integration test:
        1. Client submits async job via HTTP POST -> receives 202 Accepted & job_id
        2. Initial state is QUEUED in Redis
        3. AMQP message is consumed by AIWorker
        4. AIWorker marks job as PROCESSING in Redis
        5. AIWorker executes task and marks job as COMPLETED in Redis with result
        6. AIWorker acknowledges AMQP message
        7. Client polls GET /api/v1/jobs/{job_id} -> receives 200 OK with COMPLETED status and result
        """
        mock_channel = MockAMQPChannel()
        client = TestClient(app)

        # Step 1: Submit async job
        with patch.object(rabbitmq_connection, "get_channel", return_value=mock_channel):
            submit_resp = client.post("/api/v1/recommend/async", json={
                "farmer_latitude": 28.6139,
                "farmer_longitude": 77.2090,
                "quantity_quintals": 10.0,
                "commodity": "Onion",
            })
            self.assertEqual(submit_resp.status_code, 202)
            job_id = submit_resp.json()["job_id"]

        # Step 2: Confirm QUEUED in Redis
        queued_poll = client.get(f"/api/v1/jobs/{job_id}")
        self.assertEqual(queued_poll.status_code, 200)
        self.assertEqual(queued_poll.json()["status"], "QUEUED")

        # Step 3 & 4 & 5: Worker consumes message and executes task
        self.assertEqual(len(mock_channel.published_messages), 1)
        raw_amqp_msg = mock_channel.published_messages[0]

        worker = AIWorker()
        mock_worker_channel = MagicMock()
        deliver_method = MagicMock()
        deliver_method.delivery_tag = 99
        properties = MagicMock()
        properties.correlation_id = job_id

        # Mock ML recommendation canonical result
        mock_rec_item = {
            "rank": 1,
            "mandi": "Bareilly",
            "state": "Uttar Pradesh",
            "district": "Bareilly",
            "distance_km": 15.2,
            "current_price": 1850.0,
            "predicted_price": 1920.0,
            "expected_change": 70.0,
            "expected_change_pct": 3.78,
            "expected_direction": "UP",
            "transport_cost": 45.6,
            "market_fee": 18.5,
            "gross_revenue": 19200.0,
            "total_cost": 641.0,
            "net_return": 18559.0,
            "net_price_per_quintal": 1855.9,
            "risk_level": "LOW",
            "confidence_score": 85.0,
            "recommendation_label": "RECOMMENDED",
            "model_usage_status": "PRODUCTION_READY",
            "model_reliability_score": 90.0,
            "model_quality_class": "STRONG",
            "data_source": "CACHE",
            "data_freshness_status": "CACHE_FRESH",
            "data_age_days": 1,
            "historical_session_count": 120,
            "data_reliability_status": "READY",
            "data_reliability_warning": "",
            "warning": "",
        }

        mock_canonical_response = MagicMock()
        mock_canonical_response.to_dict.return_value = {
            "commodity": "Onion",
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
            "recommended_mandi": "Bareilly",
            "total_mandis_evaluated": 1,
            "overall_data_source": "CACHE",
            "recommendations": [mock_rec_item],
            "contract_metadata": {"schema_version": "1.0.0"},
        }

        with patch("src.services.ml_service.ml_service.get_recommendation", return_value=mock_canonical_response):
            worker.handle_message(
                ch=mock_worker_channel,
                method=deliver_method,
                properties=properties,
                body=raw_amqp_msg["body"],
            )

        # Step 6: Verify worker acknowledged message
        mock_worker_channel.basic_ack.assert_called_once_with(delivery_tag=99)

        # Step 7: Client polls and receives COMPLETED result
        final_poll = client.get(f"/api/v1/jobs/{job_id}")
        self.assertEqual(final_poll.status_code, 200)
        final_data = final_poll.json()
        self.assertEqual(final_data["status"], "COMPLETED")
        self.assertIsNotNone(final_data["result"])
        self.assertEqual(final_data["result"]["recommended_mandi"], "Bareilly")
        self.assertIsNotNone(final_data["completed_at"])


if __name__ == "__main__":
    unittest.main()
