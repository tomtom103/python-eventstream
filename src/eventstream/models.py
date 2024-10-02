import asyncio
from collections.abc import AsyncGenerator

from pydantic import BaseModel

from eventstream.exceptions import Unsubscribed


class Event(BaseModel):
    channel: str
    message: str


class Consumer:
    def __init__(self, queue: asyncio.Queue[Event | None]) -> None:
        self._queue = queue

    async def __aiter__(self) -> AsyncGenerator[Event | None, None]:
        try:
            while True:
                yield await self.get()
        except Unsubscribed:
            print("Foo")
            pass

    async def get(self) -> Event:
        item = await self._queue.get()
        if item is None:
            raise Unsubscribed()
        return item
