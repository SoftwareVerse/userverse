"""Job bus package exposing the global bus registry."""

from __future__ import annotations

from typing import Optional

from .bus import Job, JobBus, JobType

job_bus: Optional[JobBus] = None


def set_bus(bus: JobBus) -> None:
    """Register the shared job bus instance."""

    global job_bus
    job_bus = bus


def get_bus() -> Optional[JobBus]:
    """Return the shared job bus instance if one is configured."""

    return job_bus


__all__ = ["Job", "JobBus", "JobType", "get_bus", "set_bus"]
