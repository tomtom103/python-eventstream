from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, WebSocket
from redis.asyncio import ConnectionPool

from eventstream.client import EventStreamClient


@asynccontextmanager
async def redis_pool(url: str) -> AsyncIterator[ConnectionPool]:
    pool = ConnectionPool.from_url(url)
    try:
        yield pool
    finally:
        await pool.aclose()


async def event_client() -> AsyncIterator[EventStreamClient]:
    async with redis_pool("redis://localhost") as pool:
        yield EventStreamClient(pool)


EventClient = Annotated[EventStreamClient, Depends(event_client)]

app = FastAPI(debug=True)


# Forward incoming messages from the consumer
# Into a websocket (to be consumed by a Web client)
@app.websocket("/ws")
async def ws(websocket: WebSocket, client: EventClient) -> None:
    await websocket.accept()

    async with client.subscribe("api-access-bus") as consumer:
        async for message in consumer:
            if message is not None:
                await websocket.send_text(message.message)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
