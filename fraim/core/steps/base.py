# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for steps"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from fraim.core.history import History

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class BaseStep(ABC, Generic[TInput, TOutput]):
    """Base class for steps

    A step is a unit of work that can be executed by a workflow.
    It is responsible for executing a single task and returning a result.

    Steps are executed in order, and the result of each step is passed to the next step.
    """

    @abstractmethod
    async def run(self, history: History, input: TInput, **kwargs: Any) -> TOutput:
        """Run the step asynchronously"""

    def run_sync(self, history: History, input: TInput, **kwargs: Any) -> TOutput:
        """Run the step synchronously"""
        return asyncio.run(self.run(history, input, **kwargs))
