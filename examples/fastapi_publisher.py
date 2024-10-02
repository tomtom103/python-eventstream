import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
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
    async with redis_pool("redis://localhost:6379") as pool:
        yield EventStreamClient(pool)

EventClient = Annotated[EventStreamClient, Depends(event_client)]

app = FastAPI(debug=True)

@app.get("/foo")
async def get_foo(client: EventClient, request: Request) -> JSONResponse:
    headers = dict(request.headers)
    await client.publish('api-access-publisher', json.dumps({"headers": headers}))
    return JSONResponse({"status": "ok"})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
