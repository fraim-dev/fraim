# Workflows System

This directory contains the workflow system for Fraim, organized around a registry pattern that makes it easy to add new workflows.

## Registry Architecture

The workflow system uses a registry pattern that automatically discovers and routes workflows. Workflows are Python classes that extend the `Workflow` base class and are registered using a decorator.

```python
from fraim.workflows.registry import workflow
from fraim.core.workflows import Workflow

@workflow('my_workflow')
class MyWorkflow(Workflow):
    """My custom security workflow"""

    def __init__(self):
        # Initialize your workflow
        pass

    async def workflow(self, input) -> List[sarif.Result]:
        # Implement your workflow logic
        # input.code - the code to analyze
        # input.config - the global configuration
        return results
```

## Adding a New Workflow

### 1. Create the Workflow Class

Create a new file `fraim/workflows/my_workflow/workflow.py`:

```python
"""
My Custom Security Workflow

Description of what this workflow analyzes.
"""
from typing import List, Any
from fraim.core.workflows import Workflow
from fraim.outputs import sarif

FILE_PATTERNS = ['*.py', '*.js', '*.ts']


class MyWorkflow(Workflow):
    """Analyzes code for custom security issues"""

    def __init__(self, args: type[Any]):
        super().__init__(args)
        # Initialize your workflow components (LLM, parsers, etc.)

    async def workflow(self, input) -> List[sarif.Result]:
        # Access the code and configuration
        code = input.code
        config = input.config

        # Implement your analysis logic here
        results = []

        # Return SARIF results
        return results
```

### 2. Register the Workflow

Update `fraim/workflows/__init__.py` to import your workflow:

```python
# Import all workflows to trigger their registration
from .code import workflow as code_workflow
from .my_workflow import workflow as my_workflow  # Add this line
```

### 3. Run the Workflow

```bash
fraim my_workflow <other_args>
```

## Workflow Input

All workflows receive a standardized input object with:
- `input.code` - A `Contextual[str]` containing the code to analyze
- `input.config` - The global `Config` object with settings

## Workflow Output

All workflows must return a `List[sarif.Result]` containing their findings in SARIF format.
