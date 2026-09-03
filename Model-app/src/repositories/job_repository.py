"""
Job Repository Abstract Interface.
Defines the contract for job persistence independent of the underlying storage engine.
Follows Open/Closed Principle (OCP) and Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class JobRepository(ABC):
    """Abstract persistence interface for asynchronous ML jobs."""

    @abstractmethod
    def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a new job record."""
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job data by job_id, or None if not found."""
        pass

    @abstractmethod
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply field updates to an existing job record."""
        pass

    @abstractmethod
    def delete_job(self, job_id: str) -> bool:
        """Delete a job record by job_id. Returns True if deleted, False otherwise."""
        pass

    @abstractmethod
    def job_exists(self, job_id: str) -> bool:
        """Check whether a job exists."""
        pass
