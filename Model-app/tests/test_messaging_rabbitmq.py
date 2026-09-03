"""
RabbitMQ Messaging Test Suite.
Tests message envelope formatting, publishing, consumption, ACK/NACK, retries, and DLQ routing.
Uses high-fidelity in-memory AMQP mock adapter and fakeredis for deterministic offline execution.
"""
import json
from unittest.mock import MagicMock, patch
import pytest
import fakeredis
from fastapi.testclient import TestClient

from src.contracts.inference_contract import (
    CanonicalInferenceItem,
    CanonicalRecommendationResponse,
    ContractMetadata,
)
from src.core.exceptions import InvalidInputException
from src.core.redis import redis_client
from src.main import app
from src.messaging.connection import rabbitmq_connection
from src.messaging.consumer.worker import AIWorker
from src.messaging.producer.publisher import RabbitMQProducer
from src.services.job_service import job_service

client = TestClient(app)


class MockAMQPChannel:
    """In-memory AMQP channel simulating RabbitMQ broker behavior."""

    def __init__(self):
        self.exchanges = {}
        self.queues = {}
        self.bindings = []
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
        self.bindings.append((exchange, queue, routing_key))

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
        if routing_key in self.queues:
            self.queues[routing_key]["messages"].append(msg)

    def basic_ack(self, delivery_tag):
        self.acked_tags.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue=True):
        self.nacked_tags.append((delivery_tag, requeue))

    def basic_reject(self, delivery_tag, requeue=False):
        self.rejected_tags.append((delivery_tag, requeue))

    def close(self):
        self.is_open = False


