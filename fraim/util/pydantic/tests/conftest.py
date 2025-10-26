# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Shared pytest fixtures for pydantic utility tests."""

from types import ModuleType
from typing import Any

import pytest


class DynamicModule(ModuleType):
    """A ModuleType subclass that supports natural dynamic attribute assignment for testing."""

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow natural attribute assignment syntax like module.User = UserClass."""
        super().__setattr__(name, value)


@pytest.fixture
def fresh_base_module() -> DynamicModule:
    """Create a fresh base module for each test to avoid cross-contamination."""
    return DynamicModule("base_test")


@pytest.fixture
def fresh_overlay_module() -> DynamicModule:
    """Create a fresh overlay module for each test to avoid cross-contamination."""
    return DynamicModule("overlay_test")
