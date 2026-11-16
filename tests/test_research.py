"""Contract checks use deterministic workers; they never call paid providers."""

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import application
from firmly_api.schemas import ResearchRequest
from firmly_engine.jobs import research_jobs
from firmly_engine.pipeline import ResearchPipeline

service = application.app.state.service


class FakeWorker:
    def __init__(self, field):
        self.field = field
        self.track_id = field

    async def run(self, state):
        yield {"type": "search_complete", "total_documents": 1}
        yield {
            self.field: {
                "https://example.org/source": {
                    "content": "Supported sample data",
                    "url": "https://example.org/source",
                }
            }
        }


class PassStage:
    async def run(self, state):
        return dict(state)


class FinishStage:
    async def run(self, state):
        assert all(
            state.get(k) for k in ["company_data", "industry_data", "financial_data", "news_data"]
        )
        return dict(
            state,
            report="# Test\n\n## Company Overview\nAll four worker outputs reached the report.",
        )


def fake_stages(pipeline):
    pipeline.context_stage = PassStage()
    for attr, field in [
        ("company_track", "company_data"),
        ("market_track", "industry_data"),
        ("financial_track", "financial_data"),
        ("news_track", "news_data"),
    ]:
        setattr(pipeline, attr, FakeWorker(field))
    for attr in ["gather_stage", "selection_stage", "reading_stage", "writing_stage"]:
        setattr(pipeline, attr, PassStage())
    pipeline.assembly_stage = FinishStage()


class GraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_workers_survive_graph_schema(self):
        with patch.object(ResearchPipeline, "_initialize_stages", fake_stages):
            updates = [step async for step in ResearchPipeline(company="Test").run({})]
        final = updates[-1]["assembly_stage"]
        self.assertIn("All four worker outputs", final["report"])
        self.assertEqual(1, sum("gather_stage" in s for s in updates))


