"""
Redis-backed Job Repository Implementation.
Handles serialization, namespaced keys, TTL policies, and atomic operations.
Follows Single Responsibility Principle (SRP) and Liskov Substitution Principle (LSP).
"""
import json
from typing import Any, Dict, Optional
import redis

from src.core.config import settings
from src.core.exceptions import RedisStorageException
from src.core.redis import RedisClient, redis_client
from src.repositories.job_repository import JobRepository
from src.utils.logger import logger


class RedisJobRepository(JobRepository):
    """
    Durable Redis implementation of JobRepository using namespaced keys and JSON serialization.
    Key pattern: marketlink:job:{job_id}
    """

    def __init__(self, client_provider: Optional[RedisClient] = None, ttl_seconds: Optional[int] = None):
        self._client_provider = client_provider or redis_client
        self._ttl_seconds = ttl_seconds or settings.REDIS_JOB_TTL_SECONDS
        self._key_prefix = settings.REDIS_KEY_PREFIX

    def _get_key(self, job_id: str) -> str:
        """Generate standardized namespaced Redis key."""
        return f"{self._key_prefix}:{job_id.strip()}"

    def _get_redis(self) -> redis.Redis:
        """Retrieve the underlying Redis client."""
        return self._client_provider.get_client()

    def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persist a new job record.
        Active/queued jobs do not have an aggressive TTL to prevent visibility loss.
        """
        job_id = job_data.get("job_id")
        if not job_id:
            raise RedisStorageException("Cannot create job without a 'job_id'.")

        key = self._get_key(job_id)
        try:
            r = self._get_redis()
            payload = json.dumps(job_data)
            # Active jobs: store without immediate expiration to protect in-flight tasks
            r.set(key, payload)
            return job_data
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failure while creating job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to persist job '{job_id}' in Redis storage: connection error.")
        except Exception as e:
            logger.error(f"Unexpected Redis error creating job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to create job in Redis storage: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a job by ID. Returns None if the job is not found.
        """
        key = self._get_key(job_id)
        try:
            r = self._get_redis()
            raw_data = r.get(key)
            if not raw_data:
                return None
            return json.loads(raw_data)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failure while retrieving job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to retrieve job '{job_id}' from Redis storage: connection error.")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize job data for key '{key}': {e}")
            raise RedisStorageException(f"Corrupted job data in Redis storage for job '{job_id}'.")
        except Exception as e:
            logger.error(f"Unexpected Redis error retrieving job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to retrieve job from Redis storage: {e}")

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Atomically update fields of an existing job record and apply terminal TTL when completed/failed.
        Uses Redis WATCH / MULTI / EXEC transaction to prevent race conditions without distributed locks.
        """
        key = self._get_key(job_id)
        try:
            r = self._get_redis()
            for _ in range(5):  # Retry up to 5 times on concurrent conflict
                pipe = r.pipeline()
                try:
                    pipe.watch(key)
                    raw_data = pipe.get(key)
                    if not raw_data:
                        pipe.unwatch()
                        return None

                    current_data = json.loads(raw_data)
                    current_data.update(updates)
                    status = current_data.get("status")

                    pipe.multi()
                    new_payload = json.dumps(current_data)
                    pipe.set(key, new_payload)

                    # Apply TTL only when job reaches terminal state (COMPLETED or FAILED)
                    if status in ("COMPLETED", "FAILED"):
                        pipe.expire(key, self._ttl_seconds)

                    pipe.execute()
                    return current_data
                except redis.WatchError:
                    continue  # Concurrently modified, retry
                finally:
                    pipe.reset()
            # If watch retries exhausted, perform direct update
            raw_data = r.get(key)
            if not raw_data:
                return None
            current_data = json.loads(raw_data)
            current_data.update(updates)
            status = current_data.get("status")
            pipe = r.pipeline()
            pipe.set(key, json.dumps(current_data))
            if status in ("COMPLETED", "FAILED"):
                pipe.expire(key, self._ttl_seconds)
            pipe.execute()
            return current_data

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failure updating job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to update job '{job_id}' in Redis storage: connection error.")
        except Exception as e:
            logger.error(f"Unexpected Redis error updating job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to update job in Redis storage: {e}")

    def delete_job(self, job_id: str) -> bool:
        """Delete job key. Returns True if deleted, False if key did not exist."""
        key = self._get_key(job_id)
        try:
            r = self._get_redis()
            return bool(r.delete(key))
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failure deleting job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to delete job '{job_id}' from Redis storage: connection error.")
        except Exception as e:
            logger.error(f"Unexpected Redis error deleting job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to delete job from Redis storage: {e}")

    def job_exists(self, job_id: str) -> bool:
        """Check if job key exists in Redis."""
        key = self._get_key(job_id)
        try:
            r = self._get_redis()
            return bool(r.exists(key))
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failure checking existence of job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to check existence of job '{job_id}': connection error.")
        except Exception as e:
            logger.error(f"Unexpected Redis error checking existence of job '{job_id}': {e}")
            raise RedisStorageException(f"Failed to check job existence in Redis: {e}")
