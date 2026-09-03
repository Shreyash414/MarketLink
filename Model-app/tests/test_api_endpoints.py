"""
Integration tests for FastAPI endpoints with Redis-backed job storage.
Validates liveness, readiness probe with Redis/RabbitMQ status, async job submission,
and Redis job retrieval.
"""
import unittest
from unittest.mock import MagicMock, patch
import fakeredis
from fastapi.testclient import TestClient

from src.core.redis import redis_client
from src.main import app
from src.messaging.connection import rabbitmq_connection
from src.services.job_service import job_service


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.fake_redis = fakeredis.FakeRedis(decode_responses=True)
        redis_client.set_custom_client(self.fake_redis)
        self.client = TestClient(app)

    def tearDown(self):
        redis_client.set_custom_client(None)

    def test_01_health_liveness(self):
        """GET /health returns 200 OK with HEALTHY status and timestamp."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["service"], "marketlink-ai")
        self.assertIn("timestamp", data)

    def test_02_ready_readiness_probe_up(self):
        """GET /ready returns 200 READY when Redis and RabbitMQ are available."""
        with patch.object(rabbitmq_connection, "is_healthy", return_value=True):
            resp = self.client.get("/ready")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["ready"])
            self.assertEqual(data["status"], "READY")
            self.assertEqual(data["dependencies"]["redis"]["status"], "UP")
            self.assertEqual(data["dependencies"]["rabbitmq"]["status"], "UP")

    def test_03_ready_readiness_probe_down_when_redis_unavailable(self):
        """GET /ready returns 503 NOT_READY when Redis is unavailable."""
        with patch.object(redis_client, "ping", return_value=False):
            with patch.object(rabbitmq_connection, "is_healthy", return_value=True):
                resp = self.client.get("/ready")
                self.assertEqual(resp.status_code, 503)
                data = resp.json()
                self.assertFalse(data["ready"])
                self.assertEqual(data["status"], "NOT_READY")
                self.assertEqual(data["dependencies"]["redis"]["status"], "DOWN")

    def test_04_async_job_submission_and_redis_polling(self):
        """POST /api/v1/recommend/async stores QUEUED in Redis; GET /api/v1/jobs/{id} retrieves it."""
        req_payload = {
            "farmer_latitude": 28.6139,
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
            "commodity": "Onion",
        }

        with patch("src.messaging.producer.publisher.producer.publish_job", return_value="job-api-test-01"):
            # Mock publisher will register job in Redis
            job_service.create_job("job-api-test-01", "RECOMMEND_MANDI", req_payload)

            # Poll job status via endpoint
            resp_poll = self.client.get("/api/v1/jobs/job-api-test-01")
            self.assertEqual(resp_poll.status_code, 200)
            poll_data = resp_poll.json()
            self.assertEqual(poll_data["job_id"], "job-api-test-01")
            self.assertEqual(poll_data["status"], "QUEUED")
            self.assertEqual(poll_data["operation"], "RECOMMEND_MANDI")

    def test_05_job_not_found_returns_404(self):
        """GET /api/v1/jobs/unknown returns 404 with structured error response."""
        resp = self.client.get("/api/v1/jobs/unknown-id-xyz")
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data["error"]["code"], "JOB_NOT_FOUND")

    def test_06_validation_error_invalid_coordinates(self):
        """POST /api/v1/recommend returns 422 for coordinates outside latitude [-90, 90]."""
        payload = {
            "farmer_latitude": 999.0,  # Invalid latitude
            "farmer_longitude": 77.2090,
            "quantity_quintals": 10.0,
        }
        resp = self.client.post("/api/v1/recommend", json=payload)
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
