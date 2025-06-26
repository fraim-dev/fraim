import sys
from pathlib import Path
from typing import Dict, List

from fraim.workflows.registry import get_available_workflows

ExitCode = int
WorkflowName = str
TestSpecification = str


class TestRunner:    
    def __init__(self) -> None:
        pass
    
    def _log_error(self, message: str) -> None:
        """Log error message in consistent format."""
        print(f"fraim.workflows.test: error: {message}", file=sys.stderr)
    
    def _get_test_data(self) -> Dict[str, List[str]]:
        available_workflows = get_available_workflows()
        test_dir = Path(__file__).parent
        test_data = {}
        
        for workflow in sorted(available_workflows):
            workflow_test_dir = test_dir / workflow
            
            if workflow_test_dir.exists() and workflow_test_dir.is_dir():
                test_cases = [
                    d.name for d in workflow_test_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.')
                ]
                test_data[workflow] = sorted(test_cases) if test_cases else []
            else:
                test_data[workflow] = None  # Indicates directory doesn't exist
        
        return test_data

    def list_available_tests(self) -> None:
        test_data = self._get_test_data()
        
        print("=" * 50)
        print("Available tests:")
        
        for workflow, test_cases in test_data.items():
            if test_cases is None:
                print(f"\n{workflow}: (no test directory)")
            elif not test_cases:
                print(f"\n{workflow}: (no tests found)")
            else:
                print(f"\n{workflow}:")
                for test_case in test_cases:
                    print(f"  - {test_case}")
        
        print("=" * 50)
    
    def run_all_tests(self, record: bool = False) -> ExitCode:
        test_data = self._get_test_data()
        test_specs = []
        
        for workflow, test_cases in test_data.items():
            if test_cases:  # Skip workflows with no tests or no directory
                for test_case in test_cases:
                    test_specs.append(f"{workflow}:{test_case}")
        
        if not test_specs:
            self._log_error("No tests found to run")
            return 1

        return self.run_specific_tests(test_specs, record=record)
    
    def run_workflow_tests(self, workflows: List[WorkflowName], record: bool = False) -> ExitCode:
        test_data = self._get_test_data()
        test_specs = []
        
        for workflow in workflows:
            if workflow not in test_data:
                self._log_error(f"Unknown workflow: {workflow}")
                return 1
            
            test_cases = test_data[workflow]
            if test_cases is None:
                self._log_error(f"No test directory found for workflow: {workflow}")
                return 1
            elif not test_cases:
                self._log_error(f"No tests found for workflow: {workflow}")
                return 1
            else:
                for test_case in test_cases:
                    test_specs.append(f"{workflow}:{test_case}")
        
        return self.run_specific_tests(test_specs, record=record)
    
    def run_specific_tests(self, test_specs: List[TestSpecification], record: bool = False) -> ExitCode:
        # TODO: Implement specific test running
        print(f"Running specific tests: {test_specs} (record={record})")
        return 0