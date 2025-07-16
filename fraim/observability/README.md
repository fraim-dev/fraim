# LLM Observability System

This package provides an extensible, opt-in observability system for monitoring LLM API calls in the fraim security scanner.

## Architecture

The observability system is built around a plugin architecture that makes it easy to add new monitoring backends:

```
fraim/observability/
├── __init__.py          # Package initialization and backend registration
├── base.py              # Abstract base class for backends
├── registry.py          # Backend registry and management
├── manager.py           # Observability setup and coordination
└── backends/
    ├── __init__.py
    ├── langfuse.py      # Langfuse backend implementation
    └── example_wandb.py # Example of how to add new backends
```

## Usage

### Basic Usage

```bash
# No observability (default)
python -m fraim.cli code --location https://github.com/example/repo

# Enable Langfuse observability
python -m fraim.cli --observability langfuse code --location https://github.com/example/repo

```

### Setting Up Langfuse

1. **Get your API keys:**

   - Local: Go to `http://localhost:3000`, create a project, get keys from Settings > API Keys
   - Cloud: Go to `https://cloud.langfuse.com`, create account/project, get keys

2. **Set environment variables:**

   ```bash
   export LANGFUSE_PUBLIC_KEY="pk-lf-your-key-here"
   export LANGFUSE_SECRET_KEY="sk-lf-your-key-here"
   export LANGFUSE_HOST="http://localhost:3000"  # optional, defaults to localhost
   ```

3. **Run with observability:**
   ```bash
   python -m fraim.cli --observability langfuse code --location https://github.com/example/repo
   ```

## Adding New Backends

To add a new observability backend:

1. **Create a backend class** in `fraim/observability/backends/`:

```python
from ..base import ObservabilityBackend

class MyBackend(ObservabilityBackend):
    def get_name(self) -> str:
        return "mybackend"

    def get_description(self) -> str:
        return "My custom observability backend"

    def get_required_env_vars(self) -> List[str]:
        return ["MY_API_KEY"]

    def get_optional_env_vars(self) -> Dict[str, str]:
        return {"MY_HOST": "https://api.myservice.com"}

    def validate_config(self) -> bool:
        # Check if required env vars are set
        pass

    def setup_callbacks(self) -> List[str]:
        return ["mybackend"]  # Must be supported by litellm

    def get_config_help(self) -> str:
        return "Configuration help for MyBackend..."
```

2. **Register the backend** in `fraim/observability/__init__.py`:

```python
from .backends.mybackend import MyBackend
ObservabilityRegistry.register(MyBackend())
```

3. **Test the backend:**

```bash
python -m fraim.cli --help  # Should show your backend in the list
python -m fraim.cli --observability mybackend code --location ...
```

The CLI automatically picks up new backends through the `build_observability_arg()` helper function, so no CLI changes are needed.

## Backend Interface

All backends must implement the `ObservabilityBackend` abstract base class:

- `get_name()`: Return unique backend name
- `get_description()`: Return short description for CLI help
- `get_required_env_vars()`: List of required environment variables
- `get_optional_env_vars()`: Dict of optional env vars with defaults
- `validate_config()`: Check if backend is properly configured
- `setup_callbacks()`: Return litellm callback names
- `get_config_help()`: Return user-friendly configuration help
- `setup_environment()`: Optional custom environment setup

## Configuration Help

When a backend is not properly configured, the system automatically displays detailed configuration instructions. For example, if you try to use Langfuse without setting the required environment variables, you'll see:

```
WARNING: langfuse not configured properly
INFO: Configuration help for langfuse:
  Langfuse Configuration:
  Required environment variables:
    LANGFUSE_PUBLIC_KEY - Your Langfuse public key (starts with pk-lf-...)
    LANGFUSE_SECRET_KEY - Your Langfuse secret key (starts with sk-lf-...)
  ...
```

## Status and Debugging

The `ObservabilityManager` requires a logger and provides status information:

```python
from fraim.observability import ObservabilityManager

# The manager requires a logger parameter
manager = ObservabilityManager(['langfuse'], logger=config.logger)
manager.setup()

status = manager.get_status()
# Returns: {
#   'enabled': ['langfuse'],
#   'configured': ['langfuse'],  # Successfully configured
#   'failed': [],                # Failed to configure
#   'total_requested': 1,
#   'total_configured': 1
# }
```

## Future Backends

The architecture supports any observability backend that litellm supports or can be extended to support:

- **WandB**: For experiment tracking and visualization
- **OpenTelemetry**: For distributed tracing
- **Custom backends**: For internal monitoring systems
- **Multiple backends**: Can enable multiple backends simultaneously

Example for multiple backends:

```bash
python -m fraim.cli --observability langfuse wandb ... code --location
```
