import asyncio
from typing import Any, Self

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ResponseError

from eventstream.models import Event

StreamMessageType = tuple[bytes, tuple[tuple[bytes, dict[bytes, bytes]]]]


class RedisStreamBackend:
    def __init__(self, pool: ConnectionPool) -> None:
        self._client = Redis(connection_pool=pool)
        self._streams: dict[
            bytes | str | memoryview, int | bytes | str | memoryview
        ] = {}
        self._ready = asyncio.Event()

    async def publish(self, channel: str, message: Any) -> None:
        print(f"Publishing message on channel: {channel}")
        res = await self._client.xadd(channel, {"message": message})
        print(f"Response was: {res}")

    async def subscribe(self, channel: str) -> None:
        try:
            info = await self._client.xinfo_stream(channel)
            print(f"xinfo_stream: {info}")
            last_id = info["last-generated-id"]
        except ResponseError as e:
            print(f"foo: {repr(e)}")
            last_id = "0"
        self._streams[channel] = last_id
        self._ready.set()

    async def unsubscribe(self, channel: str) -> None:
        self._streams.pop(channel, None)

    async def _wait_for_messages(self) -> list[StreamMessageType]:
        await self._ready.wait()
        messages = None
        while not messages:
            messages = await self._client.xread(self._streams, count=1, block=100)
        return messages

    async def next_published(self) -> Event:
        messages = await self._wait_for_messages()
        stream, events = messages[0]
        _msg_id, message = events[0]
        self._streams[stream.decode("utf-8")] = _msg_id.decode("utf-8")
        return Event(
            channel=stream.decode("utf-8"),
            message=message.get(b"message", b"").decode("utf-8"),
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self._client.aclose()
