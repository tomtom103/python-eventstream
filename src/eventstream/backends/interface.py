from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self, TypeVar

from pydantic import BaseModel

from eventstream.models import Event

PublishModelT = TypeVar("PublishModelT", bound=BaseModel)


class AbstractBackend[T: BaseModel](ABC):

    @abstractmethod
    async def publish(self, channel: str, message: PublishModelT) -> None: ...

    @abstractmethod
    async def subscribe(self, channel: str) -> None: ...

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None: ...

    @abstractmethod
    def next_published(self) -> AsyncIterator[Event[T]]: ...

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...
