"""
Base DSPy signature class for Fraim workflows.

This module provides the base functionality for loading prompts from YAML files
and creating DSPy signatures that can be used across different workflows.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, cast
import yaml
import dspy

T = TypeVar('T', bound='BaseWorkflowSignature')


class BaseWorkflowSignature(dspy.Signature):
    """Base class for all Fraim workflow DSPy signatures.
    
    This class provides common functionality for loading prompts from YAML files
    and managing signature configuration. All workflow-specific signatures should
    inherit from this class.
    """
    
    @property
    def instructions(self) -> str:
        """Get the instructions for this signature.
        
        Returns:
            The instructions string
        """
        return self.__class__.__doc__ or ""
    
    @classmethod
    def with_instructions(cls: Type[T], instructions: str) -> T:
        """Create a new signature with updated instructions.
        
        Args:
            instructions: The new instructions to use
            
        Returns:
            A new signature instance with the updated instructions
        """
        new_cls = type(cls.__name__, (cls,), {"__doc__": instructions})
        return cast(T, new_cls())
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the signature.
        
        Args:
            *args: Positional arguments to pass to parent
            **kwargs: Keyword arguments to pass to parent
        """
        super().__init__(*args, **kwargs)
        self._prompts: Optional[Dict[str, str]] = None
        
        # Load prompts if path is available
        prompts_path = self.get_prompts_path()
        if prompts_path:
            self._prompts = self.load_prompts(prompts_path)
    
    @classmethod
    def get_prompts_path(cls) -> str:
        """Get the path to the YAML file containing prompts.
        
        Returns:
            Path to the prompts YAML file
            
        This method should be overridden by subclasses to provide
        the correct path to their prompts file.
        """
        return ""
    
    @classmethod
    def load_prompts(cls, yaml_path: str) -> Dict[str, str]:
        """Load prompts from a YAML file.
        
        Args:
            yaml_path: Path to the YAML file containing prompts
            
        Returns:
            Dictionary containing the loaded prompts
            
        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML file is invalid
            ValueError: If the YAML file doesn't contain required prompts
        """
        if not yaml_path:
            raise ValueError("No prompts path provided")
            
        yaml_path = os.path.expanduser(yaml_path)
        yaml_path = os.path.abspath(yaml_path)
        
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Prompts file not found: {yaml_path}")
            
        with open(yaml_path, 'r') as f:
            prompts = yaml.safe_load(f)
            
        if not isinstance(prompts, dict):
            raise ValueError("YAML file must contain a dictionary of prompts")
            
        required_fields = {"system", "user"}
        missing_fields = required_fields - set(prompts.keys())
        if missing_fields:
            raise ValueError(f"YAML file missing required fields: {missing_fields}")
            
        return {
            "system": str(prompts["system"]),
            "user": str(prompts["user"])
        }
    
    @classmethod
    def from_yaml(cls: Type[T], yaml_path: str) -> T:
        """Create a signature instance from a YAML file.
        
        Args:
            yaml_path: Path to the YAML file containing prompts
            
        Returns:
            An instance of the signature class
        """
        instance = cls()
        instance._prompts = cls.load_prompts(yaml_path)
        return instance

    @property
    def input_fields(self) -> Dict[str, Any]:
        """Get dictionary of input field names to field objects.
        
        Returns:
            Dictionary mapping input field names to their field objects
        """
        # Get the actual field types from dspy
        input_field_type = type(dspy.InputField())
        
        fields = {}
        for name, field in self.__class__.__dict__.items():
            if isinstance(field, input_field_type):
                fields[name] = field
        return fields
    
    @property
    def output_fields(self) -> Dict[str, Any]:
        """Get dictionary of output field names to field objects.
        
        Returns:
            Dictionary mapping output field names to their field objects
        """
        # Get the actual field types from dspy
        output_field_type = type(dspy.OutputField())
        
        fields = {}
        for name, field in self.__class__.__dict__.items():
            if isinstance(field, output_field_type):
                fields[name] = field
        return fields
    
    def equals(self, other: Any) -> bool:
        """Check if two signatures are equal.
        
        Args:
            other: Another signature instance to compare with
            
        Returns:
            True if signatures are equal, False otherwise
        """
        if not isinstance(other, BaseWorkflowSignature):
            return False
            
        # Compare input and output fields
        if set(self.input_fields.keys()) != set(other.input_fields.keys()):
            return False
        if set(self.output_fields.keys()) != set(other.output_fields.keys()):
            return False
            
        # Compare field definitions
        for name, self_field in {**self.input_fields, **self.output_fields}.items():
            other_field = other.input_fields.get(name) or other.output_fields.get(name)
            if other_field is None or type(self_field) != type(other_field):
                return False
            if hasattr(self_field, 'desc') and hasattr(other_field, 'desc'):
                if self_field.desc != other_field.desc:
                    return False
        
        # Compare prompts if both have them
        if hasattr(self, '_prompts') and hasattr(other, '_prompts'):
            if self._prompts != other._prompts:
                return False
                
        return True
    
    @property
    def system_prompt(self) -> str:
        """Get the system prompt from the loaded prompts.
        
        Returns:
            The system prompt string
            
        Raises:
            RuntimeError: If prompts haven't been loaded
        """
        if not self._prompts:
            raise RuntimeError("Prompts not loaded. Call from_yaml() first or override get_prompts_path()")
        return self._prompts["system"]
    
    @property
    def user_prompt(self) -> str:
        """Get the user prompt from the loaded prompts.
        
        Returns:
            The user prompt string
            
        Raises:
            RuntimeError: If prompts haven't been loaded
        """
        if not self._prompts:
            raise RuntimeError("Prompts not loaded. Call from_yaml() first or override get_prompts_path()")
        return self._prompts["user"]