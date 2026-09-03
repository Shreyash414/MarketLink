"""
Unit tests for RedisJobRepository.
Validates CRUD operations, TTL enforcement, namespaced keys, JSON serialization, and error handling.
"""
import json
import unittest
from unittest.mock import MagicMock
import fakeredis
import redis

from src.core.exceptions import RedisStorageException
from src.core.redis import RedisClient
from src.repositories.redis_job_repository import RedisJobRepository


class TestRedisJobRepository(unittest.TestCase):

    def setUp(self):
        # Use isolated fake Redis client per test
        self.fake_redis = fakeredis.FakeRedis(decode_responses=True)
        self.mock_client_provider = MagicMock(spec=RedisClient)
        self.mock_client_provider.get_client.return_value = self.fake_redis
        self.ttl = 3600  # 1 hour
        self.repo = RedisJobRepository(client_provider=self.mock_client_provider, ttl_seconds=self.ttl)

    def test_01_create_and_retrieve_job(self):
        """Job is persisted under namespaced key and accurately retrieved."""
        job_data = {
            "job_id": "job-1001",
            "status": "QUEUED",
            "operation": "RECOMMEND_MANDI",
            "payload": {"commodity": "Onion", "quantity": 10.0},
            "created_at": "2026-09-03T12:00:00Z",
        }
        res = self.repo.create_job(job_data)
        self.assertEqual(res["job_id"], "job-1001")

        # Verify key format: marketlink:job:job-1001
        self.assertTrue(self.fake_redis.exists("marketlink:job:job-1001"))

        retrieved = self.repo.get_job("job-1001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["status"], "QUEUED")
        self.assertEqual(retrieved["operation"], "RECOMMEND_MANDI")
        self.assertEqual(retrieved["payload"]["commodity"], "Onion")

    def test_02_update_job_status(self):
        """Updating status preserves other fields and updates status."""
        job_data = {
            "job_id": "job-1002",
            "status": "QUEUED",
            "operation": "PREDICT_PRICE",
            "payload": {"market": "Bareilly"},
            "created_at": "2026-09-03T12:00:00Z",
        }
        self.repo.create_job(job_data)

        updated = self.repo.update_job("job-1002", {"status": "PROCESSING", "updated_at": "2026-09-03T12:01:00Z"})
        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "PROCESSING")
        self.assertEqual(updated["payload"]["market"], "Bareilly")

        retrieved = self.repo.get_job("job-1002")
        self.assertEqual(retrieved["status"], "PROCESSING")

    def test_03_store_result_and_ttl(self):
        """Completing a job stores results and sets TTL expiration."""
        job_data = {
            "job_id": "job-1003",
            "status": "PROCESSING",
            "operation": "RECOMMEND_MANDI",
            "created_at": "2026-09-03T12:00:00Z",
        }
        self.repo.create_job(job_data)

        # Before completion, TTL should be -1 (no expiration)
        self.assertEqual(self.fake_redis.ttl("marketlink:job:job-1003"), -1)

        result_payload = {"recommended_mandi": "Bareilly", "net_return": 18500.0}
        updated = self.repo.update_job(
            "job-1003",
            {"status": "COMPLETED", "result": result_payload, "completed_at": "2026-09-03T12:02:00Z"},
        )
        self.assertEqual(updated["status"], "COMPLETED")
        self.assertEqual(updated["result"]["recommended_mandi"], "Bareilly")

        # After completion, TTL must be applied
        key_ttl = self.fake_redis.ttl("marketlink:job:job-1003")
        self.assertGreater(key_ttl, 0)
        self.assertLessEqual(key_ttl, self.ttl)

    def test_04_store_failure_and_ttl(self):
        """Failing a job stores error details and sets TTL expiration."""
        job_data = {
            "job_id": "job-1004",
            "status": "PROCESSING",
            "operation": "RECOMMEND_MANDI",
            "created_at": "2026-09-03T12:00:00Z",
        }
        self.repo.create_job(job_data)

        error_payload = {"message": "Invalid coordinates", "code": "INVALID_INPUT"}
        updated = self.repo.update_job(
            "job-1004",
            {"status": "FAILED", "error": error_payload, "completed_at": "2026-09-03T12:02:00Z"},
        )
        self.assertEqual(updated["status"], "FAILED")
        self.assertEqual(updated["error"]["message"], "Invalid coordinates")

        key_ttl = self.fake_redis.ttl("marketlink:job:job-1004")
        self.assertGreater(key_ttl, 0)
        self.assertLessEqual(key_ttl, self.ttl)

    def test_05_missing_job_returns_none(self):
        """Querying a non-existent job returns None without throwing errors."""
        self.assertIsNone(self.repo.get_job("non-existent-id"))
        self.assertFalse(self.repo.job_exists("non-existent-id"))

    def test_06_delete_job(self):
        """Deleting an existing job removes key and returns True."""
        job_data = {"job_id": "job-1006", "status": "QUEUED"}
        self.repo.create_job(job_data)
        self.assertTrue(self.repo.job_exists("job-1006"))

        deleted = self.repo.delete_job("job-1006")
        self.assertTrue(deleted)
        self.assertFalse(self.repo.job_exists("job-1006"))
        self.assertFalse(self.repo.delete_job("job-1006"))  # Second delete returns False

    def test_07_job_exists(self):
        """job_exists accurately reflects Redis presence."""
        self.assertFalse(self.repo.job_exists("job-1007"))
        self.repo.create_job({"job_id": "job-1007", "status": "QUEUED"})
        self.assertTrue(self.repo.job_exists("job-1007"))

    def test_08_safe_json_serialization(self):
        """Complex nested dictionaries and numbers serialize without data loss."""
        complex_payload = {
            "job_id": "job-1008",
            "status": "QUEUED",
            "nested": {
                "recommendations": [
                    {"mandi": "Agra", "price": 1450.50, "valid": True},
                    {"mandi": "Kolar", "price": 2100.00, "valid": False},
                ],
                "score": 98.6,
            },
        }
        self.repo.create_job(complex_payload)
        retrieved = self.repo.get_job("job-1008")
        self.assertEqual(retrieved["nested"]["recommendations"][0]["mandi"], "Agra")
        self.assertEqual(retrieved["nested"]["score"], 98.6)

    def test_09_corrupted_json_handling(self):
        """Corrupted JSON string raises clean RedisStorageException without leaking internals."""
        self.fake_redis.set("marketlink:job:job-corrupt", "INVALID_NOT_JSON{[[")
        with self.assertRaises(RedisStorageException) as ctx:
            self.repo.get_job("job-corrupt")
        self.assertIn("Corrupted job data", str(ctx.exception))

    def test_10_connection_error_handling(self):
        """Simulated connection failure raises clean RedisStorageException without credentials."""
        broken_client = MagicMock()
        broken_client.get.side_effect = redis.ConnectionError("Connection refused to 127.0.0.1:6379")
        mock_provider = MagicMock()
        mock_provider.get_client.return_value = broken_client

        repo = RedisJobRepository(client_provider=mock_provider)
        with self.assertRaises(RedisStorageException) as ctx:
            repo.get_job("job-conn-err")
        self.assertIn("connection error", str(ctx.exception).lower())
        self.assertNotIn("password", str(ctx.exception).lower())

    def test_11_queued_job_has_no_immediate_expiration(self):
        """Queued jobs maintain indefinite persistence until completion to protect worker visibility."""
        self.repo.create_job({"job_id": "job-1011", "status": "QUEUED"})
        self.assertEqual(self.fake_redis.ttl("marketlink:job:job-1011"), -1)


if __name__ == "__main__":
    unittest.main()
