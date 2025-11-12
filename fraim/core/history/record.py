# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.


import asyncio
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

    def elapsed_seconds(self) -> float:
        """Return the time elapsed in seconds since the record was created."""
        return (datetime.now(UTC) - self.timestamp).total_seconds()


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

    def elapsed_seconds(self) -> float:
        """Return the time elapsed in seconds since the record was created."""
        return (datetime.now(UTC) - self.timestamp).total_seconds()


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
        total_cost (float): The cumulative cost of all LLM operations in this history.

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
        # Cost tracking (with lock for thread-safe updates)
        self.total_cost: float = 0.0
        self._cost_lock = asyncio.Lock()

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

    async def add_cost(self, cost: float) -> None:
        """
        Add a cost to the total cost for this history.

        This method is async and thread-safe to support concurrent cost updates.

        Args:
            cost (float): The cost to add to the total cost.

        Example:
            >>> history = History()
            >>> await history.add_cost(0.001)
            >>> await history.add_cost(0.002)
            >>> history.get_total_cost()
            0.003
        """
        async with self._cost_lock:
            self.total_cost += cost

    async def get_total_cost(self) -> float:
        """
        Get the total cost for this history, including all nested histories.

        This method is async and thread-safe to support concurrent cost reads.

        Returns:
            float: The total cost accumulated in this history and all nested histories.

        Example:
            >>> history = History()
            >>> await history.add_cost(0.001)
            >>> sub_record = HistoryRecord("Sub task")
            >>> await sub_record.history.add_cost(0.002)
            >>> history.append_record(sub_record)
            >>> await history.get_total_cost()
            0.003
        """
        # Acquire lock for thread-safe reading
        async with self._cost_lock:
            # Sum up cost from this history and all nested histories
            nested_costs = [
                await record.history.get_total_cost() for record in self.records if isinstance(record, HistoryRecord)
            ]
            nested_cost = sum(nested_costs)
            return self.total_cost + nested_cost

    def get_total_cost_sync(self) -> float:
        """
        Get the total cost for this history, including all nested histories (synchronous version).

        This method is synchronous and does not acquire locks. It should only be used
        in contexts where thread-safety is not critical, such as display/rendering.
        For thread-safe operations, use get_total_cost() instead.

        Returns:
            float: The total cost accumulated in this history and all nested histories.

        Example:
            >>> history = History()
            >>> # ... async operations ...
            >>> # For display purposes only:
            >>> cost = history.get_total_cost_sync()
        """
        # Sum up cost from this history and all nested histories (without lock)
        nested_cost = sum(
            record.history.get_total_cost_sync() for record in self.records if isinstance(record, HistoryRecord)
        )
        return self.total_cost + nested_cost
