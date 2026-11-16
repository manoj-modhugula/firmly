"""Bound request buffering and apply consistent API response headers."""

import asyncio
import time
from collections import deque

from starlette.responses import JSONResponse

from .config import Limits


class RequestLimits:
    def __init__(self, app, *, limits: Limits, buckets: dict):
        self.app = app
        self.limits = limits
        self.buckets = buckets

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def safe_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        async def reject(status, detail):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, safe_send)

        if scope["method"] == "POST":
            headers = dict(scope.get("headers", []))
            length = headers.get(b"content-length", b"")
            if length and (not length.isdigit() or int(length) > self.limits.body_bytes):
                return await reject(413, "The request is too large.")
            now = time.monotonic()
            for key, bucket in list(self.buckets.items()):
                if not bucket or now - bucket[-1] > self.limits.rate_window:
                    del self.buckets[key]
            host = scope.get("client", ("unknown",))[0]
            bucket = self.buckets.setdefault(host, deque())
            while bucket and now - bucket[0] > self.limits.rate_window:
                bucket.popleft()
            if len(bucket) >= self.limits.requests_per_window:
                return await reject(429, "Too many requests. Please try again in a few minutes.")
            bucket.append(now)
            body = bytearray()
            try:
                async with asyncio.timeout(20):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > self.limits.body_bytes:
                            return await reject(413, "The request is too large.")
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                return await reject(408, "The request timed out. Please try again.")
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            return await self.app(scope, bounded_receive, safe_send)
        await self.app(scope, receive, safe_send)
