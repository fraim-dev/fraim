import logging
from abc import abstractmethod
from typing import Any, Iterator

from fraim.core.contextuals import CodeChunk, Contextual


class Chunker:
    """Base class for chunkers."""

    @abstractmethod
    def __init__(self, *args, **kwargs): ...

    @abstractmethod
    def __iter__(self) -> Iterator[Contextual[str]]: ...
