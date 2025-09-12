# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Checks  Infrastructure as Code (IaC) against a set of security controls.
"""

import os
from dataclasses import dataclass
from textwrap import dedent
from types import SimpleNamespace
from typing import Annotated

from rich.layout import Layout

from fraim.core.display.result import ResultsPanel
from fraim.core.parsers import TextOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingOptions, Workflow
from fraim.core.workflows.llm_processing import LLMMixin, LLMOptions
from fraim.core.workflows.sarif import write_sarif_and_html_report
from fraim.inputs.project import ProjectInput
from fraim.outputs import sarif
from fraim.tools import FilesystemTools, SarifTools

SCANNER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "prompts.yaml"))


@dataclass
class CloudControlsOptions(ChunkProcessingOptions, LLMOptions):
    """Input for the Cloud Controls workflow."""

    output: Annotated[str, {"help": "Path to save the output HTML report"}] = "fraim_output"


@dataclass
class CloudControlsInput:
    """Input for the Cloud Controls workflow."""

    pass


class CloudControlsWorkflow(LLMMixin, Workflow[CloudControlsOptions, list[sarif.Result]]):
    """Analyzes cloud config (IaC like Terraform, CloudFormation, Pulumi, etc.) for security
    vulnerabilities, compliance issues, and best practice deviations."""

    name = "cloud_controls"

    def __init__(self, args: CloudControlsOptions) -> None:
        super().__init__(args)

        # Configure the project
        # TODO: This is copied from the ChunkProcessor mixin. Move the project setup to a ProjectMixin or similar.
        kwargs = SimpleNamespace(
            location=args.location,
            globs="*",
            limit=args.limit,
            chunk_size=args.chunk_size,
            head=args.head,
            base=args.base,
            diff=args.diff,
        )
        self.project = ProjectInput(kwargs=kwargs)

        # Configure the list in which to collect the run results
        self.run_results = sarif.RunResults(results=[])

        # Configure the LLM with tools
        sarif_tools = SarifTools(self.run_results)
        filesystem_tools = FilesystemTools(self.project.project_path)
        tools = [*sarif_tools.tools, *filesystem_tools.tools]

        parser = TextOutputParser(
            dedent("""
            Use the add_sarif_result tool to record the findings as SARIF `Result` objects as you go.
            
            For your final text response, return a succint summary of your analysis.
            """)
        )

        self.step: LLMStep[CloudControlsInput, str] = LLMStep(
            self.llm,
            SCANNER_PROMPTS["system"],
            SCANNER_PROMPTS["user"],
            parser,
            tools=tools,
            max_tool_iterations=100,
        )

    async def run(self) -> list[sarif.Result]:
        """Main Cloud Controls workflow - full control over execution."""

        try:
            # Run the LLM (it will automatically emit start/completion events)
            dummy = CloudControlsInput()
            _response = await self.step.run(self.history, dummy)

            # Write the report
            report_paths = write_sarif_and_html_report(
                results=self.run_results.results,
                repo_name=self.project.repo_name,
                output_dir=self.args.output,
            )

            print(f"Found {len(self.run_results.results)} results.")
            print(f"Wrote SARIF report to {report_paths.sarif_path}")
            print(f"Wrote HTML report to {report_paths.html_path}")

            return self.run_results.results

        except Exception as e:
            # LLMStep will automatically emit failure events
            raise

    def rich_display(self) -> Layout:
        """
        Create a rich display layout showing:
        - Base class rich_display in the upper panel
        - Panel showing number of results found so far
        """
        # Get the base class display - since workflows inherit from Workflow class,
        # this should always work for ChunkProcessor mixins and LLMMixin
        base_display = super().rich_display()

        # Create a new layout with two panels
        layout = Layout()
        layout.split_column(
            Layout(base_display, name="history", ratio=1),
            Layout(ResultsPanel(lambda: self.run_results.results), name="results", size=3),
        )

        return layout
