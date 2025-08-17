import logging
from typing import Iterator

from abc import abstractmethod

from fraim.core.contextuals import CodeChunk


class Chunker:
    """Base class for chunkers."""

    def __init__(self, **kwargs) -> None:
        self.logger = kwargs.pop("logger", None)
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @abstractmethod
    def __iter__(self) -> Iterator[CodeChunk]: ...
