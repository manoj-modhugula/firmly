"""Local deterministic browser test only. No provider requests or real claims."""

import asyncio
import os

os.environ.pop("FIRMLY_SEARCH_KEY", None)
os.environ.pop("FIRMLY_MODEL_KEY", None)
from firmly_engine.jobs import research_jobs
from firmly_engine.pipeline import ResearchPipeline
from tests.test_research import FakeWorker, PassStage, fake_stages


class SlowWorker(FakeWorker):
    async def run(self, state):
        await asyncio.sleep(12)
        async for event in super().run(state):
            yield event


class SlowStage(PassStage):
    async def run(self, state):
        await asyncio.sleep(1)
        return await super().run(state)


def browser_stages(pipeline):
    fake_stages(pipeline)
    for attr, field in [
        ("company_track", "company_data"),
        ("market_track", "industry_data"),
        ("financial_track", "financial_data"),
        ("news_track", "news_data"),
    ]:
        setattr(pipeline, attr, SlowWorker(field))
    for attr in ["gather_stage", "selection_stage", "reading_stage", "writing_stage"]:
        setattr(pipeline, attr, SlowStage())


ResearchPipeline._initialize_stages = browser_stages
if __name__ == "__main__":
    import uvicorn
    from fastapi.responses import JSONResponse

    import application

    async def test_models():
        return {"models": [{"id": "test:free", "name": "Test model (free)"}]}

    application.api.state.catalog.get = test_models
    failure_checks = 0

    @application.api.middleware("http")
    async def controlled_outage(request, call_next):
        global failure_checks
        if "/research/qa-reconnect" in request.url.path:
            if request.url.path.endswith("/stream"):
                if failure_checks <= 3:
                    return JSONResponse(
                        status_code=503, content={"detail": "Controlled test outage"}
                    )
            else:
                failure_checks += 1
                if failure_checks <= 3:
                    return JSONResponse(
                        status_code=503, content={"detail": "Controlled test outage"}
                    )
        return await call_next(request)

    research_jobs["qa-reconnect"].update(
        status="completed",
        company="Connection test",
        report="# Test\n\n## Company Overview\nExisting research was recovered without a new submission.",
        completed_steps=[],
    )
    research_jobs["qa-failed"].update(
        status="failed",
        company="Interface test",
        error="Research could not finish. Check your service connections and try again.",
    )
    uvicorn.run(application.app, host="127.0.0.1", port=8001)
