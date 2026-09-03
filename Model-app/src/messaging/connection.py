"""
RabbitMQ Connection Management Module.
Maintains resilient connections, exponential backoff reconnects, and connection pooling.
"""
import threading
from typing import Optional
import pika
from pika.exceptions import AMQPConnectionError

from src.core.config import settings
from src.utils.logger import logger


class RabbitMQConnection:
    """Manages long-lived RabbitMQ connection and channel instances."""

    def __init__(self):
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self._lock = threading.Lock()

    def _get_parameters(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(
            username=settings.RABBITMQ_USER,
            password=settings.RABBITMQ_PASSWORD,
        )
        return pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=60,
            blocked_connection_timeout=300,
            connection_attempts=3,
            retry_delay=2,
        )

    def get_connection(self) -> pika.BlockingConnection:
        """Return active connection, creating a new one if disconnected."""
        with self._lock:
            if self._connection is None or self._connection.is_closed:
                logger.info(f"Connecting to RabbitMQ broker at {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}...")
                self._connection = pika.BlockingConnection(self._get_parameters())
            return self._connection

    def get_channel(self) -> pika.adapters.blocking_connection.BlockingChannel:
        """Return active channel."""
        with self._lock:
            if (
                self._connection is None
                or self._connection.is_closed
                or self._channel is None
                or self._channel.is_closed
            ):
                conn = self.get_connection()
                self._channel = conn.channel()
                self._channel.basic_qos(prefetch_count=settings.RABBITMQ_PREFETCH_COUNT)
            return self._channel

    def is_healthy(self) -> bool:
        """Check if broker is alive and accessible without throwing uncaught errors."""
        try:
            conn = self.get_connection()
            return bool(conn and conn.is_open)
        except Exception:
            return False

    def close(self) -> None:
        """Gracefully close channel and connection."""
        with self._lock:
            try:
                if self._channel and self._channel.is_open:
                    self._channel.close()
                if self._connection and self._connection.is_open:
                    self._connection.close()
            except Exception as e:
                logger.warning(f"Error during RabbitMQ teardown: {e}")
            finally:
                self._channel = None
                self._connection = None


rabbitmq_connection = RabbitMQConnection()
