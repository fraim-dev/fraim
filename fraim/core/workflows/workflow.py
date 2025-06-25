# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for workflows"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generic, List, Protocol, TypeVar

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.outputs import sarif


# Temporarily bound the input type to include code and config until we've refactored
# to push input handling into the workflow.
#
# Currently, the main loop that calls the workflow assumes that the workflow
# wants a contextual code chunk and the global config.
class WorkflowInput(Protocol):
    """Protocol defining the required input interface for all workflows."""

    code: CodeChunk
    config: Config


TInput = TypeVar("TInput", bound=WorkflowInput)

# Temporarily bound the output type to List[sarif.Result] until we've refactored to push
# output reporting into the workflow.
#
# Currently, the main loop that calls the workflow assumes that the output is a list of
# sarif.Result objects.
TOutput = TypeVar("TOutput", bound=List[sarif.Result])


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
