"""Cached model catalog with one refresh per application process."""

import asyncio
import logging
import time

import httpx
from fastapi import HTTPException

from firmly_engine.connections import MODEL_GATEWAY_ENDPOINT

logger = logging.getLogger("firmly.catalog")


class ModelCatalog:
    def __init__(self):
        self.client: httpx.AsyncClient | None = None
        self.models: list[dict[str, str]] = []
        self.fetched_at = 0.0
        self.lock = asyncio.Lock()

    async def open(self):
        self.client = httpx.AsyncClient(timeout=15)

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    async def get(self):
        if self.models and time.monotonic() - self.fetched_at < 3600:
            return {"models": self.models}
        async with self.lock:
            if self.models and time.monotonic() - self.fetched_at < 3600:
                return {"models": self.models}
            try:
                if self.client is None:
                    raise RuntimeError("Model catalog has not started")
                response = await self.client.get(f"{MODEL_GATEWAY_ENDPOINT}/models")
                response.raise_for_status()
                data = response.json()["data"]
                if not isinstance(data, list):
                    raise ValueError("Invalid model catalog")
                models = []
                for model in data:
                    if not isinstance(model, dict) or not isinstance(model.get("id"), str):
                        continue
                    architecture = model.get("architecture")
                    architecture = architecture if isinstance(architecture, dict) else {}
                    if "text" not in (architecture.get("output_modalities") or ["text"]):
                        continue
                    name = model.get("name")
                    models.append(
                        {
                            "id": model["id"],
                            "name": name if isinstance(name, str) and name else model["id"],
                        }
                    )
                self.models = models
                self.fetched_at = time.monotonic()
            except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError):
                logger.warning("Model catalog refresh unavailable")
                if not self.models:
                    raise HTTPException(
                        502,
                        "Model choices are unavailable right now. Automatic selection remains available.",
                    ) from None
            return {"models": self.models}
