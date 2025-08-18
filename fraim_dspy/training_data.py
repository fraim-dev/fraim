"""
Training data management for DSPy prompt optimization.

This module handles loading, validating, and preparing training data
from CSV files for optimizing Fraim's prompts.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Type
from dataclasses import dataclass, Field, field, make_dataclass

try:
    import pandas as pd  # type: ignore
except ImportError:
    pd = None  # type: ignore

from .exceptions import (
    TrainingDataError,
    TrainingDataNotFoundError,
    TrainingDataValidationError
)

logger = logging.getLogger(__name__)


class TrainingExample:
    """Base class for training examples."""
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for DSPy."""
        return {field: getattr(self, field) for field in self.__annotations__}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'TrainingExample':
        """Create instance from dictionary."""
        return cls(**data)


def create_training_example_class(name: str, field_definitions: Dict[str, Tuple[Type, str]]) -> Type[TrainingExample]:
    """
    Dynamically create a training example class with the specified fields.
    
    Args:
        name: Name of the training example class
        field_definitions: Dictionary mapping field names to (type, description) tuples
        
    Returns:
        A new TrainingExample subclass with the specified fields
    """
    fields_list = [
        (field_name, field_type, field(metadata={"description": desc}))
        for field_name, (field_type, desc) in field_definitions.items()
    ]
    
    return make_dataclass(
        name,
        fields_list,
        bases=(TrainingExample,),
        frozen=True
    )


class TrainingDataManager:
    """
    Manages training data for DSPy prompt optimization.
    
    Handles loading data from CSV files and preparing it for use
    with DSPy optimization algorithms.
    """
    
    def __init__(self, data_dir: Path, example_class: Type[TrainingExample], data_file_name: str):
        """
        Initialize training data manager.
        
        Args:
            data_dir: Directory containing training data CSV files
            example_class: Class to use for training examples
            data_file_name: Name of the CSV file containing training data
        """
        self.data_dir = Path(data_dir)
        self.example_class = example_class
        self.data_file = self.data_dir / data_file_name
        self.required_columns = list(example_class.__annotations__.keys())
        
        # Get JSON fields from class annotations that are marked as JSON strings
        self.json_fields = [
            field_name for field_name, field_type in example_class.__annotations__.items()
            if "json" in str(field_type).lower()
        ]
    
    def load_training_data(self) -> List[TrainingExample]:
        """
        Load training data from CSV file.
        
        Returns:
            List of training examples
            
        Raises:
            TrainingDataNotFoundError: If training data file does not exist
            TrainingDataValidationError: If training data format is invalid
            TrainingDataError: For other training data related errors
        """
        if not self.data_file.exists():
            raise TrainingDataNotFoundError(f"Training data file not found: {self.data_file}")
        
        examples = []
        try:
            if pd is None:
                raise TrainingDataError("pandas is required for loading training data")
                
            df = pd.read_csv(self.data_file)
            
            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                raise TrainingDataValidationError(f"Missing required columns: {missing_columns}")
            
            validation_errors = []
            for idx, row in df.iterrows():
                # Validate JSON fields
                try:
                    for field in self.json_fields:
                        json.loads(row[field])
                except json.JSONDecodeError as e:
                    validation_errors.append(f"Row {idx+1}: Invalid JSON in field {field}: {e}")
                    continue
                
                # Convert row to dictionary and create example
                row_dict = {col: str(row[col]) for col in self.required_columns}
                examples.append(self.example_class.from_dict(row_dict))
            
            if validation_errors:
                raise TrainingDataValidationError("\n".join(validation_errors))
            
            if not examples:
                raise TrainingDataValidationError("No valid training examples found in data file")
            
            logger.info(f"Loaded {len(examples)} training examples")
            return examples
            
        except (TrainingDataError, TrainingDataValidationError):
            raise
        except Exception as e:
            raise TrainingDataError(f"Error loading training data: {e}") from e
    
    def validate_training_data(self) -> None:
        """
        Validate training data and raise exceptions for any issues found.
        
        Raises:
            TrainingDataValidationError: If any validation issues are found
            TrainingDataError: For other training data related errors
        """
        validation_errors: List[str] = []
        
        try:
            examples = self.load_training_data()
        except TrainingDataNotFoundError:
            # Let this propagate up since it's already handled
            raise
            
        for i, example in enumerate(examples):
            # Validate JSON fields
            for field in self.json_fields:
                try:
                    value = getattr(example, field)
                    parsed = json.loads(value)
                    
                    # Additional validation based on field name conventions
                    if "vulnerabilities" in field.lower() and not isinstance(parsed, list):
                        validation_errors.append(f"Row {i+1}: {field} must be a JSON array")
                        
                except json.JSONDecodeError:
                    validation_errors.append(f"Row {i+1}: Invalid JSON in {field}")
                except Exception as e:
                    validation_errors.append(f"Row {i+1}: Error validating {field}: {e}")
        
        if validation_errors:
            raise TrainingDataValidationError("\n".join(validation_errors))
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the training data.
        
        Returns:
            Dictionary with statistics about the training data
        """
        examples = self.load_training_data()
        stats: Dict[str, Any] = {
            "total_examples": len(examples)
        }
        
        # Collect statistics for each field
        for field_name in self.example_class.__annotations__:
            field_values: Dict[str, int] = {}
            
            for example in examples:
                value = getattr(example, field_name)
                
                # Handle JSON fields
                if field_name in self.json_fields:
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            # Count items in arrays
                            stats[f"{field_name}_avg_items"] = len(parsed)
                            # Count types if items are dictionaries
                            if parsed and isinstance(parsed[0], dict):
                                for item in parsed:
                                    item_type = item.get("type", "Unknown")
                                    field_values[item_type] = field_values.get(item_type, 0) + 1
                        elif isinstance(parsed, dict):
                            # Count keys in dictionaries
                            for key in parsed:
                                field_values[key] = field_values.get(key, 0) + 1
                    except json.JSONDecodeError:
                        continue
                else:
                    # Count occurrences of non-JSON values
                    field_values[str(value)] = field_values.get(str(value), 0) + 1
            
            if field_values:
                stats[f"{field_name}_distribution"] = field_values
        
        return stats