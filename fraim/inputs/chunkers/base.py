import logging
from abc import abstractmethod
from typing import Iterator

from fraim.core.contextuals import CodeChunk


class Chunker:
    """Base class for chunkers."""

    def __init__(self, logger: logging.Logger, **kwargs) -> None:
        self.logger = logger

    @abstractmethod
    def __iter__(self) -> Iterator[CodeChunk]: ...
