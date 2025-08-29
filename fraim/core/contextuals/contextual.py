# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import dataclasses
from abc import abstractmethod, abstractproperty
from typing import Generic, Protocol, Self, TypeVar

from fraim.outputs import sarif

T = TypeVar("T")


@dataclasses.dataclass
class Location:
    """A location in a file."""

    file_path: str
    line_number_start_inclusive: int
    line_number_end_inclusive: int

    def to_sarif(self) -> sarif.Location:
        return sarif.Location(
            physicalLocation=sarif.PhysicalLocation(
                artifactLocation=sarif.ArtifactLocation(uri=self.file_path),
                region=sarif.Region(
                    startLine=self.line_number_start_inclusive,
                    endLine=self.line_number_end_inclusive,
                ),
            )
        )

    def __str__(self):
        return f"{self.file_path}:{self.line_number_start_inclusive}-{self.line_number_end_inclusive}"


class Locations(list[Location]):
    def __init__(self, *locations: Location):
        super().__init__(list(locations))

    def to_sarif(self) -> list[sarif.Location]:
        return [location.to_sarif() for location in self]

    def __add__(self, other) -> Self:
        return Locations(*(list(self) + list(other)))

    def __str__(self):
        return ", ".join([str(l) for l in self])


class Contextual(Protocol, Generic[T]):
    """A piece of content with a contextual description.

    When Contextual content is added to a prompt, the contextual description
    can be included to help the LLM better understand the content.
    """

    description: str
    content: T

    def __str__(self) -> str: ...

    @property
    @abstractmethod
    def locations(self) -> Locations: ...
