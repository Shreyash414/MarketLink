"""
Integration Test 19: RabbitMQ + Redis Full Lifecycle Flow.
Tests the complete asynchronous lifecycle:
1. Enqueue -> Redis: QUEUED -> RabbitMQ
2. Worker receive -> Redis: PROCESSING
3. ML execution -> Redis: COMPLETED (with real ML result payload)
4. Failure path -> Redis: FAILED (with error details)
"""
import json
import unittest
from unittest.mock import MagicMock, patch
import fakeredis
import pika

from src.core.redis import redis_client
from src.messaging.consumer.worker import AIWorker
from src.messaging.producer.publisher import RabbitMQProducer
from src.repositories.redis_job_repository import RedisJobRepository
from src.services.job_service import JobService


class TestRabbitMQRedisFlow(unittest.TestCase):

    def setUp(self):
        self.fake_server = fakeredis.FakeServer()
        self.fake_redis = fakeredis.FakeRedis(server=self.fake_server, decode_responses=True)
        redis_client.set_custom_client(self.fake_redis)

        # Mock RabbitMQ connection & channel
        self.mock_channel = MagicMock(spec=pika.adapters.blocking_connection.BlockingChannel)
        self.mock_conn = MagicMock()
        self.mock_conn.get_channel.return_value = self.mock_channel

        self.producer = RabbitMQProducer()
        self.producer.connection = self.mock_conn

        self.worker = AIWorker()
        self.worker.connection = self.mock_conn

    def tearDown(self):
        redis_client.set_custom_client(None)

    def test_01_successful_pipeline_flow(self):
        """
        FastAPI/Producer:
        Enqueues job -> Redis: QUEUED
        Worker receives:
        Redis: PROCESSING -> executes ML operation -> Redis: COMPLETED -> ACK
        """
        job_id = "test-flow-success-01"
        payload = {
            "market": "Bareilly",
            "commodity": "Onion",
            "current_price": 1850.0,
            "features": {"lag_7": 1800.0, "rolling_mean_7": 1820.0},
            "date": "2026-09-03",
            "farmer_facing": False,
        }

        # Step 1: Enqueue via Producer
        returned_id = self.producer.publish_job(
            operation="PREDICT_PRICE",
            payload=payload,
            correlation_id=job_id,
        )
        self.assertEqual(returned_id, job_id)

        # Confirm initial state in Redis is QUEUED
        job_record = self.fake_redis.get(f"marketlink:job:{job_id}")
        self.assertIsNotNone(job_record)
        job_dict = json.loads(job_record)
        self.assertEqual(job_dict["status"], "QUEUED")
        self.assertEqual(job_dict["operation"], "PREDICT_PRICE")

        # Confirm RabbitMQ message was published
        self.assertTrue(self.mock_channel.basic_publish.called)
        pub_kwargs = self.mock_channel.basic_publish.call_args.kwargs
        pub_body = json.loads(pub_kwargs["body"])
        self.assertEqual(pub_body["job_id"], job_id)

        # Step 2 & 3: Worker processes message with mock ML output
        mock_pred_result = {
            "market": "Bareilly",
            "commodity": "Onion",
            "current_price": 1850.0,
            "predicted_price": 1880.0,
            "expected_change": 30.0,
            "expected_change_pct": 1.62,
            "expected_direction": "UP",
            "usage_status": "USABLE_WITH_WARNING",
            "reliability_score": 48.7,
            "quality_class": "ACCEPTABLE",
            "data_source": "DIRECT",
        }

        with patch("src.services.ml_service.ml_service.predict_single", return_value=mock_pred_result):
            deliver_method = MagicMock()
            deliver_method.delivery_tag = 42
            properties = MagicMock()
            properties.correlation_id = job_id

            # Invoke worker message handler
            self.worker.handle_message(
                ch=self.mock_channel,
                method=deliver_method,
                properties=properties,
                body=json.dumps(pub_body).encode("utf-8"),
            )

        # Step 4: Verify worker ACKed the message
        self.mock_channel.basic_ack.assert_called_once_with(delivery_tag=42)

        # Step 5: Verify final state in Redis is COMPLETED with real result payload
        final_record = self.fake_redis.get(f"marketlink:job:{job_id}")
        final_dict = json.loads(final_record)
        self.assertEqual(final_dict["status"], "COMPLETED")
        self.assertEqual(final_dict["result"]["predicted_price"], 1880.0)
        self.assertEqual(final_dict["result"]["market"], "Bareilly")
        self.assertIsNotNone(final_dict["completed_at"])

    def test_02_failed_pipeline_flow(self):
        """
        FastAPI/Producer:
        Enqueues job -> Redis: QUEUED
        Worker receives:
        Redis: PROCESSING -> ML validation failure -> Redis: FAILED -> DLQ Reject
        """
        job_id = "test-flow-fail-02"
        payload = {"invalid_data": True}

        # Step 1: Enqueue via Producer
        self.producer.publish_job(
            operation="UNKNOWN_OPERATION_TYPE",
            payload=payload,
            correlation_id=job_id,
        )

        # Confirm QUEUED in Redis
        queued_dict = json.loads(self.fake_redis.get(f"marketlink:job:{job_id}"))
        self.assertEqual(queued_dict["status"], "QUEUED")

        # Step 2: Worker processes invalid operation
        deliver_method = MagicMock()
        deliver_method.delivery_tag = 99
        properties = MagicMock()
        properties.correlation_id = job_id

        msg_body = {
            "job_id": job_id,
            "operation": "UNKNOWN_OPERATION_TYPE",
            "payload": payload,
            "retry_count": 0,
        }

        self.worker.handle_message(
            ch=self.mock_channel,
            method=deliver_method,
            properties=properties,
            body=json.dumps(msg_body).encode("utf-8"),
        )

        # Step 3: Verify rejected to DLQ (requeue=False)
        self.mock_channel.basic_reject.assert_called_once_with(delivery_tag=99, requeue=False)

        # Step 4: Verify state in Redis is FAILED with error payload
        failed_record = self.fake_redis.get(f"marketlink:job:{job_id}")
        failed_dict = json.loads(failed_record)
        self.assertEqual(failed_dict["status"], "FAILED")
        self.assertIn("Unknown operation type", failed_dict["error"]["message"])
        self.assertIsNotNone(failed_dict["completed_at"])


if __name__ == "__main__":
    unittest.main()
