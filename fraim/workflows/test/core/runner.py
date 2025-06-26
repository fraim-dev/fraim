import inspect
import sys
from pathlib import Path
from typing import Dict, List

from fraim.workflows.registry import get_available_workflows

from .executor import TestExecutor
from .recorder import TestRecorder
from .test_specification import TestSpecification
from .types import ExitCode, WorkflowName


class TestRunner:    
    def __init__(self) -> None:
        pass
    
    @staticmethod
    def log_error(message: str) -> None:
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            caller_filename = Path(caller_frame.f_code.co_filename).name
            print(f"{caller_filename}: error: {message}", file=sys.stderr)
        finally:
            del frame

    def _get_test_data(self) -> Dict[str, List[str]]:
        available_workflows = get_available_workflows()
        test_dir = Path(__file__).parent.parent
        test_data = {}
        
        for workflow in sorted(available_workflows):
            workflow_test_dir = test_dir / workflow
            
            if workflow_test_dir.exists() and workflow_test_dir.is_dir():
                test_cases = [
                    d.name for d in workflow_test_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.')
                ]
                test_data[workflow] = sorted(test_cases)
            else:
                test_data[workflow] = None
        
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
    
    def get_available_test_specs(self) -> List[TestSpecification]:
        test_data = self._get_test_data()
        test_specs = []
        
        for workflow, test_cases in test_data.items():
            if test_cases:
                for test_case in test_cases:
                    test_specs.append(TestSpecification(f"{workflow}:{test_case}"))
        
        return test_specs
    
    def verify_workflows_exist(self, workflows: List[str], available_specs: List[TestSpecification]) -> bool:
        available_workflows = {spec.workflow for spec in available_specs}
        for workflow in workflows:
            if workflow not in available_workflows:
                TestRunner.log_error(f"Unknown workflow: {workflow}")
                return False
        return True
    
    def run_tests(self, test_specs: List[TestSpecification], record: bool = False) -> ExitCode:
        if not test_specs:
            TestRunner.log_error("No test specifications provided")
            return ExitCode.ERROR
        
        test_dir = Path(__file__).parent.parent
        failed_tests = []
        for spec in test_specs:
            if record:
                recorder = TestRecorder(test_dir, spec)
                result = recorder.record_test()
            else:
                executor = TestExecutor(test_dir, spec)
                result = executor.run_test()
            
            if result != ExitCode.SUCCESS:
                failed_tests.append(str(spec))
        
        if failed_tests:
            if record:
                TestRunner.log_error(f"Failed to record {len(failed_tests)} test(s): {', '.join(failed_tests)}")
            else:
                TestRunner.log_error(f"Failed {len(failed_tests)} test(s): {', '.join(failed_tests)}")
            return ExitCode.ERROR
        
        return ExitCode.SUCCESS 