class APITests(unittest.TestCase):
    def setUp(self):
        research_jobs.clear()
        application.api.state.rate.clear()
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.client = TestClient(application.app)

    def tearDown(self):
        self.env.stop()

    def test_custom_connection_contract_streams_a_complete_report(self):
        with (
            patch.object(ResearchPipeline, "_initialize_stages", fake_stages),
            TestClient(application.app) as client,
        ):
            response = client.post(
                "/api/research",
                json={
                    "company": "Contract test",
                    "search_key": "private-search-key",
                    "model_key": "private-model-key",
                },
            )
            self.assertEqual(202, response.status_code)
            job_id = response.json()["job_id"]
            stream = client.get(f"/api/research/{job_id}/stream")
            self.assertIn('"type": "complete"', stream.text)
            self.assertIn("company_track", stream.text)
            self.assertIn("assembly_stage", stream.text)
            self.assertNotIn("private-search-key", stream.text)
            self.assertNotIn("private-model-key", stream.text)
            self.assertEqual("completed", client.get(f"/api/research/{job_id}").json()["status"])

    def test_retry_request_reuses_job_without_starting_another_pipeline(self):
        from unittest.mock import AsyncMock

        request = {
            "company": "Example",
            "request_id": "12345678-1234-4234-8234-123456789abc",
            "search_key": "test-key",
            "model_key": "test-key",
        }
        with (
            patch.object(service, "process_research", new_callable=AsyncMock) as worker,
            TestClient(application.app) as client,
        ):
            first = client.post("/api/research", json=request)
            second = client.post("/api/research", json=request)
            self.assertEqual(202, first.status_code)
            self.assertEqual(first.json()["job_id"], second.json()["job_id"])
            self.assertEqual(1, len(research_jobs))
            self.assertEqual(1, worker.await_count)
            conflict = client.post("/api/research", json=dict(request, company="Different company"))
            self.assertEqual(409, conflict.status_code)
            self.assertEqual("Example", research_jobs[first.json()["job_id"]]["company"])

    def test_missing_keys_rejected_before_job_creation(self):
        response = self.client.post("/api/research", json={"company": "Acme"})
        self.assertEqual(409, response.status_code)
        self.assertEqual(0, len(research_jobs))

    def test_validation_and_config_do_not_disclose_keys(self):
        os.environ["FIRMLY_SEARCH_KEY"] = "secret-server-key"
        config = self.client.get("/api/config")
        self.assertNotIn("secret-server-key", config.text)
        for value in ["", "   ", "x" * 181]:
            self.assertEqual(
                422, self.client.post("/api/research", json={"company": value}).status_code
            )
        bad = self.client.post(
            "/api/research", json={"company": "Acme", "model_key": "secret" * 100}
        )
        self.assertEqual(422, bad.status_code)
        self.assertNotIn("secret", bad.text)

    def test_unsafe_website_rejected(self):
        for url in [
            "file:///etc/passwd",
            "https://user:password@example.org",
            "javascript:alert(1)",
        ]:
            self.assertEqual(
                422,
                self.client.post(
                    "/api/research", json={"company": "Acme", "company_url": url}
                ).status_code,
            )

    def test_sse_replay_and_retrieval(self):
        research_jobs["test"].update(status="completed", report="# Test", company="Acme")
        research_jobs["test"]["events"].extend(
            [
                {"type": "progress", "step": "company_context"},
                {"type": "progress", "step": "assembly_stage"},
            ]
        )
        first = self.client.get("/api/research/test/stream")
        self.assertIn("id: 1", first.text)
        self.assertIn("id: 2", first.text)
        second = self.client.get("/api/research/test/stream", headers={"Last-Event-ID": "1"})
        self.assertNotIn("id: 1", second.text)
        self.assertIn("id: 2", second.text)
        self.assertEqual(2, len(research_jobs["test"]["events"]))
        self.assertEqual("# Test", self.client.get("/api/research/test/report").json()["report"])

    def test_failed_job_has_terminal_event(self):
        research_jobs["failed"].update(status="failed", error="Check your service credentials.")
        response = self.client.get("/api/research/failed/stream")
        self.assertIn('"type": "error"', response.text)
        self.assertEqual(404, self.client.get("/api/research/missing").status_code)

    def test_pdf_contract_and_safe_markdown(self):
        response = self.client.post(
            "/api/generate-pdf",
            json={
                "report_content": "# A & B <C>\n\n## Company Overview\nText <script>raw</script> & **bold**.\n\n* First\n* [Source](https://example.org)\n\n| Heading | More |\n| --- | --- |\n| Data | Test |",
                "company_name": 'A/B "C"',
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn("application/pdf", response.headers["content-type"])

    def test_pdf_failure_is_recoverable(self):
        with patch.object(
            service.pdf, "export_report", return_value=(False, "secret provider detail")
        ):
            response = self.client.post("/api/generate-pdf", json={"report_content": "# Test"})
        self.assertEqual(500, response.status_code)
        self.assertNotIn("secret", response.text)

    def test_optional_persistence_returns_safe_public_fields(self):
        database = MagicMock()
        database.get_job.return_value = {
            "_id": object(),
            "inputs": {"company": "Stored company"},
            "status": "completed",
        }
        database.get_report.return_value = {"_id": object(), "report_content": "# Stored report"}
        with patch.object(service, "storage", database):
            response = self.client.get("/api/research/stored")
        self.assertEqual(200, response.status_code)
        self.assertEqual("# Stored report", response.json()["report"])
        self.assertNotIn("_id", response.text)

    def test_optional_persistence_failure_preserves_memory_report(self):
        research_jobs["memory"].update(
            status="completed", company="Memory company", report="# Memory"
        )
        database = MagicMock()
        database.get_job.side_effect = RuntimeError("database unavailable")
        with patch.object(service, "storage", database):
            response = self.client.get("/api/research/memory/report")
        self.assertEqual("# Memory", response.json()["report"])

    def test_oversized_body_rejected(self):
        response = self.client.post("/api/generate-pdf", content="x" * 600001)
        self.assertEqual(413, response.status_code)

    def test_job_capacity(self):
        os.environ.update(FIRMLY_SEARCH_KEY="fake", FIRMLY_MODEL_KEY="fake")
        for index in range(service.limits.concurrency):
            research_jobs[str(index)]["status"] = "processing"
        self.assertEqual(
            429, self.client.post("/api/research", json={"company": "Acme"}).status_code
        )


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_research_uses_same_graph_and_preserves_report(self):
        research_jobs.clear()
        research_jobs["integration"].update(company="Test", completed_steps=[])
        data = ResearchRequest(
            company="Test", search_key="private-key", model_key="private-model-key"
        )
        with patch.object(ResearchPipeline, "_initialize_stages", fake_stages):
            await service.process_research("integration", data)
        self.assertEqual("completed", research_jobs["integration"]["status"])
        self.assertIn("All four worker outputs", research_jobs["integration"]["report"])
        self.assertIsNone(data.search_key)
        self.assertIsNone(data.model_key)

    async def test_provider_exception_not_returned(self):
        research_jobs["error"].update(company="Test", completed_steps=[])
        with patch(
            "firmly_api.service.ResearchPipeline", side_effect=ValueError("secret-provider-key")
        ):
            await service.process_research("error", ResearchRequest(company="Test"))
        self.assertNotIn("secret", research_jobs["error"]["error"])


if __name__ == "__main__":
    unittest.main()
