"""External service boundary. Provider identifiers here are integration contracts."""

import os

from langchain_openai import ChatOpenAI as CompatibleChatModel
from tavily import AsyncTavilyClient as WebResearchTransport

from .resources import resources

MODEL_GATEWAY_ENDPOINT = "https://openrouter.ai/api/v1"
AUTOMATIC_MODEL_ID = "openrouter/free"
DIRECT_MODEL_IDS = {"research": "gpt-5.1", "briefing": "gpt-5.1", "report": "gpt-4o"}
BRIEFING_MODEL_ID = "gemini-2.5-flash"


def open_web_connection(search_key=None):
    key = (search_key or "").strip() or os.getenv("FIRMLY_SEARCH_KEY")
    if not key:
        raise ValueError("Add a web research key in Firmly settings.")
    owner = resources.get()
    return WebResearchTransport(api_key=key, client=owner.web_client() if owner else None)


def open_briefing_connection(model, key):
    from langchain_google_genai import ChatGoogleGenerativeAI

    connection = ChatGoogleGenerativeAI(
        model=model, temperature=0, google_api_key=key, max_retries=0, timeout=90
    )
    owner = resources.get()
    if owner:

        async def close_connection():
            if connection.async_client_running is not None:
                await connection.async_client_running.transport.close()
            connection.client.transport.close()

        owner.stack.push_async_callback(close_connection)
    return connection


__all__ = [
    "CompatibleChatModel",
    "MODEL_GATEWAY_ENDPOINT",
    "AUTOMATIC_MODEL_ID",
    "DIRECT_MODEL_IDS",
    "BRIEFING_MODEL_ID",
    "open_web_connection",
    "open_briefing_connection",
]
