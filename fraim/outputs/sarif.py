# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
SARIF (Static Analysis Results Interchange Format) Pydantic models.
Used for generating standardized vulnerability reports.
"""

from enum import Enum
from typing import Any, List, Literal

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
        description="Confidence that the result is a true positive from 1 (least confident) to 10 (most confident)"
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


# A reference to a rule or notification descriptor
class ReportingDescriptorReference(BaseSchema):
    """Information about how to locate a relevant reporting descriptor."""

    id: str | None = Field(None, description="The id of the descriptor.")


# The main Notification object schema
class Notification(BaseSchema):
    """Describes a condition relevant to the tool itself, as opposed to being relevant to the analysis target."""

    level: ResultLevelEnum = Field(description="A value specifying the severity level of the notification.")
    descriptor: ReportingDescriptorReference | None = Field(
        default=None,
        description="A reference to the descriptor for this notification.",
    )
    message: Message = Field(..., description="A message that describes the condition.")
    locations: list[Location] = Field(default_factory=list, description="The locations relevant to this notification.")


class Invocation(BaseSchema):
    """The runtime environment of a single invocation of an analysis tool."""

    execution_successful: bool = Field(
        ...,
        description="A value indicating whether the tool's execution completed successfully.",
    )

    toolExecutionNotifications: list[Notification] = Field(
        description="A list of notifications raised during tool execution.",
    )


class RunResults(BaseSchema):
    """Describes just the results of a single run of an analysis tool."""

    results: list[Result] = Field(description="The set of results contained in a SARIF log.")


class Run(RunResults):
    """Describes a single run of an analysis tool, and contains the reported output of that run."""

    tool: Tool = Field(
        description="Information about the tool or tool pipeline that generated the results in this run. A run can only contain results produced by a single tool or tool pipeline. A run can aggregate the results from multiple log files, as long as the context around the tool run (tool command-line arguments and the like) is indentical for all aggregated files."
    )

    invocations: list[Invocation] = Field(
        description="Describes the invocation of the analysis tool that will be merged with a separate run.",
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


def create_sarif_report(
        results: list[Result],
        failed_chunks: list["CodeChunkFailure"],  # type: ignore[name-defined] # to avoid circular import
        tool_version: str = "1.0.0",
) -> SarifReport:
    """
    Create a complete SARIF report from a list of results.

    Args:
        results: List of SARIF Result objects
        failed_chunks: List of CodeChunkFailure objects representing chunks that failed to be analyzed
        tool_version: Version of the scanning tool

    Returns:
        Complete SARIF report
    """
    return SarifReport(
        runs=[
            Run(
                tool=Tool(driver=ToolComponent(name="fraim", version=tool_version)),
                results=results,
                invocations=[
                    Invocation(
                        execution_successful=True,
                        toolExecutionNotifications=[
                            Notification(
                                level="error",
                                descriptor=ReportingDescriptorReference(id="PARSING_ERROR"),
                                message=Message(
                                    text=f"Code chunk could not be analyzed due to a parsing error: {failure.reason}"
                                ),
                                locations=failure.chunk.locations.to_sarif(),
                            )
                            for failure in failed_chunks
                        ],
                    )
                ],
            ),
        ],
    )

def create_result_model(allowed_types: list[str] | None = None) -> type[Result]:
    """
    Factory function to create a Result model with a restricted set of vulnerability types.

    Args:
        allowed_types: A list of strings representing the allowed vulnerability types.
                       If None or empty, the default Result model with a string type is returned.

    Returns:
        A Pydantic model class for Result, with ResultProperties.type restricted to an enum
        if allowed_types is provided.
    """
    if not allowed_types:
        return Result

    # The type annotations here are for pydantic, may take some more digging to get these to work with mypy.
    VulnTypeEnum = Enum("VulnTypeEnum", {t: t for t in allowed_types})  # type: ignore[misc]

    class RestrictedResultProperties(ResultProperties):
        type: VulnTypeEnum = Field(  # type: ignore[valid-type,assignment]
            description="Type of vulnerability (e.g., 'SQL Injection', 'XSS', 'Command Injection', etc.)"
        )

    class RestrictedResult(Result):
        properties: RestrictedResultProperties = Field(
            description="Key/value pairs that provide additional information about the result."
        )

    return RestrictedResult


def create_run_model(allowed_types: list[str] | None = None) -> type[Run]:
    """
    Factory function to create a Run model with a restricted set of vulnerability types.

    Args:
        allowed_types: A list of strings representing the allowed vulnerability types.
                       If None or empty, the default Run model with a string type is returned.

    Returns:
        A Pydantic model class for Run, with ResultProperties.type restricted to an enum
        if allowed_types is provided.
    """
    RestrictedResultModel = create_result_model(allowed_types)

    # The type annotations here are for pydantic, may take some more digging to get these to work with mypy.
    class RestrictedRun(Run):
        results: List[RestrictedResultModel] = Field(  # type: ignore[valid-type]
            description="The set of results contained in a SARIF log."
        )

    return RestrictedRun
