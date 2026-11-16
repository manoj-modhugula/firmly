"""Per-run HTTP connection pools, released on completion, failure, or cancellation."""

from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar

import httpx


class ConnectionResources:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.web: httpx.AsyncClient | None = None
        self.model_async: httpx.AsyncClient | None = None
        self.model_sync: httpx.Client | None = None

    def web_client(self) -> httpx.AsyncClient:
        if self.web is None:
            self.web = httpx.AsyncClient(timeout=30)
            self.stack.push_async_callback(self.web.aclose)
        return self.web

    def model_clients(self) -> tuple[httpx.Client, httpx.AsyncClient]:
        if self.model_async is None:
            self.model_async = httpx.AsyncClient(timeout=90)
            self.model_sync = httpx.Client(timeout=90)
            self.stack.push_async_callback(self.model_async.aclose)
            self.stack.callback(self.model_sync.close)
        return self.model_sync, self.model_async


resources: ContextVar[ConnectionResources | None] = ContextVar("firmly_connections", default=None)


@asynccontextmanager
async def connection_scope():
    owner = ConnectionResources()
    token = resources.set(owner)
    try:
        async with owner.stack:
            yield owner
    finally:
        resources.reset(token)
