# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for workflows"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generic, List, Protocol, TypeVar

from fraim.config import Config
from fraim.outputs import sarif


class WorkflowInput(Protocol):
    """Protocol defining the required input interface for all workflows."""

    config: Config


TInput = TypeVar("TInput", bound=WorkflowInput)

TOutput = TypeVar("TOutput")


class Workflow(ABC, Generic[TInput, TOutput]):
    """Base class for workflows"""

    @abstractmethod
    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        pass

    @abstractmethod
    async def workflow(self, input: TInput) -> TOutput:
        pass

    async def run(self, input: TInput) -> TOutput:
        return await self.workflow(input)

    def run_sync(self, input: TInput) -> TOutput:
        return asyncio.run(self.run(input))
