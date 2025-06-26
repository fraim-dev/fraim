from pathlib import Path

from .types import ExitCode
from .test_specification import TestSpecification


class TestExecutor:
    def __init__(self, test_dir: Path, test_spec: TestSpecification) -> None:
        self.test_dir = test_dir
        self.workflow, self.test_case = test_spec.unwrap()
        self.test_case_dir = test_dir / self.workflow / self.test_case
    
    def run_test(self) -> ExitCode:
        print(f"TestExecutor: Running {self.workflow}:{self.test_case}")
        return ExitCode.SUCCESS 