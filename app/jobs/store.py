"""Job store implementations."""

from __future__ import annotations

import asyncio
from typing import Optional

from .bus import Job


class InMemoryJobStore:
    """Asyncio-queue backed store for lightweight workloads."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Optional[Job]] = asyncio.Queue()

    async def enqueue(self, job: Optional[Job]) -> None:
        await self._queue.put(job)

    def enqueue_nowait(self, job: Optional[Job]) -> None:
        self._queue.put_nowait(job)

    async def dequeue(self) -> Optional[Job]:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    def empty(self) -> bool:
        return self._queue.empty()
