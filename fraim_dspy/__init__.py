"""
DSPy-based prompt optimization for Fraim workflows.

This module provides DSPy-powered optimization for the prompts used in Fraim's
code security analysis workflow.
"""

from .optimizer import PromptOptimizer
from .training_data import TrainingDataManager
from .workflow_factory import WorkflowFactory

__all__ = [
    "PromptOptimizer",
    "TrainingDataManager",
    "WorkflowFactory",
] 