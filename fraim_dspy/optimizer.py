"""
DSPy prompt optimizer for Fraim workflows.

This module provides the main optimization functionality for improving
prompts using DSPy's optimization algorithms. It supports any workflow
that follows Fraim's workflow configuration format.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, cast

try:
    import dspy  # type: ignore
    from dspy.teleprompt import BootstrapFewShot, MIPROv2  # type: ignore
    from dspy.evaluate import Evaluate  # type: ignore
except ImportError:
    dspy = None  # type: ignore
    BootstrapFewShot = None  # type: ignore
    MIPROv2 = None  # type: ignore
    Evaluate = None  # type: ignore

from .base_module import BaseWorkflowModule
from .workflow_factory import WorkflowFactory, WorkflowConfig, WorkflowField
from .workflow_manager import WorkflowManager
from .exceptions import (
    DspyDependencyError,
    OptimizationError,
    TrainingDataError,
    TrainingDataNotFoundError,
    TrainingDataValidationError,
    WorkflowError,
    WorkflowConfigError
)

logger = logging.getLogger(__name__)


class PromptOptimizer:
    """
    Main class for optimizing Fraim's workflow prompts using DSPy.
    
    This class handles the full optimization pipeline including:
    - Loading workflow configurations
    - Loading training data
    - Setting up DSPy models
    - Running optimization algorithms
    - Evaluating results
    - Saving optimized prompts
    """
    
    def __init__(
        self,
        workflow_dir: Path,
        workflow_name: str,
        model_name: str = "gpt-4",
        api_key: Optional[str] = None,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 16
    ):
        """
        Initialize the prompt optimizer.
        
        Args:
            workflow_dir: Directory containing workflow files
            workflow_name: Name of the workflow to optimize
            model_name: Name of the language model to use
            api_key: API key for the language model (if None, expects env var)
            max_bootstrapped_demos: Max examples for bootstrap few-shot
            max_labeled_demos: Max labeled examples for MIPROv2
        """
        if dspy is None:
            raise DspyDependencyError("dspy is required for prompt optimization")
            
        self.workflow_dir = Path(workflow_dir)
        self.workflow_name = workflow_name
        self.model_name = model_name
        self.max_bootstrapped_demos = max_bootstrapped_demos
        self.max_labeled_demos = max_labeled_demos
        
        try:
            # Initialize workflow manager
            self.workflow_manager = WorkflowManager(workflow_dir, workflow_name)
            
            # Initialize DSPy language model with proper configuration
            try:
                import litellm
                litellm.drop_params = True  # Drop unsupported parameters
            except ImportError:
                pass  # LiteLLM not available, DSPy will handle it
                
            if api_key:
                self.lm = dspy.LM(model=f"openai/{model_name}", api_key=api_key)
            else:
                self.lm = dspy.LM(model=f"openai/{model_name}")
            
            dspy.settings.configure(lm=self.lm)

            # Load workflow module
            self.workflow_module = self._create_workflow_module()
            
        except (WorkflowError, TrainingDataError) as e:
            # Let these propagate up since they're already handled
            raise
        except Exception as e:
            raise WorkflowError(f"Failed to initialize prompt optimizer: {e}") from e
    
    def _create_workflow_module(self) -> BaseWorkflowModule:
        """Create workflow module with prompts from YAML."""
        # Convert dictionary fields to WorkflowField list
        workflow_fields = [
            WorkflowField(
                name="input",
                field_type="input",
                description="Input data to process",
                type_hint="str",
                optional=False
            ),
            WorkflowField(
                name="expected_output",
                field_type="output",
                description="Expected output from the model",
                type_hint="str",
                optional=False
            )
        ]
        
        # Create module class dynamically based on workflow
        # Create the workflow configuration
        config = WorkflowConfig(
            name=self.workflow_name,
            description=self.workflow_manager.get_system_prompt(),
            prompts_path=self.workflow_manager.prompts_file,
            fields=workflow_fields
        )
        
        # Define metric function for optimization using fuzzy matching
        def fuzzy_match_metric(pred: Any, gold: Any, trace: Optional[Any] = None) -> float:
            """Fuzzy matching metric for optimization using semantic similarity."""
            try:
                # Convert outputs to strings for comparison
                pred_output = str(pred.expected_output).strip()
                gold_output = str(gold.expected_output).strip()
                
                # Try to parse as JSON first
                try:
                    pred_json = json.loads(pred_output)
                    gold_json = json.loads(gold_output)
                    
                    # Compare JSON structures with fuzzy matching
                    return _compare_json_fuzzy(pred_json, gold_json)
                except json.JSONDecodeError:
                    # If not JSON, do text-based fuzzy matching
                    return _compute_text_similarity(pred_output, gold_output)
                    
            except Exception as e:
                logger.warning(f"Failed to compute fuzzy match score: {e}")
                return 0.0
                
        def _compare_json_fuzzy(pred: Any, gold: Any) -> float:
            """Compare JSON structures with fuzzy matching."""
            if isinstance(pred, dict) and isinstance(gold, dict):
                # For dictionaries, compare each key-value pair
                scores = []
                for key in set(pred.keys()) | set(gold.keys()):
                    if key in pred and key in gold:
                        scores.append(_compare_json_fuzzy(pred[key], gold[key]))
                    else:
                        scores.append(0.0)  # Penalize missing keys
                return sum(scores) / len(scores) if scores else 0.0
                
            elif isinstance(pred, list) and isinstance(gold, list):
                # For lists, find best matches between elements
                if not pred or not gold:
                    return 0.0
                scores = []
                for p in pred:
                    best_score = max(_compare_json_fuzzy(p, g) for g in gold)
                    scores.append(best_score)
                return sum(scores) / len(scores)
                
            else:
                # For primitive values, use text similarity
                return _compute_text_similarity(str(pred), str(gold))
                
        def _compute_text_similarity(text1: str, text2: str) -> float:
            """Compute text similarity using various metrics."""
            # Normalize texts
            text1 = text1.lower().strip()
            text2 = text2.lower().strip()
            
            if not text1 or not text2:
                return 0.0
                
            # Exact match gets highest score
            if text1 == text2:
                return 1.0
                
            # Compute word overlap score
            words1 = set(text1.split())
            words2 = set(text2.split())
            overlap = len(words1 & words2)
            total = len(words1 | words2)
            
            if total == 0:
                return 0.0
                
            # Combine with character-level similarity
            char_sim = sum(a == b for a, b in zip(text1, text2)) / max(len(text1), len(text2))
            word_sim = overlap / total
            
            # Weight word similarity more heavily
            return 0.7 * word_sim + 0.3 * char_sim

        # Create the module class with its signature and metric
        module_class = WorkflowFactory.create_module(
            config=config,
            metric_fn=fuzzy_match_metric
        )

        return module_class() # type: ignore
    
    def _prepare_dspy_examples(self) -> List[Any]:  # Using Any since dspy.Example lacks type hints
        """Prepare training examples for DSPy."""
        training_data = self.workflow_manager.get_training_data()
        
        if not isinstance(training_data, dict) or "examples" not in training_data:
            raise TrainingDataValidationError("Training data must be a dictionary with 'examples' key")
            
        examples = training_data["examples"]
        if not isinstance(examples, list) or not examples:
            raise TrainingDataValidationError("Training data 'examples' must be a non-empty list")
            
        dspy_examples = []
        for i, example in enumerate(examples):
            try:
                if not hasattr(example, "to_dict"):
                    raise TrainingDataValidationError(f"Example {i} missing to_dict() method")
                    
                example_dict = example.to_dict()
                if not isinstance(example_dict, dict):
                    raise TrainingDataValidationError(f"Example {i} to_dict() must return a dictionary")
                    
                if "input" not in example_dict or "expected_output" not in example_dict:
                    raise TrainingDataValidationError(f"Example {i} missing required fields: input and/or expected_output")
                    
                # Validate input and expected_output are strings
                if not isinstance(example_dict["input"], str):
                    raise TrainingDataValidationError(f"Example {i} input must be a string")
                if not isinstance(example_dict["expected_output"], str):
                    raise TrainingDataValidationError(f"Example {i} expected_output must be a string")
                    
                # Create DSPy example with proper field initialization
                dspy_example = dspy.Example(
                    input=example_dict["input"],
                    expected_output=example_dict["expected_output"]
                )
                dspy_examples.append(dspy_example)
                
            except Exception as e:
                if isinstance(e, TrainingDataValidationError):
                    raise
                raise TrainingDataValidationError(f"Failed to process example {i}: {str(e)}")
        
        return dspy_examples
    
    def optimize_workflow(
        self,
        train_examples: Optional[List[Any]] = None,  # Using Any since dspy.Example lacks type hints
        dev_examples: Optional[List[Any]] = None,
        method: str = "bootstrap",
        num_threads: int = 1
    ) -> BaseWorkflowModule:
        """
        Optimize workflow prompts using DSPy.
        
        Args:
            train_examples: Optional training examples (if None, loads from data)
            dev_examples: Optional development set for evaluation
            method: Optimization method ('bootstrap' or 'mipro')
            num_threads: Number of threads for optimization
            
        Returns:
            Optimized workflow module
            
        Raises:
            TrainingDataError: If there are issues with training data
            OptimizationError: If optimization fails
            WorkflowError: If there are workflow-related issues
        """
        logger.info(f"Starting {self.workflow_name} optimization using {method}")
        
        try:
            if train_examples is None:
                train_examples = self._prepare_dspy_examples()
                
            if not train_examples:
                raise TrainingDataError("No training examples available for optimization")
            
            # Validate optimization method
            if method not in ["bootstrap", "mipro"]:
                raise OptimizationError(f"Invalid optimization method: {method}")
            
            # Optimize the module
            self.workflow_module.optimize(
                train_examples=train_examples,
                dev_examples=dev_examples,
                method=method,
                max_bootstrapped_demos=self.max_bootstrapped_demos,
                num_threads=num_threads
            )
            
            return self.workflow_module
            
        except (TrainingDataError, OptimizationError, WorkflowError):
            # Let these propagate up since they're already handled
            raise
        except Exception as e:
            error_msg = f"Failed to optimize {self.workflow_name}: {e}"
            logger.error(error_msg)
            raise OptimizationError(error_msg) from e
    
    def save_optimized_prompts(self, output_dir: Path) -> None:
        """
        Save optimized prompts to files.
        
        Args:
            output_dir: Directory to save optimized prompts
            
        Raises:
            OptimizationError: If saving prompts fails
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create workflow-specific output directory
            workflow_dir = output_dir / self.workflow_name
            workflow_dir.mkdir(exist_ok=True)
            
            # Save the optimized prompts
            self.workflow_module.save_optimized_prompts(workflow_dir)
            
        except Exception as e:
            error_msg = f"Failed to save {self.workflow_name} prompts: {e}"
            logger.error(error_msg)
            raise OptimizationError(error_msg) from e
    
    def run_full_optimization(
        self,
        output_dir: Path,
        optimization_method: str = "bootstrap",
        num_threads: int = 1
    ) -> Dict[str, Any]:
        """
        Run the complete optimization pipeline.
        
        Args:
            output_dir: Directory to save results
            optimization_method: 'bootstrap' or 'mipro'
            num_threads: Number of threads for optimization
            
        Returns:
            Dictionary with optimization results and statistics
            
        Raises:
            TrainingDataError: If there are issues with training data
            OptimizationError: If optimization fails
            WorkflowError: If there are workflow-related issues
        """
        logger.info("Starting prompt optimization pipeline")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Get training data statistics
            training_data = self.workflow_manager.get_training_data()
            stats = training_data["stats"]
            logger.info(f"Training data statistics: {stats}")
            
            results: Dict[str, Any] = {
                "workflow": self.workflow_name,
                "training_data_stats": stats,
                "optimization_method": optimization_method,
                "model_name": self.model_name,
                "status": "pending",
                "save_prompts": "pending"
            }
            
            # Run optimization
            module = self.optimize_workflow(
                method=optimization_method,
                num_threads=num_threads
            )
            
            if not module:
                raise OptimizationError("Optimization failed to produce a valid module")
                
            results["status"] = "success"
            
            # Save optimized prompts
            self.save_optimized_prompts(output_dir)
            results["save_prompts"] = "success"
            
            # Save results summary
            results_file = output_dir / "optimization_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Optimization pipeline complete. Results saved to {results_file}")
            return results
            
        except (TrainingDataError, OptimizationError, WorkflowError) as e:
            # Log the error but let it propagate up
            logger.error(str(e))
            raise
        except Exception as e:
            error_msg = f"Unexpected error during optimization: {e}"
            logger.error(error_msg)
            raise OptimizationError(error_msg) from e