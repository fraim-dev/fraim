# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from collections.abc import Iterator
from typing import ContextManager, Protocol, runtime_checkable

from fraim.core.contextuals import Contextual


@runtime_checkable
class Input(Protocol, ContextManager):
    def __iter__(self) -> Iterator[Contextual]: ...

    # TODO: Are inputs redundant, given contextuals? Root path is not its concern.
    #       If there must be root path here, refactor this to return pathlib.Path

    # The relative file path of the input, related to the project path.
    def root_path(self) -> str: ...
