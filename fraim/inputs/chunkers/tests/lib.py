from collections.abc import Iterator
from types import TracebackType
from typing import Self

from fraim.core.contextuals import CodeChunk


class InMemory:
    def __init__(self, *files: CodeChunk, root_path: str):
        self._files = files
        self._root_path = root_path

    @property
    def root_path(self) -> str:
        return self._root_path

    def __iter__(self) -> Iterator[CodeChunk]:
        yield from self._files

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass
