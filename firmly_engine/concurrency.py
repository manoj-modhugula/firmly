"""Structured parallel work that cancels sibling operations on failure."""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


async def gather_tasks(*operations: Coroutine[Any, Any, T]) -> list[T]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(operation) for operation in operations]
    return [task.result() for task in tasks]
