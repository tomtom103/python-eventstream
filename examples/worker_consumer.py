import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import anyio
from redis.asyncio import ConnectionPool

from eventstream.client import EventStreamClient
from eventstream.models import Consumer


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
        client = await stack.enter_async_context(EventStreamClient(pool))

        header_consumer = await stack.enter_async_context(
            client.subscribe("api-header-publisher")
        )
        counter_consumer = await stack.enter_async_context(
            client.subscribe("api-call-counter")
        )

        async def consume(consumer: Consumer) -> None:
            async for message in consumer:
                if message is None:
                    raise Exception("End of stream")
                print(
                    f"Received event: {message.message} from channel: {message.channel}"
                )

        async with anyio.create_task_group() as tg:
            tg.start_soon(consume, header_consumer)
            tg.start_soon(consume, counter_consumer)


if __name__ == "__main__":
    asyncio.run(main())
