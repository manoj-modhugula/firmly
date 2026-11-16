# Changes: request attribution.
"""Firmly model connections and per-request settings."""

import os
from dataclasses import dataclass, field
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from .connections import (
    AUTOMATIC_MODEL_ID,
    BRIEFING_MODEL_ID,
    DIRECT_MODEL_IDS,
    MODEL_GATEWAY_ENDPOINT,
    CompatibleChatModel,
    open_briefing_connection,
)
from .resources import resources

DEFAULT_RESEARCH_MODEL = AUTOMATIC_MODEL_ID

Role = Literal["research", "briefing", "report"]


@dataclass(frozen=True)
class ModelSettings:
    model_key: str | None = field(default=None, repr=False)
    model: str | None = None

    @classmethod
    def resolve(cls, model_key: str | None = None, model: str | None = None) -> "ModelSettings":
        """Merge request-supplied settings with environment fallbacks."""
        key = (model_key or "").strip() or os.getenv("FIRMLY_MODEL_KEY")
        model = (model or "").strip() or os.getenv("FIRMLY_MODEL") or DEFAULT_RESEARCH_MODEL
        return cls(model_key=key or None, model=model)

    @property
    def uses_gateway(self) -> bool:
        return bool(self.model_key)


def create_research_model(
    role: Role, config: ModelSettings | None = None, *, streaming: bool = False
) -> BaseChatModel:
    config = config or ModelSettings.resolve()

    owner = resources.get()
    transport = {}
    if owner:
        sync_client, async_client = owner.model_clients()
        transport = {"http_client": sync_client, "http_async_client": async_client}

    if config.uses_gateway:
        return CompatibleChatModel(
            **transport,
            model=config.model or DEFAULT_RESEARCH_MODEL,
            temperature=0,
            streaming=streaming,
            api_key=config.model_key,
            base_url=MODEL_GATEWAY_ENDPOINT,
            timeout=90,
            max_retries=1,
            default_headers={
                "HTTP-Referer": os.getenv("FIRMLY_ORIGIN", "http://localhost"),
                "X-Title": "Firmly",
            },
        )

    briefing_key = os.getenv("FIRMLY_BRIEFING_KEY")
    if role == "briefing" and briefing_key:
        return open_briefing_connection(BRIEFING_MODEL_ID, briefing_key)

    direct_key = os.getenv("FIRMLY_DIRECT_MODEL_KEY")
    if not direct_key:
        raise ValueError(
            "No model connection configured. Add a model access key in Firmly settings, "
            "or set FIRMLY_MODEL_KEY (or FIRMLY_DIRECT_MODEL_KEY) in the backend .env file."
        )
    return CompatibleChatModel(
        **transport,
        model=DIRECT_MODEL_IDS[role],
        temperature=0,
        streaming=streaming,
        api_key=direct_key,
        timeout=90,
        max_retries=1,
    )
