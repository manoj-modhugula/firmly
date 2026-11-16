# Firmly validation

## Automated checks

Current suite: 37 backend tests and 22 frontend tests. Full cleanup results are recorded in [Code review](REFACTOR_REVIEW.md).

Backend checks cover request validation, credential redaction, pipeline integration, job lifecycle, replayable progress events, report retrieval, PDF handling, request limits, and submission recovery. Frontend checks cover report parsing, source links, progress handling, navigation helpers, and request recovery.

```sh
.venv/bin/python -m unittest discover -s tests -v
npm test --prefix ui
npm run build --prefix ui
```

The frontend production build and automated checks have passed locally. Tests use deterministic workers and do not validate external provider output.

## Browser checks

- Research submission, streamed progress, completion, report navigation, and PDF download using controlled test workers.
- Reload reconnection and interrupted-request recovery without duplicate research jobs.
- Missing configuration, failed research, unavailable reports, and export error recovery.
- Settings navigation, report section restoration, and browser Back/Forward behavior.
- Desktop layouts at 1280px and 1440px; narrow layouts at 390px and 320px.
- Readable 16px inputs and report body text; contained scrolling for report tabs and wide tables.
- Homepage research prompt dismissal by typing, outside click, and Escape.
- A single homepage sample-report action in the preview card.

The saved Cursor example contains editorial research with linked sources covering announcements through November 13, 2025. It is a historical example, not a live-generated report.

For controlled browser testing:

```sh
.venv/bin/python -m tests.browser_fixture
```

The fixture binds to `127.0.0.1:8001`. The application runs separately on port 8000.

## Remaining verification

- Live research quality, claim-to-source accuracy, provider latency, and free-model availability require configured service credentials.
- MongoDB persistence has contract coverage with a stub; real database connectivity and restart recovery remain unverified.
- A complete accessibility audit and broad PDF Unicode/script checks remain outstanding.
- Public hosting and Docker image execution have not been verified.

## Runtime limits

Use one application worker. Active jobs and event history are held in process memory and do not survive restart. Completed reports can optionally be persisted to MongoDB. Local rate and concurrency limits do not provide public authentication or shared usage quotas.
