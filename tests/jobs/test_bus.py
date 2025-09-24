import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

@pytest.fixture
def anyio_backend():
    return "asyncio"

from app.jobs import JobBus
from app.jobs.bus import JobType
from app.jobs.store import InMemoryJobStore


@pytest.mark.anyio
async def test_job_bus_processes_jobs():
    loop = asyncio.get_running_loop()
    bus = JobBus(InMemoryJobStore(), loop=loop)

    processed = []

    async def handler(job):
        processed.append(job.payload["value"])

    bus.register(JobType.EMAIL_SEND, handler)

    worker = asyncio.create_task(bus.run_worker())

    bus.enqueue(JobType.EMAIL_SEND, {"value": 42})

    await asyncio.sleep(0)

    await asyncio.wait_for(bus.join(), timeout=1)

    bus.stop()
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)

    assert processed == [42]
