"""
Workflow management for DSPy prompt optimization.

This module handles loading and managing workflow-specific data and prompts
for optimizing Fraim's prompts.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Tuple, cast

from .training_data import TrainingExample, create_training_example_class, TrainingDataManager, TrainingDataValidationError
from .workflow_factory import WorkflowField

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Manages workflow-specific data and prompts for DSPy optimization.
    
    Each workflow should have:
    1. A prompts YAML file (workflow_name_prompts.yaml)
    2. A training data CSV file (workflow_name_training_data.csv)
    """
    
    def __init__(self, workflow_dir: Path, workflow_name: str):
        """
        Initialize workflow manager.
        
        Args:
            workflow_dir: Directory containing workflow files
            workflow_name: Name of the workflow (e.g., 'scanner', 'triager')
        """
        self.workflow_dir = Path(workflow_dir)
        self.workflow_name = workflow_name
        self.prompts_file = self.workflow_dir / f"{workflow_name}_prompts.yaml"
        self.training_file = self.workflow_dir / f"{workflow_name}_training_data.csv"
        
        # Define standard fields for all workflows
        self.fields: Dict[str, Tuple[Type, str]] = {
            "input": (str, "Input data to process"),
            "expected_output": (str, "Expected output from the model")
        }
        
        # Validate workflow files exist
        if not self.workflow_dir.exists():
            raise ValueError(f"Workflow directory not found: {self.workflow_dir}")
        if not self.prompts_file.exists():
            raise ValueError(f"Prompts file not found: {self.prompts_file}")
        if not self.training_file.exists():
            raise ValueError(f"Training data file not found: {self.training_file}")
            
        # Load workflow configuration
        self.prompts = self._load_prompts()
        self.training_manager = self._setup_training_manager()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompts from YAML file."""
        try:
            with open(self.prompts_file, 'r') as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ValueError("Prompts file must contain a dictionary")
                return cast(Dict[str, str], data)
        except Exception as e:
            raise ValueError(f"Error loading prompts file: {e}")
    
    def _setup_training_manager(self) -> TrainingDataManager:
        """Setup training data manager with appropriate example class."""
        example_class = create_training_example_class(
            f"{self.workflow_name.title()}TrainingExample",
            self.fields
        )
        
        return TrainingDataManager(
            data_dir=self.workflow_dir,
            example_class=example_class,
            data_file_name=f"{self.workflow_name}_training_data.csv"
        )
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the workflow."""
        return str(self.prompts.get("system", ""))
    
    def get_user_prompt(self) -> str:
        """Get the user prompt for the workflow."""
        return str(self.prompts.get("user", ""))
    
    def get_workflow_fields(self) -> List[WorkflowField]:
        """Convert dictionary fields to WorkflowField objects."""
        workflow_fields = []
        
        for name, (type_hint, description) in self.fields.items():
            # Determine if this is an input or output field
            field_type = "output" if name.startswith("expected_") else "input"
            
            workflow_fields.append(
                WorkflowField(
                    name=name,
                    field_type=field_type,
                    description=description,
                    type_hint=type_hint.__name__,
                    optional=False
                )
            )
        
        return workflow_fields
    
    def get_training_data(self) -> Dict[str, Any]:
        """Get training data and statistics."""
        examples = self.training_manager.load_training_data()
        stats = self.training_manager.get_data_statistics()
        
        return {
            "examples": examples,
            "stats": stats
        }
    
    def validate(self) -> Dict[str, Dict[str, Any]]:
        """
        Validate workflow configuration and data.
        
        Returns:
            Dictionary with validation results
        """
        results: Dict[str, Dict[str, Any]] = {
            "prompts": {"valid": True, "issues": []},
            "training_data": {"valid": True, "issues": []}
        }
        
        # Validate prompts
        prompt_issues: List[str] = []
        required_fields = ["system", "user"]
        for field in required_fields:
            if field not in self.prompts:
                results["prompts"]["valid"] = False
                prompt_issues.append(f"Missing required field: {field}")
        results["prompts"]["issues"] = prompt_issues
        
        # Validate training data
        try:
            self.training_manager.validate_training_data()
        except TrainingDataValidationError as e:
            results["training_data"]["valid"] = False
            results["training_data"]["issues"] = [str(e)]
        
        return results