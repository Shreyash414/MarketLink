"""
RabbitMQ Topology Declarations.
Configures durable exchanges, queues, Dead Letter Exchange (DLX), and Dead Letter Queue (DLQ).
"""
import pika

from src.core.config import settings
from src.utils.logger import logger


def setup_rabbitmq_topology(channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
    """
    Declare enterprise AMQP topology:
    - Primary Direct Exchange
    - Dead Letter Direct Exchange (DLX)
    - Primary Work Queue with x-dead-letter-exchange routing
    - Dead Letter Queue (DLQ)
    """
    logger.info("Declaring RabbitMQ exchanges and queues...")

    # 1. Declare Dead Letter Exchange & Queue
    channel.exchange_declare(
        exchange=settings.RABBITMQ_DLQ_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )
    channel.queue_declare(
        queue=settings.RABBITMQ_DLQ_QUEUE,
        durable=True,
    )
    channel.queue_bind(
        queue=settings.RABBITMQ_DLQ_QUEUE,
        exchange=settings.RABBITMQ_DLQ_EXCHANGE,
        routing_key=settings.RABBITMQ_DLQ_ROUTING_KEY,
    )

    # 2. Declare Primary Exchange
    channel.exchange_declare(
        exchange=settings.RABBITMQ_EXCHANGE,
        exchange_type="direct",
        durable=True,
    )

    # 3. Declare Primary Work Queue with DLX configuration
    queue_args = {
        "x-dead-letter-exchange": settings.RABBITMQ_DLQ_EXCHANGE,
        "x-dead-letter-routing-key": settings.RABBITMQ_DLQ_ROUTING_KEY,
    }
    channel.queue_declare(
        queue=settings.RABBITMQ_QUEUE,
        durable=True,
        arguments=queue_args,
    )
    channel.queue_bind(
        queue=settings.RABBITMQ_QUEUE,
        exchange=settings.RABBITMQ_EXCHANGE,
        routing_key=settings.RABBITMQ_ROUTING_KEY,
    )

    logger.info("RabbitMQ topology declared successfully.")
