"""
Training Data Generation for Fraim DSPy

This module provides tools for generating training data from CVE databases
to populate the scanner_training_data.csv and triager_training_data.csv files
used in Fraim's DSPy prompt optimization.
"""

from .models import CVEData
from .fetcher import CVEDataFetcher
from .manager import CVETrainingDataManager

__all__ = [
    "CVEData",
    "CVEDataFetcher",
    "CVETrainingDataManager",
]
