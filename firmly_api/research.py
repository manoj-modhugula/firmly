"""Research HTTP routes and safe public event serialization.
Changes: API routing, bounded streaming, and safe export integration.
"""

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from firmly_engine.jobs import ResearchEvents, public_event

from .schemas import PDFRequest, ResearchRequest

router = APIRouter()


@router.post("/research", status_code=202)
async def research(data: ResearchRequest, request: Request):
    return request.app.state.service.submit(data)


def public_job(job):
    return {
        key: job.get(key)
        for key in ["status", "company", "report", "error", "current_step", "completed_steps"]
    }


@router.get("/research/{job_id}")
async def status(job_id: str, request: Request):
    return public_job(await request.app.state.service.get_job(job_id))


@router.get("/research/{job_id}/report")
async def report(job_id: str, request: Request):
    job = await request.app.state.service.get_job(job_id)
    if job.get("report"):
        return {"report": job["report"], "company": job.get("company")}
    return JSONResponse(status_code=202, content=public_job(job))


@router.get("/research/{job_id}/stream")
async def stream(job_id: str, request: Request):
    job = await request.app.state.service.get_job(job_id)
    try:
        cursor = max(0, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        cursor = 0

    async def events():
        nonlocal cursor
        last_heartbeat = time.monotonic()
        while not await request.is_disconnected():
            queue = job.get("events", [])
            while cursor < len(queue):
                event = queue[cursor]
                cursor += 1
                # Intermediate provider errors are not public and may be recoverable.
                if event.get("type") in {"error", "query_error"}:
                    continue
                # Large source payloads stay on the server.
                safe = public_event(event)
                yield f"id: {cursor}\ndata: {json.dumps(safe)}\n\n"
            if job["status"] in {"completed", "failed"}:
                event = (
                    {"type": "complete", "report": job.get("report"), "company": job.get("company")}
                    if job["status"] == "completed"
                    else {"type": "error", "error": job.get("error")}
                )
                yield f"data: {json.dumps(event)}\n\n"
                break
            if time.monotonic() - last_heartbeat > 10:
                yield ": heartbeat\n\n"
                last_heartbeat = time.monotonic()
            if isinstance(queue, ResearchEvents):
                await queue.wait(timeout=1, after=cursor)
            else:
                await asyncio.sleep(0.15)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate-pdf")
async def pdf(data: PDFRequest, request: Request):
    success, result = await asyncio.to_thread(
        request.app.state.service.pdf.export_report, data.report_content, data.company_name
    )
    if not success:
        raise HTTPException(
            500, "PDF export failed. Your report is still available; please try again."
        )
    buffer, filename = result
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/health")
async def health():
    return {"status": "ok"}
