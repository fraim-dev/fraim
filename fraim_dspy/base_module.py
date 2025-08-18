"""
Base DSPy module class for Fraim workflows.

This module provides the base functionality for creating and optimizing
DSPy modules that can be used across different workflows.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Callable
import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2
from dspy.evaluate import Evaluate

from .base_signature import BaseWorkflowSignature

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseWorkflowModule')


class BaseWorkflowModule(dspy.Module):
    """Base class for all Fraim workflow DSPy modules.
    
    This class provides common functionality for creating and optimizing
    workflow modules. All workflow-specific modules should inherit from this class.
    """
    
    def __init__(
        self,
        signature_class: Type[BaseWorkflowSignature],
        yaml_path: str,
        metric_fn: Optional[Callable[[dspy.Example, dspy.Example, Optional[Any]], float]] = None
    ) -> None:
        """Initialize the workflow module.
        
        Args:
            signature_class: The signature class to use
            yaml_path: Path to the YAML file containing prompts
            metric_fn: Optional evaluation metric function
        """
        super().__init__()
        # Create and store signature instance
        self.signature = signature_class.from_yaml(yaml_path)
        # Store signature class and yaml path for optimization
        self._signature_class = signature_class
        self._yaml_path = yaml_path
        # Create predictor with signature and store it
        self.predictor = dspy.ChainOfThought(signature=self.signature)
        self.metric_fn = metric_fn
        self.optimized_predictor: Optional[dspy.ChainOfThought] = None
        
    def _create_predictor_copy(self) -> dspy.ChainOfThought:
        """Create a new predictor with the same signature configuration.
        
        Returns:
            A new predictor instance with copied signature
        """
        # Create new signature instance
        new_signature = self._signature_class.from_yaml(self._yaml_path)
        return dspy.ChainOfThought(signature=new_signature)
    
    def forward(self, **inputs: Any) -> Any:
        """Run the workflow module with the given inputs.
        
        Args:
            **inputs: Keyword arguments to pass to the predictor
            
        Returns:
            The predictor's output
        """
        if self.optimized_predictor:
            return self.optimized_predictor(**inputs)
        return self.predictor(**inputs)
    
    def optimize(
        self,
        train_examples: List[dspy.Example],
        dev_examples: Optional[List[dspy.Example]] = None,
        method: str = "bootstrap",
        max_bootstrapped_demos: int = 4,
        num_threads: int = 1
    ) -> None:
        """Optimize the module using DSPy's optimization algorithms.
        
        Args:
            train_examples: Training examples for optimization
            dev_examples: Optional development set for evaluation
            method: Optimization method ('bootstrap' or 'mipro')
            max_bootstrapped_demos: Max examples for bootstrap few-shot
            num_threads: Number of threads for optimization
            
        Raises:
            ValueError: If no metric function is provided or unknown optimization method
        """
        if not self.metric_fn:
            raise ValueError("Metric function must be provided for optimization")
            
        if len(train_examples) == 0:
            logger.warning("No training examples provided, skipping optimization")
            return
            
        # Split data into train/dev if dev set not provided
        if not dev_examples and len(train_examples) > 1:
            train_size = int(0.8 * len(train_examples))
            dev_examples = train_examples[train_size:]
            train_examples = train_examples[:train_size]

        # Choose optimization algorithm
        if method == "bootstrap":
            optimizer = BootstrapFewShot(
                metric=self.metric_fn,
                max_bootstrapped_demos=min(max_bootstrapped_demos, len(train_examples))
            )
        elif method == "mipro":
            optimizer = MIPROv2(
                metric=self.metric_fn,
                init_temperature=0.7
            )
        else:
            raise ValueError(f"Unknown optimization method: {method}")
            
        # Create separate but equal predictors for student and teacher
        student_predictor = self._create_predictor_copy()
        teacher_predictor = self._create_predictor_copy()
        
        if train_examples:
            logger.info(f"First training example: {train_examples[0]}")
            logger.info(f"First training example type: {type(train_examples[0])}")
            logger.info(f"First training example fields: {dir(train_examples[0])}")
        
        # Optimize the module using both predictors
        try:
            logger.info("Starting optimization with compile...")
            self.optimized_predictor = optimizer.compile(
                student=student_predictor,
                teacher=teacher_predictor,
                trainset=train_examples
            )
            logger.info("Optimization compile completed successfully")
        except Exception as e:
            logger.error(f"Optimization failed with error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Evaluate on dev set if available
        if dev_examples:
            evaluator = Evaluate(
                devset=dev_examples,
                metric=self.metric_fn,
                num_threads=num_threads,
                provide_traceback=True
            )
            score = evaluator(self)
            logger.info(f"Optimization complete. Dev set score: {score.score:.3f}")
        else:
            logger.info("Optimization complete. No dev set for evaluation.")
    
    def save_optimized_prompts(self, output_dir: Path) -> None:
        """Save the optimized prompts to files.
        
        Args:
            output_dir: Directory to save optimized prompts
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.optimized_predictor:
            logger.warning("No optimized predictor available, nothing to save")
            return
            
        # Save the optimized module
        module_file = output_dir / f"optimized_{self.__class__.__name__.lower()}.json"
        self.save(module_file)
        
        # Extract and save the optimized prompts
        predictor = self.optimized_predictor
        prompt_data: Dict[str, Any] = {
            "signature_instructions": predictor.signature.__doc__ or "",
            "few_shot_examples": [],
            "predictor_info": {
                "type": type(predictor).__name__,
                "has_demos": hasattr(predictor, "demos") and bool(predictor.demos)
            }
        }
        
        # Extract few-shot demos if they exist
        if hasattr(predictor, "demos") and predictor.demos:
            for i, demo in enumerate(predictor.demos):
                try:
                    demo_data = {"demo_index": i}
                    
                    # Try different ways to extract demo data
                    if hasattr(demo, "_store") and demo._store:
                        demo_data["demo_content"] = demo._store
                    elif hasattr(demo, "toDict"):
                        demo_data["demo_content"] = demo.toDict()
                    else:
                        # Try to get raw demo attributes
                        demo_attrs: Dict[str, str] = {}
                        for attr in dir(demo):
                            if not attr.startswith("_") and not callable(getattr(demo, attr)):
                                try:
                                    value = getattr(demo, attr)
                                    if value is not None:
                                        demo_attrs[attr] = str(value)
                                except:
                                    pass
                        demo_data["demo_content"] = demo_attrs  # type: ignore
                        
                    prompt_data["few_shot_examples"].append(demo_data)
                except Exception as e:
                    prompt_data["few_shot_examples"].append({
                        "demo_index": i,
                        "error": f"Could not extract demo: {str(e)}"
                    })
                    
        # Save the prompt data
        prompt_file = output_dir / f"optimized_{self.__class__.__name__.lower()}_prompts.json"
        with open(prompt_file, 'w') as f:
            json.dump(prompt_data, f, indent=2)
            
        logger.info(f"Saved optimized prompts to {prompt_file}")
    
    @classmethod
    def from_yaml(
        cls: Type[T],
        signature_class: Type[BaseWorkflowSignature],
        yaml_path: str,
        metric_fn: Optional[Callable[[dspy.Example, dspy.Example, Optional[Any]], float]] = None
    ) -> T:
        """Create a module instance from a YAML file.
        
        Args:
            signature_class: The signature class to use
            yaml_path: Path to the YAML file containing prompts
            metric_fn: Optional evaluation metric function
            
        Returns:
            An instance of the module class
        """
        return cls(signature_class, yaml_path, metric_fn)
