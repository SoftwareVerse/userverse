"""Simple asyncio-backed job bus for background processing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

from app.utils.logging import logger


class JobType(str, Enum):
    EMAIL_SEND = "email_send"


@dataclass(slots=True)
class Job:
    type: JobType
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class JobStore(Protocol):
    async def enqueue(self, job: Optional[Job]) -> None:
        ...

    def enqueue_nowait(self, job: Optional[Job]) -> None:
        ...

    async def dequeue(self) -> Optional[Job]:
        ...

    def task_done(self) -> None:
        ...

    async def join(self) -> None:
        ...


class JobBus:
    """Coordinates workers that process jobs pulled from a store."""

    def __init__(
        self,
        store: JobStore,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._store = store
        self._loop = loop or asyncio.get_event_loop()
        self._handlers: Dict[JobType, Callable[[Job], Awaitable[Any]]] = {}
        self._stopping = asyncio.Event()
        self._worker_count = 0

    def register(self, job_type: JobType, handler: Callable[[Job], Awaitable[Any]]) -> None:
        """Register an async handler for a given job type."""

        self._handlers[job_type] = handler

    def enqueue(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Enqueue a job from any thread by scheduling it on the loop."""

        if self._stopping.is_set():
            raise RuntimeError("Job bus is shutting down")

        job = Job(job_type, payload, metadata or {})

        def _put() -> None:
            self._store.enqueue_nowait(job)

        if self._loop.is_closed():
            raise RuntimeError("Event loop is closed; cannot enqueue job")

        self._loop.call_soon_threadsafe(_put)

    async def enqueue_async(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Async variant of enqueue for use inside the loop."""

        if self._stopping.is_set():
            raise RuntimeError("Job bus is shutting down")

        await self._store.enqueue(Job(job_type, payload, metadata or {}))

    async def run_worker(self) -> None:
        """Continuously pull jobs from the store until shutdown."""

        self._worker_count += 1
        try:
            while True:
                try:
                    job = await self._store.dequeue()
                except asyncio.CancelledError:
                    raise

                if job is None:
                    self._store.task_done()
                    break

                handler = self._handlers.get(job.type)
                if not handler:
                    logger.error("No handler registered for job type %s", job.type)
                    self._store.task_done()
                    continue

                try:
                    await handler(job)
                except Exception:  # pragma: no cover - logged and continued
                    logger.exception("Error processing job type %s", job.type)
                finally:
                    self._store.task_done()
        finally:
            self._worker_count -= 1

    async def join(self) -> None:
        """Wait until all tasks in the store have been processed."""

        await self._store.join()

    def stop(self) -> None:
        """Signal workers to exit once the queue drains."""

        if self._stopping.is_set():
            return

        self._stopping.set()

        if self._loop.is_closed():  # pragma: no cover - defensive
            return

        def _put_sentinel() -> None:
            for _ in range(max(self._worker_count, 1)):
                self._store.enqueue_nowait(None)

        self._loop.call_soon_threadsafe(_put_sentinel)
