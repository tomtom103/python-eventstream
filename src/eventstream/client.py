from asyncio import Queue, Task, create_task
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Self

from redis.asyncio import ConnectionPool

from eventstream.backends.redis import RedisStreamBackend
from eventstream.models import Consumer, Event


class EventStreamClient:
    def __init__(self, pool: ConnectionPool):
        # TODO: We could potentially have other backends for this
        self._backend = RedisStreamBackend(pool)
        self._subscribers: dict[str, set[Queue[Event | None]]] = {}
        self._listener_task: Task[Any] | None = None

    async def publish(self, channel: str, message: Any) -> None:
        await self._backend.publish(channel, message)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[Consumer]:
        queue: Queue[Event | None] = Queue()
        try:
            if not self._subscribers.get(channel):
                await self._backend.subscribe(channel)
                self._subscribers[channel] = {queue}
            else:
                self._subscribers[channel].add(queue)

            yield Consumer(queue)
        finally:
            self._subscribers[channel].remove(queue)
            if not self._subscribers.get(channel):
                del self._subscribers[channel]
                await self._backend.unsubscribe(channel)
            await queue.put(None)

    async def _listener(self) -> None:
        while True:
            event = await self._backend.next_published()
            print(self._subscribers)
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
