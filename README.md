# Firmly

Company research, in perspective. Research a company, follow progress, and review a briefing covering its business, industry, financials, and news. Explore linked sources, evidence gaps, and suggested questions, or export the report as a PDF.

## Run locally

Requires Python 3.11+ and Node 22.13+.

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt -c requirements.lock.txt
npm ci --prefix ui
npm run build --prefix ui
.venv/bin/uvicorn application:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The **Explore sample report** action works without any API keys and is a saved, source-backed Cursor example covering announcements through November 13, 2025, clearly labelled with its period and not updated live.

For frontend development, keep the API running and use `npm run dev --prefix ui` on http://127.0.0.1:5174. The Vite proxy targets the local API.

## Live research

Copy `.env.example` to `.env` and add `FIRMLY_SEARCH_KEY` plus `FIRMLY_MODEL_KEY`, then restart Python. Alternatively, enter both keys in Model settings; those keys stay in tab memory and clear on reload. No keys are saved to browser storage or included in report persistence.

The default is automatic free model selection. Create the external service keys described in [Connection setup](docs/CONNECTIONS.md), then enter them under **Model access key** and **Web research key**. The external services control usage quotas and any optional paid settings. No paid fallback is configured for automatic free selection.

The pipeline grounds the company, researches four areas in parallel, collects and curates sources, retrieves source content, writes briefings, and edits the report. Progress displays pipeline stage events. Reference lists are preserved after model editing; they do not guarantee that every generated claim is correct.

## Verification

```sh
.venv/bin/python -m unittest discover -s tests -v
npm test --prefix ui
npm run build --prefix ui
```

The tests use deterministic workers and never call paid APIs. `tests/browser_fixture.py` is a local browser test fixture, not a production server or real research demo.

For all frontend checks, run `npm run check --prefix ui`. Install Python development tools with `.venv/bin/pip install -r requirements-dev.txt`, then run `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`.

See [Architecture](docs/ARCHITECTURE.md), [Validation](docs/VALIDATION.md), and [Code review](docs/REFACTOR_REVIEW.md) for module boundaries, verification, and remaining release checks.

## Project structure

- `ui/src/components`: homepage, settings, progress, reports, notices, and navigation.
- `ui/src/lib`: typed API client, report section parsing, progress mapping, and saved Cursor example.
- `ui/src/hooks`: workspace coordination, navigation, settings return behavior, and research state.
- `firmly_engine`: research pipeline, stages, instructions, provider selection, source references, and PDF export.
- `firmly_api`: routes, request schemas, job lifecycle, middleware, model catalog, and interface hosting.
- `application.py`: ASGI server entry point.

## Runtime and deployment

### Portfolio on Vercel

Import this repository with **Root Directory** set to `ui`. The included `ui/vercel.json` builds the portfolio version with `npm run build:portfolio`. It serves the homepage, saved Cursor report, source links, and a downloadable PDF without a backend or API keys. Research and settings actions explain that live research is not connected and offer the sample report.

The build mode is selected by `ui/.env.portfolio`, which contains a public feature flag only. The regular `npm run build --prefix ui` keeps the full API-backed application. The portfolio PDF in `ui/public/samples/cursor-report.pdf` is exported from `SAMPLE_REPORT` using `ReportPDFExporter`; regenerate it when updating the saved report.

### Full application

The production command serves the compiled UI and API from one Python process. Use one worker: active jobs and replay history are held in process memory. Active jobs do not survive restart. Without MongoDB, creating new jobs cleans up completed reports older than one hour, or earlier when the 100-job capacity is reached. A reload reconnects by its opaque job URL; a missing job offers a new run instead of silently duplicating it.

MongoDB is optional. Set `FIRMLY_STORAGE_URI` to persist completed reports in the `firmly` database. MongoDB errors do not discard an otherwise completed in-memory report. The optional database path has contract coverage only when a database is supplied; no database is configured for this local build.

Deploy to a Python/ASGI host with long-lived streaming support, one process, and a reverse-proxy idle timeout of at least 60 seconds. SSE sends heartbeats every 10 seconds. Do not deploy the Python API on static-only hosting. Before exposing a shared installation with owner-funded keys publicly, add appropriate access control and shared quotas; the current per-process rate and concurrency limits are intended for a local or controlled demo.

Research is limited to 15 minutes and three active jobs. POST requests are bounded to 600KB and 20 requests per IP per 10 minutes. API errors hide provider exception details. No account, saved-library interface, comparisons, monitoring, chat, or billing is included.

Research submissions accept an optional UUID `request_id`. Repeating an accepted request reuses its job rather than launching another provider run; changing its company context returns a conflict. The browser retains only pending request metadata (ID and company details) in tab session storage for recovery. API credentials remain in memory and clear on reload.

## Attribution

Third-party attribution and licensing are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [LICENSE](LICENSE).
