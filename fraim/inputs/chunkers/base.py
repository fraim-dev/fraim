from abc import abstractmethod
from typing import Any, Iterator

from fraim.core.contextuals import Contextual


class Chunker:
    """Base class for chunkers."""

    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    @abstractmethod
    def __iter__(self) -> Iterator[Contextual[str]]: ...
