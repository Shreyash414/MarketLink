"""
Unit tests for JobService layer with Mocked JobRepository.
Validates business logic and verifies that JobService can be tested completely independent of Redis (DIP).
"""
import unittest
from typing import Any, Dict, Optional
from src.core.exceptions import JobNotFoundException
from src.repositories.job_repository import JobRepository
from src.services.job_service import JobService


class MockJobRepository(JobRepository):
    """Simple in-memory fake repository honoring JobRepository interface for testing."""

    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}

    def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        self.storage[job_data["job_id"]] = dict(job_data)
        return self.storage[job_data["job_id"]]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.storage.get(job_id)

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if job_id not in self.storage:
            return None
        self.storage[job_id].update(updates)
        return self.storage[job_id]

    def delete_job(self, job_id: str) -> bool:
        if job_id in self.storage:
            del self.storage[job_id]
            return True
        return False

    def job_exists(self, job_id: str) -> bool:
        return job_id in self.storage


class TestJobService(unittest.TestCase):

    def setUp(self):
        self.mock_repo = MockJobRepository()
        self.service = JobService(repository=self.mock_repo)

    def test_01_create_job_initializes_queued_state(self):
        """Creating a job through JobService creates a record with status QUEUED."""
        job = self.service.create_job(
            job_id="test-job-01",
            operation="RECOMMEND_MANDI",
            payload={"commodity": "Potato", "quantity": 25.0},
        )
        self.assertEqual(job["job_id"], "test-job-01")
        self.assertEqual(job["status"], "QUEUED")
        self.assertEqual(job["operation"], "RECOMMEND_MANDI")
        self.assertIsNotNone(job["created_at"])
        self.assertIsNone(job["completed_at"])

        # Check repository directly
        in_repo = self.mock_repo.get_job("test-job-01")
        self.assertEqual(in_repo["status"], "QUEUED")

    def test_02_set_processing(self):
        """Setting processing updates status to PROCESSING."""
        self.service.create_job(job_id="test-job-02", operation="PREDICT_PRICE")
        self.service.set_processing("test-job-02")
        job = self.service.get_job("test-job-02")
        self.assertEqual(job["status"], "PROCESSING")
        self.assertIsNotNone(job["updated_at"])

    def test_03_set_completed(self):
        """Setting completed updates status and stores result payload."""
        self.service.create_job(job_id="test-job-03", operation="RECOMMEND_MANDI")
        self.service.set_processing("test-job-03")

        result = {"recommended_mandi": "Agra", "expected_net_return": 25000.0}
        self.service.set_completed("test-job-03", result=result)

        job = self.service.get_job("test-job-03")
        self.assertEqual(job["status"], "COMPLETED")
        self.assertEqual(job["result"], result)
        self.assertIsNotNone(job["completed_at"])

    def test_04_set_failed(self):
        """Setting failed updates status and stores structured error."""
        self.service.create_job(job_id="test-job-04", operation="RECOMMEND_MANDI")
        self.service.set_failed("test-job-04", error_message="Model timed out", error_details={"code": 504})

        job = self.service.get_job("test-job-04")
        self.assertEqual(job["status"], "FAILED")
        self.assertEqual(job["error"]["message"], "Model timed out")
        self.assertEqual(job["error"]["details"]["code"], 504)
        self.assertIsNotNone(job["completed_at"])

    def test_05_get_job_or_raise(self):
        """get_job_or_raise returns record when present, raises JobNotFoundException when missing."""
        self.service.create_job(job_id="test-job-05", operation="RECOMMEND_MANDI")
        job = self.service.get_job_or_raise("test-job-05")
        self.assertEqual(job["job_id"], "test-job-05")

        with self.assertRaises(JobNotFoundException):
            self.service.get_job_or_raise("non-existent-job-xyz")

    def test_06_job_exists(self):
        """job_exists returns true only when job is registered."""
        self.assertFalse(self.service.job_exists("test-job-06"))
        self.service.create_job(job_id="test-job-06", operation="PREDICT_PRICE")
        self.assertTrue(self.service.job_exists("test-job-06"))


if __name__ == "__main__":
    unittest.main()
