from asyncio import Queue, Task, create_task
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Self

from pydantic import BaseModel
from redis.asyncio import ConnectionPool

from eventstream.backends import RedisStreamBackend
from eventstream.backends.interface import PublishModelT
from eventstream.models import Event, EventStream


class EventStreamClient[T: BaseModel]:
    def __init__(self, pool: ConnectionPool):
        # TODO: We could potentially have other backends for this
        self._backend: RedisStreamBackend[T] = RedisStreamBackend(
            pool, group="foo", dlq="dql-foo"
        )
        self._client = self._backend._client
        self._subscribers: dict[str, set[Queue[Event[T] | None]]] = {}
        self._listener_task: Task[Any] | None = None

    async def publish(self, channel: str, message: PublishModelT) -> None:
        await self._backend.publish(channel, message)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[EventStream[T]]:
        queue: Queue[Event[T] | None] = Queue()
        try:
            if not self._subscribers.get(channel):
                await self._backend.subscribe(channel)
                self._subscribers[channel] = {queue}
            else:
                self._subscribers[channel].add(queue)

            yield EventStream[T](queue)
        finally:
            self._subscribers[channel].remove(queue)
            if not self._subscribers.get(channel):
                del self._subscribers[channel]
                await self._backend.unsubscribe(channel)
            await queue.put(None)

    async def _listener(self) -> None:
        while True:
            async for event in self._backend.next_published():
                for queue in list(self._subscribers.get(event.channel, [])):
                    await queue.put(event)

    async def connect(self) -> None:
        await self._backend.__aenter__()
        self._listener_task = create_task(self._listener())

    async def disconnect(self) -> None:
        if self._listener_task is not None:
            if self._listener_task.done():
                self._listener_task.result()
            else:
                self._listener_task.cancel()
        await self._backend.__aexit__()

    async def __aenter__(self) -> Self:
        # Create the task group
        await self.connect()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.disconnect()
        self._listener_task = None
