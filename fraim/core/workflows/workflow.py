# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for workflows"""

from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar, cast, get_args, get_origin

from rich.layout import Layout

from fraim.core.display import HistoryView
from fraim.core.history import History

Options = TypeVar("Options")
Result = TypeVar("Result")


class Workflow(ABC, Generic[Options, Result]):
    name: ClassVar[str]

    def __init__(self, args: Options) -> None:
        super().__init__()  # type: ignore

        self.args = args

        self.history = History()

    @abstractmethod
    async def run(self) -> Result:
        pass

    def rich_display(self) -> Layout:
        layout = Layout(renderable=HistoryView(self.history, title=self.name), name="history", ratio=1)
        return layout

    @classmethod
    def options(cls) -> type[Options] | None:
        c: type | None = cls
        while c is not object:
            for base in getattr(c, "__orig_bases__", ()):
                if get_origin(base) is Workflow:
                    opt = get_args(base)[0]
                    unwrapped = get_origin(opt) or opt  # handle Annotated[T, ...] etc.
                    # Tell the type checker this is specifically type[Options]
                    if isinstance(unwrapped, type):
                        return cast("type[Options]", unwrapped)
                    return None
            if c is not None:
                c = c.__base__
        return None
