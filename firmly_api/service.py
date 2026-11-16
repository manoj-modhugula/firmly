"""Job submission, provider execution, recovery, and resource ownership.
Changes: bounded job lifecycle, credential handling, and persistence recovery.
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from pymongo.errors import PyMongoError

from firmly_engine.jobs import JobStore, active_store, job_store
from firmly_engine.pipeline import ResearchPipeline
from firmly_engine.resources import connection_scope
from firmly_engine.services.pdf_service import ReportPDFExporter
from firmly_engine.services.storage import ReportStore

from .config import Limits
from .schemas import ResearchRequest

logger = logging.getLogger("firmly.jobs")


class JobService:
    def __init__(self, *, jobs: JobStore = job_store, limits: Limits | None = None):
        self.jobs = jobs
        self.limits = limits or Limits()
        self.tasks: set[asyncio.Task] = set()
        self.storage: ReportStore | None = None
        self.pdf = ReportPDFExporter()

    def open(self) -> None:
        uri = os.getenv("FIRMLY_STORAGE_URI")
        if uri:
            try:
                self.storage = ReportStore(uri)
            except (PyMongoError, ValueError):
                logger.warning(
                    "Optional database configuration is unavailable; continuing in memory."
                )

    async def close(self) -> None:
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self.storage:
            await asyncio.to_thread(self.storage.close)
            self.storage = None

    def submit(self, data: ResearchRequest):
        # A retried submission reuses its original job; a lost response must not start
        # another provider run. Only non-secret company context is compared.
        job_id = str(data.request_id or uuid.uuid4())
        context = (data.company, data.company_url, data.industry, data.hq_location, data.model)
        if job_id in self.jobs:
            if self.jobs[job_id].get("request_context") != context:
                raise HTTPException(
                    409, "This request belongs to different company details. Start a new request."
                )
            data.search_key = data.model_key = None
            return {"job_id": job_id, "status": "accepted"}
        missing = []
        if not (data.search_key or os.getenv("FIRMLY_SEARCH_KEY")):
            missing.append("web research")
        if not (
            data.model_key or os.getenv("FIRMLY_MODEL_KEY") or os.getenv("FIRMLY_DIRECT_MODEL_KEY")
        ):
            missing.append("a model provider")
        if missing:
            raise HTTPException(
                409, "Configure " + " and ".join(missing) + " in settings before starting research."
            )
        self.jobs.prune(ttl=self.limits.job_ttl, capacity=self.limits.max_jobs)
        active = sum(job["status"] in {"pending", "processing"} for job in self.jobs.values())
        if active >= self.limits.concurrency or len(self.jobs) >= self.limits.max_jobs:
            raise HTTPException(429, "Research is at capacity. Please try again shortly.")
        self.jobs[job_id].update(
            status="pending",
            company=data.company,
            created_at=time.time(),
            completed_steps=[],
            request_context=context,
        )
        task = asyncio.create_task(self.process_research(job_id, data))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return {"job_id": job_id, "status": "accepted"}

    async def db_call(self, method, *args, **kwargs):
        if self.storage:
            try:
                return await asyncio.to_thread(getattr(self.storage, method), *args, **kwargs)
            except Exception:
                logger.warning("Optional persistence unavailable (%s)", method)
        return None

    async def process_research(self, job_id: str, data: ResearchRequest):
        job = self.jobs[job_id]
        token = active_store.set(self.jobs)
        try:
            async with connection_scope():
                await self.db_call(
                    "create_job",
                    job_id,
                    data.model_dump(mode="json", exclude={"search_key", "model_key", "request_id"}),
                )
                graph = ResearchPipeline(
                    company=data.company,
                    url=data.company_url,
                    industry=data.industry,
                    hq_location=data.hq_location,
                    job_id=job_id,
                    search_key=data.search_key,
                    model_key=data.model_key,
                    model=data.model,
                )
                final = {}
                job["status"] = "processing"
                async with asyncio.timeout(self.limits.research_timeout):
                    async for state in graph.run(thread={}):
                        for node, update in state.items():
                            if isinstance(update, dict):
                                final.update(update)
                            self.jobs.record_step(job_id, node)
                report = final.get("report") or (final.get("assembled_report") or {}).get("report")
                if not report or not report.strip():
                    raise ValueError("Empty report")
                job.update(
                    status="completed", report=report, last_update=datetime.now(UTC).isoformat()
                )
                stored = await self.db_call("store_report", job_id, {"report": report})
                if stored:
                    await self.db_call("update_job", job_id, status="completed")
        except asyncio.CancelledError:
            job.update(
                status="failed", error="The server restarted. Please begin the research again."
            )
            raise
        except Exception as exc:
            # Provider exceptions can contain request headers; never return or log them.
            logger.warning("Research failed (%s)", type(exc).__name__)
            message = (
                "Research took too long. Please try again."
                if isinstance(exc, TimeoutError)
                else "Research could not be completed. Check your service credentials and try again."
            )
            job.update(status="failed", error=message, last_update=datetime.now(UTC).isoformat())
            await self.db_call("update_job", job_id, status="failed", error=message)
        finally:
            data.search_key = None
            data.model_key = None
            job["events"].notify()
            active_store.reset(token)

    async def get_job(self, job_id: str):
        if job_id in self.jobs:
            return self.jobs[job_id]
        persisted = await self.db_call("get_job", job_id)
        if persisted:
            if persisted.get("status") in {"processing", "pending"}:
                persisted.update(
                    status="failed",
                    error="The server restarted before this report was completed. Please research again.",
                )
            report = await self.db_call("get_report", job_id)
            if persisted.get("status") == "completed" and not (report or {}).get("report_content"):
                persisted.update(
                    status="failed",
                    error="This report could not be retrieved. Please research again.",
                )
            return {
                "company": persisted.get("inputs", {}).get("company", "Company"),
                "status": persisted.get("status"),
                "error": persisted.get("error"),
                "report": (report or {}).get("report_content"),
                "completed_steps": [],
            }
        raise HTTPException(404, "This research is unavailable or expired. Please start again.")
