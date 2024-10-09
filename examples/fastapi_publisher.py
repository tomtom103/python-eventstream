from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import ConnectionPool

from eventstream.client import EventStreamClient


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


async def event_client() -> AsyncIterator[EventStreamClient[Any]]:
    async with redis_pool("redis://localhost:6379") as pool:
        yield EventStreamClient[Any](pool)


EventClient = Annotated[EventStreamClient[Any], Depends(event_client)]

app = FastAPI(debug=True)

COUNTER_LUA = """local current = redis.call('get', KEYS[1])
if current == nil then current = 0 end
return redis.call('incrby', KEYS[1], 1)
"""


@app.get("/foo")
async def get_foo(client: EventClient, request: Request) -> JSONResponse:
    await client.publish(
        "observability-event-stream",
        ObservabilityMessage(event_type="GET", value=str(request.url)),
    )

    counter_script = client._client.register_script(COUNTER_LUA)
    call_count = await counter_script(keys=(str(request.url),))
    await client.publish(
        "counter-event-stream", CounterMessage.model_validate({"count": call_count})
    )
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
