import logging
from abc import abstractmethod


class Chunker:
    """Base class for chunkers."""

    def __init__(self, **kwargs):
        self.logger = kwargs.pop("logger", None)
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

    @abstractmethod
    def __iter__(self): ...
