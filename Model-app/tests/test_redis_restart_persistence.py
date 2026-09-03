"""
Acceptance Test 20: Process Restart Persistence Test.
Demonstrates that job state persists in Redis across complete FastAPI process lifecycle restarts,
proving why Redis replaces ephemeral in-memory storage.
"""
import unittest
import fakeredis
from fastapi.testclient import TestClient

from src.core.redis import redis_client
from src.main import app
from src.repositories.redis_job_repository import RedisJobRepository
from src.services.job_service import job_service


class TestRedisRestartPersistence(unittest.TestCase):

    def setUp(self):
        # Shared server simulates persistent Redis daemon across restarts
        self.shared_server = fakeredis.FakeServer()
        self.shared_client = fakeredis.FakeRedis(server=self.shared_server, decode_responses=True)
        redis_client.set_custom_client(self.shared_client)

    def tearDown(self):
        redis_client.set_custom_client(None)

    def test_job_state_persists_across_fastapi_process_restart(self):
        """
        Step 1: Create a job via FastAPI instance A.
        Step 2: Verify job exists in Redis.
        Step 3: Simulate complete FastAPI restart (clean app, new client, new connection).
        Step 4: Query the same job ID via new FastAPI instance B.
        Step 5: Verify job state and payload are intact and retrieved from Redis.
        """
        # --- Instance A (Before Restart) ---
        with TestClient(app) as client_a:
            # Create a job
            job_id = "restart-acceptance-job-888"
            job_service.create_job(
                job_id=job_id,
                operation="RECOMMEND_MANDI",
                payload={"commodity": "Onion", "quantity_quintals": 50.0},
            )
            # Update to COMPLETED
            job_service.set_completed(
                job_id=job_id,
                result={"recommended_mandi": "Bareilly", "expected_net_return": 92500.0},
            )

            # Query via Instance A
            resp_a = client_a.get(f"/api/v1/jobs/{job_id}")
            self.assertEqual(resp_a.status_code, 200)
            data_a = resp_a.json()
            self.assertEqual(data_a["status"], "COMPLETED")
            self.assertEqual(data_a["result"]["recommended_mandi"], "Bareilly")

        # --- Process Restart Simulation ---
        # Close previous client connections
        redis_client.close()

        # Connect new process instance to the same Redis storage
        new_process_client = fakeredis.FakeRedis(server=self.shared_server, decode_responses=True)
        redis_client.set_custom_client(new_process_client)

        # --- Instance B (After Restart) ---
        with TestClient(app) as client_b:
            # Query the exact same job ID after restart
            resp_b = client_b.get(f"/api/v1/jobs/{job_id}")
            self.assertEqual(resp_b.status_code, 200)
            data_b = resp_b.json()

            # Confirm state survived process termination
            self.assertEqual(data_b["job_id"], job_id)
            self.assertEqual(data_b["status"], "COMPLETED")
            self.assertEqual(data_b["operation"], "RECOMMEND_MANDI")
            self.assertEqual(data_b["result"]["recommended_net_return"] if "recommended_net_return" in data_b["result"] else data_b["result"]["expected_net_return"], 92500.0)
            self.assertIsNotNone(data_b["completed_at"])


if __name__ == "__main__":
    unittest.main()
