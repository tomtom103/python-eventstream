import asyncio
from collections.abc import AsyncGenerator
from typing import Generic, TypeVar

from pydantic import BaseModel

from eventstream.exceptions import Unsubscribed

MessageT = TypeVar("MessageT", bound=BaseModel)


class Event(BaseModel, Generic[MessageT]):
    channel: str
    message: MessageT


class EventStream[T: BaseModel]:
    def __init__(self, queue: asyncio.Queue[Event[T] | None]) -> None:
        self._queue = queue

    async def __aiter__(self) -> AsyncGenerator[Event[T] | None, None]:
        try:
            while True:
                yield await self.get()
        except Unsubscribed:
            print("Foo")
            pass

    async def get(self) -> Event[T]:
        item = await self._queue.get()
        if item is None:
            raise Unsubscribed()
        return item
