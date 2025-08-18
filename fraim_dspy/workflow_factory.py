"""
Factory module for creating DSPy workflow components.

This module provides a clean factory pattern implementation for creating
workflow signatures and modules, following dependency injection principles.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable, TypeVar, Union
import dspy
from pydantic import BaseModel, Field

from .base_signature import BaseWorkflowSignature
from .base_module import BaseWorkflowModule

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowField:
    """Immutable definition of a field in a workflow signature."""
    name: str
    field_type: str  # "input" or "output"
    description: str
    type_hint: str
    optional: bool = False

    def to_dspy_field(self) -> tuple[Any, Type[Any]]:
        """Convert to DSPy field configuration."""
        field_type = self._get_python_type()
        
        if self.field_type.lower() == "input":
            field = dspy.InputField(desc=self.description, prefix=self.name)
        elif self.field_type.lower() == "output":
            field = dspy.OutputField(desc=self.description, prefix=self.name)
        else:
            raise ValueError(f"Invalid field type: {self.field_type}")
            
        # Ensure we return a proper type, not a Union or Optional
        if self.optional:
            # For optional fields, we still use the base type but mark it as optional in the field
            field.optional = True
            return field, field_type
        return field, field_type
    
    def _get_python_type(self) -> Type[Any]:
        """Map type string to Python type."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
            "any": Any
        }
        
        if self.type_hint.lower() not in type_map:
            raise ValueError(f"Unsupported type: {self.type_hint}")
        return type_map[self.type_hint.lower()]


@dataclass(frozen=True)
class WorkflowConfig:
    """Immutable workflow configuration."""
    name: str
    description: str
    prompts_path: Path
    fields: List[WorkflowField]

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.name:
            raise ValueError("Workflow name is required")
        if not self.prompts_path.exists():
            raise ValueError(f"Prompts file not found: {self.prompts_path}")
        if not self.fields:
            raise ValueError("At least one field is required")


class SignatureFactory:
    """Factory for creating workflow signatures."""
    
    @classmethod
    def create(cls, config: WorkflowConfig) -> Type[BaseWorkflowSignature]:
        """Create a new signature class from configuration.
        
        Args:
            config: Workflow configuration
            
        Returns:
            A new signature class configured with the specified fields
        """
        fields: Dict[str, tuple[Any, Type]] = {
            field.name: field.to_dspy_field() 
            for field in config.fields
        }
        
        # Create the signature class
        class WorkflowSignature(BaseWorkflowSignature):
            """Dynamically created workflow signature."""
            
            def __init__(self, **kwargs: Any) -> None:
                """Initialize with required fields."""
                # Initialize default values for all fields
                field_values = {
                    name: kwargs.get(name, "") 
                    for name in fields.keys()
                }
                super().__init__(**field_values)
            
            @classmethod
            def get_prompts_path(cls) -> str:
                return str(config.prompts_path)
                
        # Add field definitions
        for name, (field_def, field_type) in fields.items():
            logger.info(f"Adding field {name} with type {field_type} and definition {field_def}")
            setattr(WorkflowSignature, name, field_def)
            if not hasattr(WorkflowSignature, "__annotations__"):
                setattr(WorkflowSignature, "__annotations__", {})
            WorkflowSignature.__annotations__[name] = field_type
            
        WorkflowSignature.__doc__ = config.description
        WorkflowSignature.__name__ = f"{config.name}Signature"
        
        # Debug log the created signature class
        logger.info(f"Created signature class {WorkflowSignature.__name__}")
        logger.info(f"Signature annotations: {WorkflowSignature.__annotations__}")
        logger.info(f"Signature fields: {[f for f in dir(WorkflowSignature) if not f.startswith('_')]}")
        
        return WorkflowSignature


class ModuleFactory:
    """Factory for creating workflow modules."""
    
    @classmethod
    def create(
        cls,
        config: WorkflowConfig,
        metric_fn: Optional[Callable[[dspy.Example, dspy.Example, Optional[Any]], float]] = None
    ) -> Type[BaseWorkflowModule]:
        """Create a new module class from configuration.
        
        Args:
            config: Workflow configuration
            metric_fn: Optional evaluation metric function
            
        Returns:
            A new module class configured with the specified signature
        """
        # Create the signature class first
        signature_class = SignatureFactory.create(config)
        
        class WorkflowModule(BaseWorkflowModule):
            """Dynamically created workflow module."""
            
            def __init__(
                self,
                signature_class: Type[BaseWorkflowSignature] = signature_class,
                yaml_path: str = str(config.prompts_path),
                metric_fn: Optional[Callable[[Any, Any, Optional[Any]], float]] = metric_fn
            ) -> None:
                """Initialize with pre-configured signature."""
                super().__init__(
                    signature_class=signature_class,
                    yaml_path=yaml_path,
                    metric_fn=metric_fn
                )
                
        WorkflowModule.__name__ = f"{config.name}Module"
        WorkflowModule.__doc__ = f"DSPy module for {config.name} workflow"
        
        return WorkflowModule


class WorkflowFactory:
    """High-level factory for creating complete workflows."""
    
    @classmethod
    def create_signature(cls, config: WorkflowConfig) -> Type[BaseWorkflowSignature]:
        """Create a signature class from configuration."""
        return SignatureFactory.create(config)
    
    @classmethod
    def create_module(
        cls,
        config: WorkflowConfig,
        metric_fn: Optional[Callable[[dspy.Example, dspy.Example, Optional[Any]], float]] = None
    ) -> Type[BaseWorkflowModule]:
        """Create a module class from configuration."""
        return ModuleFactory.create(config, metric_fn)