import importlib.util
import inspect
import pkgutil

from fraim.core.workflows import Workflow


def discover_builtins(package: str) -> dict[str, type[Workflow]]:
    """
    Import all modules under the built-in workflows package and register classes.
    """
    discovered_workflows: dict[str, type[Workflow]] = {}
    try:
        pkg = importlib.import_module(package)
    except ModuleNotFoundError:
        raise

    if not hasattr(pkg, "__path__"):
        return discovered_workflows

    for module in pkgutil.walk_packages(pkg.__path__, package + "."):
        imported_module = importlib.import_module(module.name)
        # Find all classes in the module that are subclasses of Workflow
        for workflow_name, workflow_class in inspect.getmembers(imported_module, inspect.isclass):
            # Ensure it's a subclass of Workflow but not Workflow itself
            if issubclass(workflow_class, Workflow) and workflow_class is not Workflow:
                discovered_workflows[workflow_class.name] = workflow_class

    return discovered_workflows


def discover_workflows() -> dict[str, type[Workflow]]:
    return discover_builtins("fraim.workflows")
