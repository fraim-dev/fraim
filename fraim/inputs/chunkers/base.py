from abc import abstractmethod
from collections.abc import Iterator
from typing import Any

from fraim.core.contextuals import Contextual


class Chunker:
    """Base class for chunkers."""

    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def __iter__(self) -> Iterator[Contextual[str]]: ...
