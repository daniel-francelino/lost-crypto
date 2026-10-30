from enum import StrEnum


class JobStatus(StrEnum):
    """Lifecycle shared by the DB-backed jobs the worker executes."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
