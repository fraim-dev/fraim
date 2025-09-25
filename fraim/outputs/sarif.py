# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
SARIF (Static Analysis Results Interchange Format) Pydantic models.
Used for generating standardized vulnerability reports.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ArtifactContent(BaseSchema):
    """Represents (part of) the contents of an artifact."""

    text: str = Field(description="UTF-8-encoded content from a text artifact.")


class ArtifactLocation(BaseSchema):
    """Specifies the location of an artifact (usually a file)."""

    uri: str = Field(description="A string containing a valid absolute URI.")


class Region(BaseSchema):
    """A region within an artifact where a result was detected."""

    startLine: int = Field(description="The line number of the first character in the region.")
    endLine: int = Field(description="The line number of the last character in the region.")
    snippet: ArtifactContent | None = Field(
        default=None, description="The portion of the artifact contents within the specified region."
    )


class PhysicalLocation(BaseSchema):
    """A physical location relevant to the a result. Specifies a reference to a programming artifact together with a range of bytes or characters within that artifact."""

    artifactLocation: ArtifactLocation = Field(description="The location of the artifact.")
    region: Region = Field(description="Specifies a portion of the artifact.")
    contextRegion: Region | None = Field(
        default=None,
        description="Specifies a portion of the artifact that encloses the region. Allows a viewer to display additional context around the region.",
    )


class Message(BaseSchema):
    """Encapsualtes a message intended to be read by the end user."""

    text: str = Field(description="A plain text message string.")


class Location(BaseSchema):
    """A location within a programming artifact."""

    physicalLocation: PhysicalLocation = Field(description="Identifies the artifact and region.")


class ThreadFlowLocation(BaseSchema):
    """A location visited by an analysis tool while simulating or monitoring the execution of a program."""

    location: Location = Field(
        description="The location visited by an analysis tool while simulating or monitoring the execution of a program."
    )
    kinds: list[str] = Field(
        description="A set of distinct strings that categorize the thread flow location. Well-known kinds include 'acquire', 'release', 'enter', 'exit', 'call', 'return', 'branch', 'implicit', 'false', 'true', 'caution', 'danger', 'unknown', 'unreachable', 'taint', 'function', 'handler', 'lock', 'memory', 'resource', 'scope', and 'value'."
    )


class ThreadFlow(BaseSchema):
    """Describes a sequence of code locations that specify a path through a single thread of execution such as an operating system or fiber."""

    message: Message = Field(description="A message relevant to the thread flow.")
    locations: list[ThreadFlowLocation] = Field(
        min_length=1,
        description="An array of one or more unique threadFlowLocation objects, each of which describes a location in a threadFlow.",
    )


class CodeFlow(BaseSchema):
    """A set of threadFlows which together describe a pattern of code execution relevant to detecting a result."""

    message: Message = Field(description="A message relevant to the code flow.")
    threadFlows: list[ThreadFlow] = Field(
        min_length=1,
        description="An array of one or more unique threadFlow objects, each of which describes the progress of a program through a thread of execution.",
    )


class ResultProperties(BaseSchema):
    """Key/value pairs that provide additional information about a result."""

    type: str = Field(description="Type of vulnerability (e.g., 'SQL Injection', 'XSS', 'Command Injection', etc.)")
    confidence: int = Field(
        ge=1,
        le=10,
        description="Confidence that the result is a true positive from 1 (least confident) to 10 (most confident)",
    )
    exploitable: bool = Field(description="True if the vulnerability is exploitable, false otherwise.")
    explanation: Message = Field(description="Explanation of the exploitability of the vulnerability.")


ResultLevelEnum = Literal["error", "warning", "note"]


class Result(BaseSchema):
    """A result produced by an analysis tool."""

    message: Message = Field(
        description="A message that describes the result. The first sentence of the message only will be displayed when visible space is limited."
    )
    level: ResultLevelEnum = Field(description="A value specifying the severity level of the result.")
    locations: list[Location] = Field(
        min_length=1,
        description="The set of locations where the result was detected. Specify only one location unless the problem indicated by the result can only be corrected by making a change at every specified location..",
    )
    properties: ResultProperties = Field(
        description="Key/value pairs that provide additional information about the result."
    )
    codeFlows: list[CodeFlow] | None = Field(
        default=None,
        description="An array of zero or more unique codeFlow objects, each of which describes a pattern of execution relevant to detecting the result.",
    )


class ToolComponent(BaseSchema):
    """A component, such as a plug-in or the driver, of the analysis tool that was run."""

    name: str = Field(description="The name of the tool component.")
    version: str = Field(description="The tool component version in the format specified by S.")


class Tool(BaseSchema):
    """The analysis tool that was run.."""

    driver: ToolComponent = Field(description="The analysis tool that was run.")


class RunResults(BaseSchema):
    """Describes just the results of a single run of an analysis tool."""

    results: list[Result] = Field(description="The set of results contained in a SARIF log.")


class Run(RunResults):
    """Describes a single run of an analysis tool, and contains the reported output of that run."""

    tool: Tool = Field(
        description="Information about the tool or tool pipeline that generated the results in this run. A run can only contain results produced by a single tool or tool pipeline. A run can aggregate the results from multiple log files, as long as the context around the tool run (tool command-line arguments and the like) is indentical for all aggregated files."
    )


class SarifReport(BaseSchema):
    """A SARIF log file."""

    version: str = Field(default="2.1.0", description="The SARIF format version of this log file.")
    schema_: str = Field(
        default="https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        alias="$schema",
        description="The URI of the JSON schema corresponding to the version of the SARIF specification that the log file complies with.",
    )
    runs: list[Run] = Field(description="The set of runs contained in a SARIF log.")


def create_sarif_report(results: list[Result], tool_version: str = "1.0.0") -> SarifReport:
    """
    Create a complete SARIF report from a list of results.

    Args:
        results: List of SARIF Result objects
        tool_version: Version of the scanning tool

    Returns:
        Complete SARIF report
    """
    return SarifReport(runs=[Run(tool=Tool(driver=ToolComponent(name="fraim", version=tool_version)), results=results)])
