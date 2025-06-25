# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Observability package for LLM monitoring and logging.
"""

from .backends.langfuse import LangfuseBackend
from .manager import ObservabilityManager
from .registry import ObservabilityRegistry

# Register available backends
ObservabilityRegistry.register(LangfuseBackend())

__all__ = ["ObservabilityManager", "ObservabilityRegistry"]
