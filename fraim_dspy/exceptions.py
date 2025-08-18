"""
Custom exceptions for the fraim_dspy package.

This module defines custom exceptions that are used throughout the package
to provide more specific error information and better error handling.
"""

class FraimDspyError(Exception):
    """Base exception class for all fraim_dspy errors."""
    pass

class TrainingDataError(FraimDspyError):
    """Raised when there are issues with training data."""
    pass

class TrainingDataNotFoundError(TrainingDataError):
    """Raised when training data file is not found."""
    pass

class TrainingDataValidationError(TrainingDataError):
    """Raised when training data validation fails."""
    pass

class WorkflowError(FraimDspyError):
    """Raised when there are issues with workflow configuration or execution."""
    pass

class WorkflowConfigError(WorkflowError):
    """Raised when there are issues with workflow configuration."""
    pass

class OptimizationError(FraimDspyError):
    """Raised when there are issues during prompt optimization."""
    pass

class DspyDependencyError(FraimDspyError):
    """Raised when required DSPy dependencies are not available."""
    pass
