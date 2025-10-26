# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""SARIF result recording tools for collecting analysis results."""

from collections.abc import Iterator
from textwrap import dedent
from typing import Any

from pydantic import BaseModel, Field, create_model

from fraim.core.tools import BaseTool
from fraim.outputs.sarif import Result, RunResults


class SarifTools:
    """
    Interface for SARIF result recording and management.

    This class provides fraim-compatible tools for collecting SARIF results during
    analysis workflows. Results are accumulated in a RunResults instance that can
    be used to generate complete SARIF reports.
    """

    def __init__(self, run_results: RunResults | None = None):
        """Initialize with a RunResults instance to collect results.

        Args:
            run_results: The RunResults instance to collect results in
        """
        self.run_results = run_results or RunResults(results=[])

        self.tools: list[BaseTool] = [
            AddSarifResultTool.create(self.run_results),
        ]

    def __iter__(self) -> Iterator[BaseTool]:
        return iter(self.tools)


class SarifBaseTool(BaseTool):
    """
    Base class for all SARIF tools.

    Stores the RunResults instance in a field.
    """

    run_results: RunResults = Field(exclude=True, description="The RunResults instance to collect results in")

    @classmethod
    def create(cls, run_results: RunResults, **kwargs: Any) -> "SarifBaseTool":
        """
        Create a new instance of the tool.

        Args:
            run_results: The RunResults instance for collecting results.
        """
        instance = cls(run_results=run_results, **kwargs)
        return instance


class AddSarifResultTool(SarifBaseTool):
    name: str = "add_sarif_result"
    description: str = dedent("""
                              Add a new Result to the SARIF report.
                              
                              Use this tool to record your analysis findings.
                              """)
    args_schema: type[BaseModel] = create_model(
        "AddSarifResultArgs",
        result=(Result, Field(description="SARIF Result object to add")),
    )

    async def _run(self, *args: Any, result: Result, **kwargs: Any) -> str:
        """Add a SARIF result to the RunResults instance.

        Args:
            result: The SARIF Result object to add

        Returns:
            Success message with result count
        """
        self.run_results.results.append(result)
        return f"Success. Total results: {len(self.run_results.results)}"

    def display_message(self, *args: Any, result: Result, **kwargs: Any) -> str:
        return f"Found result '{result.level}: {result.message.text}'"
