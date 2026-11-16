"""Regression checks for resource bounds, isolation, and failure recovery."""

import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from firmly_api.app import create_app
from firmly_api.catalog import ModelCatalog
from firmly_api.config import Limits
from firmly_api.middleware import RequestLimits
from firmly_api.schemas import ResearchRequest
from firmly_api.service import JobService
from firmly_engine.jobs import JobStore, ResearchEvents, active_store, publish_event
from firmly_engine.pipeline import ResearchPipeline
from firmly_engine.resources import connection_scope, resources
from firmly_engine.services.storage import ReportStore
from firmly_engine.stages.retrieve import SourceReadingStage
from tests.test_research import fake_stages


class EventTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_bounds_apply_to_append_and_extend(self):
        events = ResearchEvents()
        events.extend([{"type": "query_generating"}, {"type": "report_chunk"}])
        self.assertEqual([], events)
        events.extend({"type": "progress", "step": str(i)} for i in range(2050))
        self.assertEqual(2048, len(events))

    async def test_new_event_wakes_all_subscribers(self):
        events = ResearchEvents()
        tasks = [asyncio.create_task(events.wait(10, after=0)) for _ in range(2)]
        await asyncio.sleep(0)
        events.append({"type": "progress"})
        await asyncio.wait_for(asyncio.gather(*tasks), 0.1)
        await asyncio.wait_for(events.wait(10, after=0), 0.1)

    async def test_publication_isolated_to_bound_store_and_ignores_missing_jobs(self):
        first, second = JobStore(), JobStore()
        first["same"]
        second["same"]
        token = active_store.set(first)
        try:
            publish_event("same", {"type": "progress"})
            publish_event("missing", {"type": "progress"})
        finally:
            active_store.reset(token)
        self.assertEqual(1, len(first["same"]["events"]))
        self.assertEqual(0, len(second["same"]["events"]))
        self.assertNotIn("missing", first)

    async def test_pruning_keeps_active_jobs_and_removes_oldest_completed(self):
        jobs = JobStore()
        jobs["active"]["created_at"] = 0
        jobs["old"].update(status="completed", created_at=time.time() - 5)
        jobs["recent"].update(status="failed", created_at=time.time())
        jobs.prune(ttl=3600, capacity=3)
        self.assertEqual({"active", "recent"}, set(jobs))
        jobs["expired"].update(status="completed", created_at=0)
        jobs.prune(ttl=1, capacity=10)
        self.assertNotIn("expired", jobs)
        self.assertIn("active", jobs)


class BodyLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_chunked_body_stops_reading_at_limit(self):
        reads = 0
        chunks = iter([b"1234", b"5678", b"never-read"])

        async def receive():
            nonlocal reads
            reads += 1
            return {"type": "http.request", "body": next(chunks), "more_body": True}

        messages = []

        async def send(message):
            messages.append(message)

        app = AsyncMock()
        middleware = RequestLimits(app, limits=Limits(body_bytes=6), buckets={})
        await middleware(
            {"type": "http", "method": "POST", "headers": [], "client": ("test", 1)}, receive, send
        )
        self.assertEqual(2, reads)
        self.assertEqual(413, messages[0]["status"])
        app.assert_not_awaited()
        self.assertIn((b"x-content-type-options", b"nosniff"), messages[0]["headers"])

    async def test_valid_chunked_body_replayed_once_and_disconnect_preserved(self):
        chunks = iter(
            [
                {"type": "http.request", "body": b"one", "more_body": True},
                {"type": "http.request", "body": b"two", "more_body": False},
                {"type": "http.disconnect"},
            ]
        )

        async def receive():
            return next(chunks)

        async def app(scope, receive, send):
            self.assertEqual(b"onetwo", (await receive())["body"])
            self.assertEqual("http.disconnect", (await receive())["type"])

        await RequestLimits(app, limits=Limits(), buckets={})(
            {"type": "http", "method": "POST", "headers": [], "client": ("test", 1)},
            receive,
            AsyncMock(),
        )


class ResourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_pools_reused_and_closed_on_failure(self):
        with self.assertRaises(ValueError):
            async with connection_scope() as owner:
                web = owner.web_client()
                sync, asynchronous = owner.model_clients()
                self.assertIs(web, owner.web_client())
                self.assertIs(asynchronous, owner.model_clients()[1])
                raise ValueError("controlled")
        self.assertTrue(web.is_closed)
        self.assertTrue(sync.is_closed)
        self.assertTrue(asynchronous.is_closed)
        self.assertIsNone(resources.get())

    async def test_service_cancels_tasks_and_clears_credentials(self):
        service = JobService(jobs=JobStore())
        data = ResearchRequest(company="Test", search_key="private", model_key="private")
        started = asyncio.Event()

        class WaitingPipeline:
            def __init__(self, **kwargs):
                pass

            async def run(self, thread):
                started.set()
                await asyncio.sleep(100)
                yield {}

        with patch("firmly_api.service.ResearchPipeline", WaitingPipeline):
            result = service.submit(data)
            await started.wait()
            await service.close()
        self.assertEqual("failed", service.jobs[result["job_id"]]["status"])
        self.assertIsNone(data.search_key)
        self.assertIsNone(data.model_key)
        self.assertFalse(service.tasks)

    async def test_timeout_fails_without_leaking_provider_details(self):
        service = JobService(jobs=JobStore(), limits=Limits(research_timeout=0.001))

        class SlowPipeline:
            def __init__(self, **kwargs):
                pass

            async def run(self, thread):
                await asyncio.sleep(10)
                yield {}

        data = ResearchRequest(company="Test", search_key="private", model_key="private")
        with patch("firmly_api.service.ResearchPipeline", SlowPipeline):
            await service.process_research("test", data)
        self.assertEqual("failed", service.jobs["test"]["status"])
        self.assertIn("too long", service.jobs["test"]["error"])
        self.assertIsNone(data.search_key)

    async def test_custom_job_store_receives_pipeline_events(self):
        service = JobService(jobs=JobStore())
        data = ResearchRequest(company="Test")
        with patch.object(ResearchPipeline, "_initialize_stages", fake_stages):
            await service.process_research("isolated", data)
        events = service.jobs["isolated"]["events"]
        self.assertTrue(any(event["type"] == "search_complete" for event in events))
        self.assertEqual("completed", service.jobs["isolated"]["status"])

    async def test_extraction_concurrency_shared_across_categories_and_urls_deduplicated(self):
        connection = MagicMock()
        current = peak = calls = 0

        async def extract(url, **kwargs):
            nonlocal current, peak, calls
            current += 1
            calls += 1
            peak = max(peak, current)
            await asyncio.sleep(0.002)
            current -= 1
            return {"results": [{"raw_content": url}]}

        connection.extract = extract
        with patch("firmly_engine.stages.retrieve.open_web_connection", return_value=connection):
            stage = SourceReadingStage()
        await asyncio.gather(
            stage.fetch_raw_content(["a", "a", "b", "c", "d"]),
            stage.fetch_raw_content(["e", "f", "g", "h"]),
        )
        self.assertLessEqual(peak, 3)
        self.assertEqual(8, calls)


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_catalog_requests_share_refresh_and_use_stale_cache_on_failure(self):
        count = 0

        async def handler(request):
            nonlocal count
            count += 1
            await asyncio.sleep(0.002)
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "test:free", "name": "Test"},
                        {"id": "image", "architecture": {"output_modalities": ["image"]}},
                    ]
                },
            )

        catalog = ModelCatalog()
        catalog.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            first, second = await asyncio.gather(catalog.get(), catalog.get())
            self.assertEqual(first, second)
            self.assertEqual(1, count)
            self.assertEqual(["test:free"], [m["id"] for m in first["models"]])
            catalog.fetched_at = 0
            await catalog.client.aclose()
            catalog.client = None
            self.assertEqual(first, await catalog.get())
        finally:
            await catalog.close()


class PersistenceTests(unittest.TestCase):
    def test_storage_writes_are_upserts_with_timezone_aware_dates_and_close(self):
        with patch("firmly_engine.services.storage.MongoClient") as client:
            store = ReportStore("mongodb://localhost")
        store.create_job("same", {"company": "Test"})
        store.store_report("same", {"report": "# Test"})
        self.assertTrue(store.jobs.update_one.call_args.kwargs["upsert"])
        created = store.jobs.update_one.call_args.args[1]["$setOnInsert"]["created_at"]
        self.assertIsNotNone(created.tzinfo)
        self.assertTrue(store.reports.update_one.call_args.kwargs["upsert"])
        store.close()
        client.return_value.close.assert_called_once()

    def test_limits_and_headers_apply_to_error_responses(self):
        service = JobService(jobs=JobStore(), limits=Limits(requests_per_window=1))
        with TestClient(create_app(service)) as client:
            first = client.post("/api/research", json={"company": "Test"})
            second = client.post("/api/research", json={"company": "Test"})
        self.assertEqual(429, second.status_code)
        for response in [first, second]:
            self.assertEqual("nosniff", response.headers["x-content-type-options"])


class StructuredConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_failing_briefing_cancels_its_siblings(self):
        from firmly_engine.concurrency import gather_tasks

        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def waiting():
            started.set()
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()

        async def failing():
            await started.wait()
            raise ValueError("controlled failure")

        with self.assertRaises(ExceptionGroup):
            await gather_tasks(waiting(), failing())
        self.assertTrue(cancelled.is_set())


class FullPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stages_complete_with_mocked_service_boundaries(self):
        from contextlib import ExitStack

        from langchain_core.messages import AIMessage
        from langchain_core.runnables import RunnableLambda

        class WebConnection:
            async def search(self, query, **kwargs):
                return {
                    "results": [
                        {
                            "url": "https://example.org/company",
                            "title": "Test company",
                            "content": "Test company provides software and announced a product.",
                            "score": 0.9,
                        }
                    ]
                }

            async def extract(self, url, **kwargs):
                return {
                    "results": [
                        {
                            "url": url,
                            "raw_content": "Test company provides software. Its product announcement is documented here.",
                        }
                    ]
                }

        def model(role, config=None, **kwargs):
            if role == "research":
                text = "Test company products\nTest company recent news\n"
            elif role == "briefing":
                text = "## Company Overview\nTest company provides software. [Source](https://example.org/company)"
            else:
                text = "# Test company\n\n## Conversation Briefing\nPrepare questions about its product.\n\n## Company Overview\nTest company provides software.\n\n## Industry Overview\nSoftware.\n\n## Financial Overview\nFinancial details were not disclosed.\n\n## News\nA product announcement was found."
            return RunnableLambda(lambda prompt: AIMessage(content=text))

        service = JobService(jobs=JobStore())
        with ExitStack() as stack:
            for module in [
                "firmly_engine.stages.tracks.shared",
                "firmly_engine.stages.summarize",
                "firmly_engine.stages.compose",
            ]:
                stack.enter_context(patch(f"{module}.create_research_model", side_effect=model))
            for module in ["firmly_engine.stages.tracks.shared", "firmly_engine.stages.retrieve"]:
                stack.enter_context(
                    patch(f"{module}.open_web_connection", return_value=WebConnection())
                )
            await service.process_research("real-stages", ResearchRequest(company="Test company"))
        job = service.jobs["real-stages"]
        self.assertEqual("completed", job["status"], job.get("error"))
        self.assertIn("https://example.org/company", job["report"])
        self.assertIn("## References", job["report"])
        self.assertEqual(10, len(job["completed_steps"]))
        event_types = {event["type"] for event in job["events"]}
        self.assertTrue(
            {
                "research_init",
                "search_complete",
                "curation",
                "enrichment",
                "briefing_complete",
                "report_compilation",
            }
            <= event_types
        )


class ServiceBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_adapters_share_owned_transports_without_requests(self):
        from firmly_engine.connections import open_web_connection
        from firmly_engine.models import ModelSettings, create_research_model

        async with connection_scope() as owner:
            first = open_web_connection("test-key")
            second = open_web_connection("test-key")
            self.assertIs(first._client, second._client)
            self.assertIs(first._client, owner.web_client())
            model = create_research_model("research", ModelSettings(model_key="test-key"))
            self.assertIs(model.http_async_client, owner.model_clients()[1])
            self.assertNotIn("test-key", repr(ModelSettings(model_key="test-key")))
        self.assertTrue(model.http_async_client.is_closed)

    async def test_completed_persisted_job_without_report_has_recoverable_failure(self):
        service = JobService(jobs=JobStore())
        service.storage = MagicMock()
        service.storage.get_job.return_value = {
            "status": "completed",
            "inputs": {"company": "Test"},
        }
        service.storage.get_report.return_value = None
        job = await service.get_job("stored")
        self.assertEqual("failed", job["status"])
        self.assertIn("retrieved", job["error"])


class EventPayloadTests(unittest.TestCase):
    def test_source_bodies_are_not_retained_in_progress_history(self):
        jobs = JobStore()
        jobs["test"]
        jobs.publish(
            "test",
            {
                "type": "search_complete",
                "total_documents": 1,
                "merged_docs": {"private": "large source body"},
                "search_key": "private-key",
            },
        )
        self.assertEqual(
            {"type": "search_complete", "total_documents": 1}, jobs["test"]["events"][0]
        )


class SourceURLTests(unittest.IsolatedAsyncioTestCase):
    async def test_curation_preserves_distinct_query_based_sources(self):
        from firmly_engine.stages.rank import SourceSelectionStage

        state = {
            "company": "Test",
            "company_data": {
                f"https://example.org/article?id={i}": {
                    "url": f"https://example.org/article?id={i}",
                    "title": f"Source {i}",
                    "content": "Evidence",
                    "score": 0.9,
                }
                for i in [1, 2]
            },
        }
        result = await SourceSelectionStage().run(state)
        self.assertEqual(2, len(result["curated_company_data"]))
        self.assertEqual(2, len(result["references"]))
        self.assertTrue(all("?id=" in url for url in result["references"]))

    async def test_source_url_validation_rejects_unsafe_protocols_and_credentials(self):
        from firmly_engine.formatting.references import normalize_url

        for url in [
            "file:///etc/passwd",
            "javascript://alert(1)",
            "https://user:password@example.org",
            "https://[invalid",
        ]:
            self.assertEqual("", normalize_url(url))
        self.assertEqual(
            "https://example.org/a/?id=1", normalize_url("https://example.org/a/?id=1#section")
        )
