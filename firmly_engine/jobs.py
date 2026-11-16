"""In-memory job records and bounded progress publication for one application worker."""

import asyncio
import time
from collections import defaultdict
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

JobStatus = Literal["pending", "processing", "completed", "failed"]
ProgressEvent = dict[str, Any]


PUBLIC_EVENT_FIELDS = frozenset(
    {
        "type",
        "step",
        "category",
        "message",
        "count",
        "total_documents",
        "completed_steps",
        "query",
        "query_number",
    }
)


def public_event(event: ProgressEvent) -> ProgressEvent:
    return {key: value for key, value in event.items() if key in PUBLIC_EVENT_FIELDS}


class ResearchEvents(list[ProgressEvent]):
    """Keep replay history bounded and notify stream subscribers of new events."""

    def __init__(self):
        super().__init__()
        self._signal = asyncio.Event()

    def append(self, item: ProgressEvent) -> None:
        if item.get("type") in {"query_generating", "report_chunk"} or len(self) >= 2048:
            return
        super().append(item.copy())
        self._signal.set()

    def extend(self, items) -> None:
        for item in items:
            self.append(item)

    def notify(self) -> None:
        self._signal.set()

    async def wait(self, timeout: float, after: int | None = None) -> None:
        # Clear before checking: an append between the check and wait sets the signal.
        self._signal.clear()
        if after is not None and len(self) > after:
            return
        try:
            await asyncio.wait_for(self._signal.wait(), timeout)
        except TimeoutError:
            pass


class JobRecord(TypedDict, total=False):
    status: JobStatus
    company: str | None
    report: str | None
    error: str | None
    last_update: str
    created_at: float
    current_step: str
    completed_steps: list[str]
    request_context: tuple
    events: ResearchEvents


def new_job() -> JobRecord:
    return JobRecord(
        status="pending",
        company=None,
        report=None,
        error=None,
        last_update=datetime.now(UTC).isoformat(),
        created_at=time.time(),
        completed_steps=[],
        events=ResearchEvents(),
    )


class JobStore(defaultdict[str, JobRecord]):
    def __init__(self):
        super().__init__(new_job)

    def publish(self, job_id: str | None, event: ProgressEvent) -> None:
        job = self.get(job_id) if job_id else None
        if job is not None:
            job["events"].append(public_event(event))

    def record_step(self, job_id: str, step: str) -> None:
        job = self[job_id]
        job["current_step"] = step
        if step not in job["completed_steps"]:
            job["completed_steps"].append(step)
        self.publish(
            job_id,
            {"type": "progress", "step": step, "completed_steps": job["completed_steps"].copy()},
        )

    def prune(self, *, ttl: int, capacity: int) -> None:
        now = time.time()
        for key, job in list(self.items()):
            if job["status"] in {"completed", "failed"} and now - job["created_at"] > ttl:
                del self[key]
        finished = sorted(
            (key for key, job in self.items() if job["status"] in {"completed", "failed"}),
            key=lambda key: self[key]["created_at"],
        )
        for key in finished:
            if len(self) < capacity:
                break
            del self[key]


job_store = JobStore()
research_jobs = job_store
active_store: ContextVar[JobStore] = ContextVar("firmly_job_store", default=job_store)


def publish_event(job_id: str | None, event: ProgressEvent) -> None:
    active_store.get().publish(job_id, event)
