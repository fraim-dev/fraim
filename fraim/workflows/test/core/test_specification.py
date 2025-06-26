import re
from typing import Tuple

class TestSpecification:
    _PATTERN = re.compile(r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$')
    
    def __init__(self, spec: str) -> None:
        if not self.is_valid(spec):
            raise ValueError(f"Invalid test specification format: '{spec}'. Expected: 'workflow:test_case'")
        
        workflow, test_case = spec.split(':', 1)
        self._workflow = workflow
        self._test_case = test_case
        self._spec = spec
    
    def __repr__(self) -> str:
        return f"TestSpecification('{self._spec}')"
    
    def __str__(self) -> str:
        return self._spec
    
    @classmethod
    def is_valid(cls, spec: str) -> bool:
        return bool(cls._PATTERN.match(spec))
    
    @property
    def test_case(self) -> str:
        return self._test_case
    
    @property
    def workflow(self) -> str:
        return self._workflow
    
    def matches_workflow(self, workflow: str) -> bool:
        return self._workflow == workflow
    
    def unwrap(self) -> Tuple[str, str]:
        return self._workflow, self._test_case 