@pytest.fixture(autouse=True)
def setup_redis_and_amqp():
    """Setup clean fakeredis instance per test."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    redis_client.set_custom_client(fake_redis)
    yield
    redis_client.set_custom_client(None)


def test_producer_publishes_durable_message_and_registers_in_redis():
    """Producer publishes JSON message with persistent delivery mode and registers QUEUED in Redis."""
    mock_channel = MockAMQPChannel()
    producer = RabbitMQProducer()

    with patch.object(producer.connection, "get_channel", return_value=mock_channel):
        payload = {
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
            "commodity": "Onion",
        }
        job_id = producer.publish_job(
            operation="RECOMMEND_MANDI",
            payload=payload,
            correlation_id="job-producer-01",
        )

        assert job_id == "job-producer-01"
        assert len(mock_channel.published_messages) == 1

        pub = mock_channel.published_messages[0]
        assert pub["exchange"] == "marketlink.ai.exchange"
        assert pub["routing_key"] == "ai.job.request"

        body = json.loads(pub["body"])
        assert body["job_id"] == "job-producer-01"
        assert body["operation"] == "RECOMMEND_MANDI"
        assert body["payload"]["commodity"] == "Onion"

        # Verify initial job state in Redis is QUEUED
        job = job_service.get_job("job-producer-01")
        assert job is not None
        assert job["status"] == "QUEUED"
        assert job["operation"] == "RECOMMEND_MANDI"


def test_worker_processes_recommendation_and_updates_redis():
    """Worker consumes message, invokes ML recommendation, and updates Redis to COMPLETED."""
    worker = AIWorker()
    mock_channel = MockAMQPChannel()

    job_id = "job-worker-01"
    job_service.create_job(job_id=job_id, operation="RECOMMEND_MANDI")

    msg_body = {
        "job_id": job_id,
        "operation": "RECOMMEND_MANDI",
        "payload": {
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
            "commodity": "Onion",
        },
        "retry_count": 0,
    }

    mock_canonical = CanonicalRecommendationResponse(
        contract_metadata=ContractMetadata(
            schema_version="1.0.0",
            generated_at="2026-09-03T12:00:00Z",
        ),
        commodity="Onion",
        farmer_latitude=28.6139,
        farmer_longitude=77.2090,
        quantity_quintals=10.0,
        recommended_mandi="Bareilly",
        total_mandis_evaluated=1,
        overall_data_source="CACHE",
        recommendations=[
            CanonicalInferenceItem(
                rank=1,
                mandi="Bareilly",
                state="Uttar Pradesh",
                district="Bareilly",
                distance_km=215.4,
                current_price=1850.0,
                predicted_price=1900.0,
                expected_change=50.0,
                expected_change_pct=2.7,
                expected_direction="UP",
                transport_cost=6462.0,
                market_fee=370.0,
                gross_revenue=19000.0,
                total_cost=6832.0,
                net_return=12168.0,
                net_price_per_quintal=1216.8,
                confidence_score=78.5,
                risk_level="MEDIUM",
                recommendation_label="RECOMMENDED",
                model_usage_status="USABLE_WITH_WARNING",
                model_reliability_score=78.5,
                model_quality_class="ACCEPTABLE",
                data_freshness_status="STALE_CACHE",
                data_age_days=1,
                historical_session_count=100,
                data_reliability_status="ACCEPTABLE",
            )
        ],
    )

    with patch("src.services.ml_service.ml_service.get_recommendation", return_value=mock_canonical):
        deliver = MagicMock()
        deliver.delivery_tag = 101
        props = MagicMock()
        props.correlation_id = job_id

        worker.handle_message(
            ch=mock_channel,
            method=deliver,
            properties=props,
            body=json.dumps(msg_body).encode("utf-8"),
        )

        assert 101 in mock_channel.acked_tags

        # Verify Redis state
        job = job_service.get_job(job_id)
        assert job["status"] == "COMPLETED"
        assert job["result"]["recommended_mandi"] == "Bareilly"


def test_worker_handles_validation_error_and_routes_to_dlq():
    """Worker captures input validation failure, records FAILED in Redis, and rejects message to DLQ."""
    worker = AIWorker()
    mock_channel = MockAMQPChannel()

    job_id = "job-worker-fail"
    job_service.create_job(job_id=job_id, operation="RECOMMEND_MANDI")

    msg_body = {
        "job_id": job_id,
        "operation": "RECOMMEND_MANDI",
        "payload": {
            "farmer_latitude": 999.0,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
        },
        "retry_count": 0,
    }

    with patch("src.services.ml_service.ml_service.get_recommendation", side_effect=InvalidInputException("Bad coords")):
        deliver = MagicMock()
        deliver.delivery_tag = 102
        props = MagicMock()
        props.correlation_id = job_id

        worker.handle_message(
            ch=mock_channel,
            method=deliver,
            properties=props,
            body=json.dumps(msg_body).encode("utf-8"),
        )

        assert (102, False) in mock_channel.rejected_tags

        job = job_service.get_job(job_id)
        assert job["status"] == "FAILED"
        assert "Bad coords" in job["error"]["message"]


def test_worker_retries_transient_failures_and_routes_to_dlq_when_exhausted():
    """Worker retries transient errors up to MAX_RETRIES, then marks FAILED in Redis and routes to DLQ."""
    worker = AIWorker()
    mock_channel = MockAMQPChannel()

    job_id = "job-transient-01"
    job_service.create_job(job_id=job_id, operation="RECOMMEND_MANDI")

    # Retry count 0 -> should republish with retry_count 1 and ACK initial
    msg_body = {
        "job_id": job_id,
        "operation": "RECOMMEND_MANDI",
        "payload": {"farmer_latitude": 28.61, "farmer_longitude": 77.20, "quantity_quintals": 10.0},
        "retry_count": 0,
    }

    with patch("src.services.ml_service.ml_service.get_recommendation", side_effect=RuntimeError("Transient network timeout")):
        with patch("time.sleep", return_value=None):
            deliver = MagicMock()
            deliver.delivery_tag = 201
            props = MagicMock()
            props.correlation_id = job_id

            worker.handle_message(
                ch=mock_channel,
                method=deliver,
                properties=props,
                body=json.dumps(msg_body).encode("utf-8"),
            )

            # Check that message was republished with incremented retry count
            assert len(mock_channel.published_messages) == 1
            retried_body = json.loads(mock_channel.published_messages[0]["body"])
            assert retried_body["retry_count"] == 1
            assert 201 in mock_channel.acked_tags

    # Now simulate retry_count = MAX_RETRIES (3) -> should route to DLQ
    msg_body_exhausted = {
        "job_id": job_id,
        "operation": "RECOMMEND_MANDI",
        "payload": {"farmer_latitude": 28.61, "farmer_longitude": 77.20, "quantity_quintals": 10.0},
        "retry_count": 3,
    }

    with patch("src.services.ml_service.ml_service.get_recommendation", side_effect=RuntimeError("Persistent timeout")):
        deliver = MagicMock()
        deliver.delivery_tag = 202
        props = MagicMock()
        props.correlation_id = job_id

        worker.handle_message(
            ch=mock_channel,
            method=deliver,
            properties=props,
            body=json.dumps(msg_body_exhausted).encode("utf-8"),
        )

        # Should reject to DLQ
        assert (202, False) in mock_channel.rejected_tags

        job = job_service.get_job(job_id)
        assert job["status"] == "FAILED"
        assert "attempts" in job["error"]["message"].lower()
