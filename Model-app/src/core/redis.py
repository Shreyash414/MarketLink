"""
Redis Infrastructure & Connection Management Module.
Responsible solely for connection pooling, client access, health checks, and lifecycle cleanup.
Follows Single Responsibility Principle (SRP) — contains zero job business logic.
"""
import threading
from typing import Optional
import redis

from src.core.config import settings
from src.utils.logger import logger


class RedisClient:
    """Manages Redis connection pooling, client lifecycle, and health verification."""

    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._lock = threading.Lock()
        self._custom_client: Optional[redis.Redis] = None

    def _init_pool(self) -> None:
        """Initialize the connection pool lazily."""
        if self._custom_client is not None:
            return

        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    try:
                        if settings.REDIS_URL:
                            self._pool = redis.ConnectionPool.from_url(
                                settings.REDIS_URL,
                                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                                decode_responses=True,
                            )
                        else:
                            self._pool = redis.ConnectionPool(
                                host=settings.REDIS_HOST,
                                port=settings.REDIS_PORT,
                                db=settings.REDIS_DB,
                                password=settings.REDIS_PASSWORD or None,
                                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                                decode_responses=True,
                            )
                        self._client = redis.Redis(connection_pool=self._pool)
                    except Exception as e:
                        logger.error(f"Failed to initialize Redis connection pool: {e}")
                        self._pool = None
                        self._client = None

    def get_client(self) -> redis.Redis:
        """Return the active Redis client with decode_responses=True."""
        if self._custom_client is not None:
            return self._custom_client

        if self._client is None:
            self._init_pool()

        if self._client is None:
            # Create a lightweight standalone client attempt
            if settings.REDIS_URL:
                return redis.Redis.from_url(
                    settings.REDIS_URL,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    decode_responses=True,
                )
            return redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD or None,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,
            )

        return self._client

    def ping(self) -> bool:
        """
        Check if Redis is reachable. Returns True if alive, False otherwise.
        Does not raise exceptions or crash caller.
        """
        try:
            client = self.get_client()
            return bool(client.ping())
        except Exception as e:
            logger.warning(f"Redis health ping failed: {e}")
            return False

    def close(self) -> None:
        """Gracefully disconnect and close connection pool."""
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception as e:
                    logger.warning(f"Error closing Redis client: {e}")
                self._client = None

            if self._pool is not None:
                try:
                    self._pool.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting Redis pool: {e}")
                self._pool = None

    def set_custom_client(self, client: Optional[redis.Redis]) -> None:
        """
        Allows injecting a mock, fake, or custom client (e.g. fakeredis) for tests.
        """
        with self._lock:
            self._custom_client = client


# Singleton infrastructure client instance
redis_client = RedisClient()
