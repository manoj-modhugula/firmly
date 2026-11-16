"""Application paths, environment bootstrap, and resource limits."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)
os.environ.setdefault("LANGSMITH_TRACING", "false")


@dataclass(frozen=True)
class Limits:
    max_jobs: int = 100
    job_ttl: int = 3600
    research_timeout: float = 900
    concurrency: int = 3
    body_bytes: int = 600_000
    requests_per_window: int = 20
    rate_window: int = 600
