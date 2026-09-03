"""
RabbitMQ Producer / Publisher Module.
Publishes asynchronous ML prediction and recommendation jobs to the durable exchange.
Persists initial QUEUED state directly to Redis via JobService.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import uuid

import pika

from src.core.config import settings
from src.core.exceptions import MessagingException
from src.messaging.connection import rabbitmq_connection
from src.messaging.topology import setup_rabbitmq_topology
from src.services.job_service import job_service
from src.utils.logger import logger


class RabbitMQProducer:
    """Publishes asynchronous ML tasks to RabbitMQ broker and registers state in Redis."""

    def __init__(self):
        self.connection = rabbitmq_connection

    def publish_job(
        self,
        operation: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Register job in Redis and publish message to exchange with persistence delivery mode.
        """
        job_id = correlation_id or str(uuid.uuid4())

        # 1. Store initial QUEUED state in Redis authoritative store
        job_service.create_job(
            job_id=job_id,
            operation=operation,
            payload=payload,
        )

        message_body = {
            "job_id": job_id,
            "operation": operation,
            "payload": payload,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        }

        try:
            channel = self.connection.get_channel()
            setup_rabbitmq_topology(channel)

            properties = pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
                correlation_id=job_id,
                message_id=str(uuid.uuid4()),
                headers={"x-retry-count": 0, "operation": operation},
            )

            channel.basic_publish(
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=settings.RABBITMQ_ROUTING_KEY,
                body=json.dumps(message_body),
                properties=properties,
            )

            logger.info(f"Successfully published job '{job_id}' (op={operation}) to RabbitMQ exchange")
            return job_id

        except Exception as e:
            logger.error(f"Failed to publish async job '{job_id}' to RabbitMQ: {e}")
            job_service.set_failed(job_id, error_message=f"Messaging error during enqueue: {e}")
            raise MessagingException(f"Failed to enqueue async job: {e}")


producer = RabbitMQProducer()
