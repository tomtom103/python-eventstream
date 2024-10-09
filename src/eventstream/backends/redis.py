import asyncio
from collections.abc import AsyncIterator
from typing import Any, Self

import lz4.frame  # type: ignore[import-untyped]
import ujson
from pydantic import BaseModel
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ResponseError

from eventstream.models import Event

from .interface import AbstractBackend, PublishModelT

StreamMessageType = tuple[bytes, tuple[tuple[bytes, dict[bytes, bytes]]]]


class RedisStreamBackend[T: BaseModel](AbstractBackend[T]):
    def __init__(self, pool: ConnectionPool, group: str, dlq: str) -> None:
        self._client = Redis(connection_pool=pool)
        self._streams: dict[
            bytes | str | memoryview, int | bytes | str | memoryview
        ] = {}
        self._ready = asyncio.Event()
        self._group = group  # Stream group name
        self._dlq = dlq  # Dead Letter Queue name

    async def publish(self, channel: str, message: PublishModelT) -> None:
        await self._client.xadd(channel, {"message": self._serialize(message)})

    async def subscribe(self, channel: str) -> None:
        try:
            # Attempt to create a group if it doesn't already exist
            await self._client.xgroup_create(
                channel, self._group, id="0", mkstream=True
            )
        except ResponseError:
            # Group already exists, we can ignore
            pass

        self._streams[channel] = ">"
        self._ready.set()

    async def unsubscribe(self, channel: str) -> None:
        self._streams.pop(channel, None)

    async def _wait_for_messages(self) -> list[StreamMessageType]:
        await self._ready.wait()
        messages = None
        while not messages:
            messages = await self._client.xreadgroup(
                groupname=self._group,
                consumername="consumer-1",
                streams=self._streams,
                count=1,
                block=100,
            )
        return messages

    async def next_published(self) -> AsyncIterator[Event[T]]:
        while True:
            messages = await self._wait_for_messages()

            for stream_data in messages:
                stream, events = stream_data

                for event in events:
                    _msg_id, message = event

                    # Store the last message ID processed for each stream
                    self._streams[stream.decode("utf-8")] = _msg_id.decode("utf-8")

                    raw_event = {
                        "channel": stream.decode("utf-8"),
                        "message": ujson.decode(
                            self._deserialize(message.get(b"message", b""))
                        ),
                    }
                    yield Event.model_validate(raw_event)

    async def ack_message(self, stream: str, msg_id: str) -> None:
        """Ack the message in the group"""
        await self._client.xack(stream, self._group, msg_id)

    async def move_to_dlq(self, stream: str, msg_id: str, message: T) -> None:
        # Move message to SQL
        self._client.xadd(
            self._dlq, {"original_stream": stream, "message": message.model_dump_json()}
        )
        # Ack message so it's not reprocessed
        await self.ack_message(stream, msg_id)

    def _serialize(self, m: PublishModelT) -> Any:
        # TODO: `json` is not super efficient at being compressed
        # potentially find another lossless format
        return lz4.frame.compress(
            m.model_dump_json().encode(encoding="utf-8"),
            compression_level=lz4.frame.COMPRESSIONLEVEL_MAX,
            content_checksum=True,
        )

    def _deserialize(self, b: bytes) -> str:
        d: bytes = lz4.frame.decompress(b)
        return d.decode(encoding="utf-8")

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self._client.aclose()
