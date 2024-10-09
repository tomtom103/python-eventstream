import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import anyio
from pydantic import BaseModel
from redis.asyncio import ConnectionPool

from eventstream.client import EventStreamClient
from eventstream.models import EventStream


class ObservabilityMessage(BaseModel):
    event_type: str
    value: str


class CounterMessage(BaseModel):
    count: int


@asynccontextmanager
async def redis_pool(url: str) -> AsyncIterator[ConnectionPool]:
    pool = ConnectionPool.from_url(url)
    try:
        yield pool
    finally:
        await pool.aclose()


async def main() -> None:
    async with AsyncExitStack() as stack:
        pool = await stack.enter_async_context(redis_pool("redis://localhost:6379"))
        client = await stack.enter_async_context(EventStreamClient[Any](pool))

        observability_stream: EventStream[ObservabilityMessage] = (
            await stack.enter_async_context(
                client.subscribe("observability-event-stream")
            )
        )
        counter_stream: EventStream[CounterMessage] = await stack.enter_async_context(
            client.subscribe("counter-event-stream")
        )

        async def consume[T: BaseModel](stream: EventStream[T]) -> None:
            async for event in stream:
                if event is None:
                    raise Exception("End of stream")
                print(f"Received event: {event.message} from channel: {event.channel}")

        async with anyio.create_task_group() as tg:
            tg.start_soon(consume, observability_stream)
            tg.start_soon(consume, counter_stream)


if __name__ == "__main__":
    asyncio.run(main())
