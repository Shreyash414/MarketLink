"""
AI Worker Daemon.
Asynchronously consumes ML jobs from RabbitMQ, reuses pre-loaded in-memory models,
handles retries, routes permanent failures to Dead Letter Queue (DLQ), and updates Redis job state.
"""
import json
import signal
import sys
import time
from typing import Any, Dict, Optional

import pika

from src.core.config import settings
from src.core.exceptions import InvalidInputException, ModelServiceException, RedisStorageException
from src.messaging.connection import rabbitmq_connection
from src.messaging.topology import setup_rabbitmq_topology
from src.models.model_predictor import get_shared_predictor
from src.services.job_service import job_service
from src.services.ml_service import ml_service
from src.utils.logger import logger


class AIWorker:
    """Consumes ML asynchronous jobs, executes inference, and records status in Redis."""

    def __init__(self):
        self.connection = rabbitmq_connection
        self.predictor = get_shared_predictor()
        self._should_stop = False

    def handle_message(
        self,
        ch: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        """
        Process an incoming AMQP message with strict Redis state transition ordering.
        """
        try:
            raw_text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body
            message = json.loads(raw_text)
        except Exception as e:
            logger.error(f"Malformed non-JSON message received. Rejecting to DLQ: {e}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        job_id = message.get("job_id") or properties.correlation_id or "unknown"
        operation = message.get("operation", "UNKNOWN")
        payload = message.get("payload", {})
        retry_count = message.get("retry_count", 0)

        logger.info(f"Worker received job '{job_id}' (operation={operation}, retry={retry_count})")

        # 1. Transition state to PROCESSING in Redis
        try:
            job_service.set_processing(job_id)
        except Exception as e:
            logger.error(f"Redis failure updating job '{job_id}' to PROCESSING: {e}. Requeuing message.")
            # Do NOT ack message if Redis fails before processing
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        # 2. Execute task logic
        try:
            if operation == "RECOMMEND_MANDI":
                canonical = ml_service.get_recommendation(
                    farmer_latitude=float(payload["farmer_latitude"]),
                    farmer_longitude=float(payload["farmer_longitude"]),
                    quantity_quintals=float(payload["quantity_quintals"]),
                    commodity=payload.get("commodity", "Onion"),
                    max_distance_km=payload.get("max_distance_km"),
                    transport_rate=float(payload.get("transport_rate", 3.0)),
                    farmer_facing=payload.get("farmer_facing", True),
                )
                result_dict = canonical.to_dict()

            elif operation == "PREDICT_PRICE":
                result_dict = ml_service.predict_single(
                    market=payload["market"],
                    commodity=payload.get("commodity", "Onion"),
                    current_price=float(payload["current_price"]),
                    features=payload["features"],
                    date=payload.get("date"),
                    farmer_facing=payload.get("farmer_facing", True),
                )

            else:
                raise ValueError(f"Unknown operation type: '{operation}'")

            # 3. Store COMPLETED result in Redis BEFORE acknowledging message
            job_service.set_completed(job_id, result_dict)

            # 4. Acknowledge message only after successful Redis persistence
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Worker successfully processed and completed job '{job_id}'")

        except (InvalidInputException, ValueError) as e:
            # Non-retryable user validation error: record failure and reject to DLQ
            logger.warning(f"Unrecoverable task error for job '{job_id}': {e}")
            try:
                job_service.set_failed(job_id, error_message=str(e), error_details={"error_type": "VALIDATION_ERROR"})
            except Exception as re:
                logger.error(f"Failed to record failure in Redis for job '{job_id}': {re}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

        except RedisStorageException as e:
            # Redis failed during result persistence: requeue message so result is not lost
            logger.error(f"Redis storage failure persisting result for job '{job_id}': {e}. Requeuing.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        except Exception as e:
            # Transient service or unexpected error: retry logic
            logger.error(f"Transient error processing job '{job_id}': {e}")
            if retry_count < settings.RABBITMQ_MAX_RETRIES:
                new_retry = retry_count + 1
                logger.info(f"Retrying job '{job_id}' (attempt {new_retry}/{settings.RABBITMQ_MAX_RETRIES})...")
                message["retry_count"] = new_retry
                time.sleep(1.0)
                # Publish retry back to queue
                ch.basic_publish(
                    exchange=settings.RABBITMQ_EXCHANGE,
                    routing_key=settings.RABBITMQ_ROUTING_KEY,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=pika.DeliveryMode.Persistent,
                        correlation_id=job_id,
                        headers={"x-retry-count": new_retry},
                    ),
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Retries exhausted: record permanent failure in Redis and route to DLQ
                logger.error(f"Max retries exhausted for job '{job_id}'. Routing to DLQ.")
                try:
                    job_service.set_failed(
                        job_id,
                        error_message=f"Processing failed after {settings.RABBITMQ_MAX_RETRIES} attempts: {e}",
                        error_details={"error_type": "MAX_RETRIES_EXCEEDED"},
                    )
                except Exception as re:
                    logger.error(f"Failed to record failure in Redis for job '{job_id}': {re}")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self) -> None:
        """Start listening for messages on the configured work queue."""
        logger.info(f"Starting AI Worker consuming from '{settings.RABBITMQ_QUEUE}'...")
        channel = self.connection.get_channel()
        setup_rabbitmq_topology(channel)

        channel.basic_consume(
            queue=settings.RABBITMQ_QUEUE,
            on_message_callback=self.handle_message,
            auto_ack=False,
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user.")
            channel.stop_consuming()
        except Exception as e:
            logger.error(f"Worker encountered fatal consumption error: {e}")
            raise


def run_worker() -> None:
    """CLI entrypoint for running the AI Worker daemon."""
    worker = AIWorker()

    def sig_handler(sig, frame):
        logger.info("Termination signal received. Shutting down worker...")
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    worker.start_consuming()


if __name__ == "__main__":
    run_worker()
