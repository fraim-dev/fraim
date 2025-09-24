# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.


from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class EventRecord:
    """
    A record of a single event in the execution history.

    This class represents an atomic event that occurred during workflow execution,
    capturing both a human-readable description and the precise timestamp when
    the event occurred.

    Attributes:
        description (str): A human-readable description of the event that occurred.
        timestamp (datetime): The UTC timestamp when the event was recorded.
                            Defaults to the current UTC time when the record is created.

    Example:
        >>> event = EventRecord("Started processing file main.py")
        >>> print(event.description)
        Started processing file main.py
    """

    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class HistoryRecord:
    """
    A record representing a nested sub-history of related events.

    This class captures a collection of related events that occurred as part of
    a larger operation or workflow step. It provides hierarchical organization
    of events, allowing for nested tracking of complex operations.

    Attributes:
        description (str): A human-readable description of the operation or
                         workflow step that this history record represents.
        timestamp (datetime): The UTC timestamp when this history record was created.
                            Defaults to the current UTC time when the record is created.
        history (History): A nested History object that contains the detailed
                         sequence of events and sub-histories that occurred as
                         part of this history record. Defaults to an empty History
                         with the title "Sub-history".

    Example:
        >>> history_record = HistoryRecord("File processing workflow")
        >>> history_record.history.append_record(EventRecord("Started reading file"))
        >>> history_record.history.append_record(EventRecord("Completed file analysis"))
    """

    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    history: "History" = field(default_factory=lambda: History())


# Type alias for any record type that can be stored in history
type Record = EventRecord | HistoryRecord


class History:
    """
    A chronological history manager for tracking workflow execution events.

    This class provides a centralized way to track and manage the execution
    history of workflows, maintaining a chronological sequence of events and
    sub-histories. It supports both individual events and nested history records
    for complex workflow tracking.

    Attributes:
        records (list[Record]): A chronological list of records (events or sub-histories)
                              that have occurred during workflow execution.

    Example:
        >>> history = History()
        >>> history.append_record(EventRecord("Workflow started"))
        >>> sub_history = HistoryRecord("File processing")
        >>> history.append_record(sub_history)
    """

    def __init__(self) -> None:
        """
        Initialize a new History instance.

        Creates an empty history ready to track workflow execution events.
        """
        # Chronological list of records
        self.records: list[Record] = []

    def append_record(self, record: Record) -> None:
        """
        Append a new record to the end of the history.

        This method adds a new event or history record to the chronological
        sequence of records, maintaining the order of execution.

        Args:
            record (Record): The event record or history record to append.
                           Can be either an EventRecord or HistoryRecord instance.

        Example:
            >>> history = History()
            >>> event = EventRecord("Process completed")
            >>> history.append_record(event)
        """
        self.records.append(record)

    def pop_record(self) -> Record:
        """
        Pop the most recent record from the history.
        """
        return self.records.pop()

    def replace_record(self, record: Record) -> None:
        """
        Replace the most recent record in the history with a new record.

        This method updates the last record in the history with a new record.
        If the history is empty, the new record is simply appended instead.
        This is useful for updating the status of an ongoing operation.

        Args:
            record (Record): The new record to replace the last record with.
                           Can be either an EventRecord or HistoryRecord instance.

        Example:
            >>> history = History()
            >>> history.append_record(EventRecord("Processing..."))
            >>> history.replace_record(EventRecord("Processing completed"))
        """
        if not self.records:
            self.records.append(record)
        else:
            self.records[-1] = record

    def get_records(self) -> list[Record]:
        """
        Retrieve all records in the history.

        Returns a copy of the internal records list, preserving the chronological
        order of events and sub-histories that have been recorded.

        Returns:
            list[Record]: A list containing all EventRecord and HistoryRecord
                        instances in chronological order.

        Example:
            >>> history = History()
            >>> history.append_record(EventRecord("Started"))
            >>> history.append_record(EventRecord("Completed"))
            >>> records = history.get_records()
            >>> len(records)
            2
        """
        return self.records
