import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from redis.asyncio import ConnectionPool

from eventstream.client import EventStreamClient


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

        async with client.subscribe('api-access-publisher') as consumer:
            async for message in consumer:
                print(f"Received event: {message.message} from channel: {message.channel}")

if __name__ == "__main__":
    asyncio.run(main())
