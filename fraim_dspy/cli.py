"""
Command-line interface for DSPy prompt optimization.

This module provides a CLI for running prompt optimization on Fraim's
code analysis workflows using DSPy.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Tuple, Type

from .optimizer import PromptOptimizer
from .training_data import TrainingDataManager, create_training_example_class, TrainingDataValidationError


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("dspy_optimization.log")
        ]
    )


def get_standard_fields() -> Dict[str, Tuple[Type, str]]:
    """Get standard fields for all workflows."""
    return {
        "input": (str, "Input data to process"),
        "expected_output": (str, "Expected output from the model")
    }


def cmd_validate_workflow(args: argparse.Namespace) -> None:
    """Validate workflow training data."""
    workflow_dir = Path(args.workflow_dir)
    training_file = workflow_dir / f"{args.workflow}_training_data.csv"
    prompts_file = workflow_dir / f"{args.workflow}_prompts.yaml"
    
    if not workflow_dir.exists():
        print(f"❌ Workflow directory not found: {workflow_dir}")
        sys.exit(1)
    
    if not training_file.exists():
        print(f"❌ Training data file not found: {training_file}")
        sys.exit(1)
        
    if not prompts_file.exists():
        print(f"❌ Prompts file not found: {prompts_file}")
        sys.exit(1)
    
    example_class = create_training_example_class(
        f"{args.workflow.title()}TrainingExample",
        get_standard_fields()
    )
    training_manager = TrainingDataManager(
            data_dir=workflow_dir,
            example_class=example_class,
            data_file_name=f"{args.workflow}_training_data.csv"
        )
    try:
        training_manager.validate_training_data()
        issues = []
    except TrainingDataValidationError as e:
        issues = [str(e)]
    
    if not issues:
        print("✅ All workflow training data is valid!")
    else:
        print("❌ Training data validation issues found:")
        for issue in issues:
            print(f"  - {issue}")


def cmd_show_stats(args: argparse.Namespace) -> None:
    """Show workflow training data statistics."""
    workflow_dir = Path(args.workflow_dir)
    example_class = create_training_example_class(
        f"{args.workflow.title()}TrainingExample",
        get_standard_fields()
    )
    training_manager = TrainingDataManager(
            data_dir=workflow_dir,
            example_class=example_class,
            data_file_name=f"{args.workflow}_training_data.csv"
        )
    stats = training_manager.get_data_statistics()
    
    print(f"📊 Training Data Statistics for {args.workflow}:")
    print(f"  Total examples: {stats['total_examples']}")
    
    for field, distribution in stats.items():
        if field.endswith('_distribution'):
            field_name = field.replace('_distribution', '')
            print(f"\n  {field_name} distribution:")
            for value, count in distribution.items():
                print(f"    {value}: {count}")


def cmd_optimize(args: argparse.Namespace) -> None:
    """Run prompt optimization for a specific workflow."""
    workflow_dir = Path(args.workflow_dir)
    training_file = workflow_dir / f"{args.workflow}_training_data.csv"
    prompts_file = workflow_dir / f"{args.workflow}_prompts.yaml"
    
    if not workflow_dir.exists():
        print(f"❌ Workflow directory not found: {workflow_dir}")
        sys.exit(1)
    
    if not training_file.exists():
        print(f"❌ Training data file not found: {training_file}")
        sys.exit(1)
        
    if not prompts_file.exists():
        print(f"❌ Prompts file not found: {prompts_file}")
        sys.exit(1)
    
    optimizer = PromptOptimizer(
        workflow_dir=workflow_dir,
        workflow_name=args.workflow,
        model_name=args.model,
        api_key=args.api_key,
        max_bootstrapped_demos=args.max_demos,
        max_labeled_demos=args.max_labeled_demos
    )

    results = optimizer.run_full_optimization(
        output_dir=args.output_dir,
        optimization_method=args.method,
        num_threads=args.threads
    )
    
    print("🎯 Optimization Results:")
    for key, value in results.items():
        if key == "training_data_stats":
            continue  # Skip detailed stats
        print(f"  {key}: {value}")


# Common optimization arguments
def add_optimization_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workflow-dir",
        type=str,
        required=True,
        help="Directory containing workflow files (prompts and training data)"
    )
    parser.add_argument(
        "--workflow",
        type=str,
        required=True,
        help="Name of the workflow to optimize (e.g., 'scanner', 'triager')"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="./fraim_dspy/output",
        help="Directory to save optimized prompts"
    )
    parser.add_argument(
        "--model",
        default="gpt-4",
        help="Language model to use for optimization"
    )
    parser.add_argument(
        "--api-key",
        help="API key for the language model (uses env var if not provided)"
    )
    parser.add_argument(
        "--method",
        choices=["bootstrap", "mipro"],
        default="bootstrap",
        help="Optimization method to use"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="Number of threads for optimization"
    )
    parser.add_argument(
        "--max-demos",
        type=int,
        default=4,
        help="Maximum number of bootstrapped demos"
    )
    parser.add_argument(
        "--max-labeled-demos",
        type=int,
        default=16,
        help="Maximum number of labeled demos for MIPROv2"
    )


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DSPy prompt optimization for Fraim code workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate workflow training data
  python -m fraim_dspy.cli validate --workflow-dir ./fraim/workflows/code --workflow scanner
  
  # Show workflow training data statistics
  python -m fraim_dspy.cli stats --workflow-dir ./fraim/workflows/code --workflow scanner
  
  # Run optimization for a workflow
  python -m fraim_dspy.cli optimize --workflow-dir ./fraim/workflows/code --workflow scanner
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate workflow training data"
    )
    validate_parser.add_argument(
        "--workflow-dir",
        type=str,
        required=True,
        help="Directory containing workflow files"
    )
    validate_parser.add_argument(
        "--workflow",
        type=str,
        required=True,
        help="Name of the workflow to validate"
    )
    validate_parser.set_defaults(func=cmd_validate_workflow)
    
    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show workflow training data statistics"
    )
    stats_parser.add_argument(
        "--workflow-dir",
        type=str,
        required=True,
        help="Directory containing workflow files"
    )
    stats_parser.add_argument(
        "--workflow",
        type=str,
        required=True,
        help="Name of the workflow to show stats for"
    )
    stats_parser.set_defaults(func=cmd_show_stats)
    
    # Full optimization command
    optimize_parser = subparsers.add_parser(
        "optimize",
        help="Run prompt optimization"
    )
    add_optimization_args(optimize_parser)
    optimize_parser.set_defaults(func=cmd_optimize)
    
    # Parse arguments and run command
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    setup_logging(args.verbose)
    
    try:
        args.func(args)
    except Exception as e:
        logging.error(f"Command failed: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()