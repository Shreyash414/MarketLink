"""
Concurrency and Atomic Update Tests for Redis Job Storage.
Ensures thread-safe state transitions and atomic consistency under concurrent updates.
"""
import concurrent.futures
import threading
import unittest
import fakeredis

from src.core.redis import RedisClient
from src.repositories.redis_job_repository import RedisJobRepository
from src.services.job_service import JobService


class TestRedisConcurrency(unittest.TestCase):

    def setUp(self):
        # FakeServer shared across threads simulates real Redis server
        self.server = fakeredis.FakeServer()
        self.client = fakeredis.FakeRedis(server=self.server, decode_responses=True)
        self.mock_provider = RedisClient()
        self.mock_provider.set_custom_client(self.client)
        self.repo = RedisJobRepository(client_provider=self.mock_provider)
        self.service = JobService(repository=self.repo)

    def tearDown(self):
        self.mock_provider.set_custom_client(None)

    def test_01_concurrent_independent_job_creations(self):
        """100 concurrent threads creating distinct jobs in Redis with zero collisions or loss."""
        num_jobs = 100
        job_ids = [f"concurrent-job-{i}" for i in range(num_jobs)]

        def worker(jid: str):
            self.service.create_job(job_id=jid, operation="RECOMMEND_MANDI", payload={"index": jid})

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(worker, job_ids))

        # Verify all 100 exist in Redis
        for jid in job_ids:
            job = self.service.get_job(jid)
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "QUEUED")
            self.assertEqual(job["payload"]["index"], jid)

    def test_02_concurrent_updates_to_same_job(self):
        """Simultaneous competing updates to a shared job record resolve cleanly via atomic watch/pipeline."""
        job_id = "shared-job-concurrency"
        self.service.create_job(job_id=job_id, operation="RECOMMEND_MANDI")

        num_updates = 20
        results_collected = []

        def worker(thread_idx: int):
            # Attempt to transition or update payload atomically
            res = self.repo.update_job(job_id, {f"field_{thread_idx}": thread_idx})
            if res:
                results_collected.append(thread_idx)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_updates)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_job = self.service.get_job(job_id)
        self.assertIsNotNone(final_job)
        # All atomic updates should be reflected in the final dictionary
        for i in range(num_updates):
            self.assertIn(f"field_{i}", final_job)
            self.assertEqual(final_job[f"field_{i}"], i)


if __name__ == "__main__":
    unittest.main()
