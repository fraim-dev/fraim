# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Cache storage and retrieval for LLM API calls"""

import dataclasses
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir  # type: ignore[import-untyped]

# Cache version - increment this to invalidate all existing caches
CACHE_VERSION = 1


def is_caching_enabled() -> bool:
    """Check if LLM caching is enabled via environment variable.

    Returns:
        True if FRAIM_ENABLE_LLM_CACHE is set to a truthy value
    """
    return os.getenv("FRAIM_ENABLE_LLM_CACHE", "").lower() in ("true", "1", "yes", "on")


def get_default_cache_dir() -> str:
    """Get the default cache directory.

    Uses FRAIM_CACHE_DIR environment variable if set,
    otherwise uses platformdirs to get the user cache directory.

    Returns:
        Path to the cache directory
    """
    env_cache = os.getenv("FRAIM_CACHE_DIR")
    if env_cache:
        return env_cache
    return str(user_cache_dir("fraim"))


class LLMCache:
    """Manages cache storage for LLM API calls.

    Can be used as a callable wrapper around async functions:
        cached_completion = cache(completion_function)
        result = await cached_completion(**params)

    Storage structure:
        {cache_dir}/llm/{request_hash}.json

    Each cache file includes:
    - version: Cache format version
    - request: The LLM request parameters (for debugging)
    - response: The cached LLM response
    """

    def __init__(self, cache_dir: str | None = None):
        """Initialize LLM cache manager.

        Args:
            cache_dir: Root directory for cache storage. If None, uses default.
        """
        if cache_dir is None:
            cache_dir = get_default_cache_dir()
        self.cache_dir = Path(cache_dir) / "llm"
        self.enabled = is_caching_enabled()

    def __call__(self, func: Any) -> Any:
        """Wrap an async function with caching.

        Args:
            func: Async function to wrap with caching

        Returns:
            Wrapped async function that checks cache before calling original
        """
        from fraim.core.utils.hash import compute_hash

        async def wrapper(**kwargs: Any) -> Any:
            # If caching is disabled, just call the function
            if not self.enabled:
                return await func(**kwargs)

            # Compute hash of all request parameters
            request_hash = compute_hash(kwargs)

            # Check cache
            cached_response = self.load(request_hash)
            if cached_response is not None:
                return cached_response

            # Cache miss - call the function
            response = await func(**kwargs)

            # Save to cache
            self.save(request_hash, kwargs, response)

            return response

        return wrapper

    def save(self, request_hash: str, request_data: dict[str, Any], response_data: Any) -> None:
        """Save LLM request and response to cache.

        Args:
            request_hash: Hash of the request parameters
            request_data: The LLM request (for debugging)
            response_data: The LLM response to cache
        """
        cache_path = self._get_cache_path(request_hash)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            "version": CACHE_VERSION,
            "request": request_data,
            "request_hash": request_hash,
            "response": self._serialize(response_data),
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

    def load(self, request_hash: str) -> Any | None:
        """Load cached LLM response if it exists.

        Args:
            request_hash: Hash of the request parameters

        Returns:
            Cached response data, or None if not found
        """
        cache_path = self._get_cache_path(request_hash)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                cache_data = json.load(f)

            # Check version compatibility
            if cache_data.get("version") != CACHE_VERSION:
                # Wrong version, treat as cache miss
                return None

            return self._deserialize(cache_data["response"])
        except (json.JSONDecodeError, KeyError, OSError, ImportError, AttributeError):
            # Cache is corrupted or invalid, treat as miss
            return None

    def _get_cache_path(self, request_hash: str) -> Path:
        """Get the path to a cache file."""
        return self.cache_dir / f"{request_hash}.json"

    def _serialize(self, obj: Any) -> Any:
        """Serialize an object to JSON-compatible format.

        Handles dataclasses, Pydantic models, and nested structures.
        """
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj

        if dataclasses.is_dataclass(obj):
            return {
                "__dataclass__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "data": {k: self._serialize(v) for k, v in dataclasses.asdict(obj).items()},  # type: ignore[arg-type]
            }

        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}

        if isinstance(obj, (list, tuple)):
            return [self._serialize(item) for item in obj]

        # Handle Pydantic models
        if hasattr(obj, "model_dump"):
            return {
                "__pydantic__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "data": obj.model_dump(),
            }

        # Fallback: try to convert to dict or use repr
        if hasattr(obj, "__dict__"):
            return {
                "__object__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                "data": self._serialize(obj.__dict__),
            }

        # Last resort: string representation
        return str(obj)

    def _deserialize(self, data: Any) -> Any:
        """Deserialize data from JSON format back to Python objects.

        Reconstructs dataclasses and Pydantic models from their JSON representation.
        """
        if data is None or isinstance(data, (bool, int, float, str)):
            return data

        if isinstance(data, list):
            return [self._deserialize(item) for item in data]

        if isinstance(data, dict):
            # Check if this is a serialized object
            if "__dataclass__" in data:
                # Reconstruct dataclass
                class_path = data["__dataclass__"]
                obj_data = {k: self._deserialize(v) for k, v in data["data"].items()}
                return self._reconstruct_class(class_path, obj_data)

            if "__pydantic__" in data:
                # Reconstruct Pydantic model
                class_path = data["__pydantic__"]
                return self._reconstruct_class(class_path, data["data"])

            if "__object__" in data:
                # Generic object - return as dict
                return {k: self._deserialize(v) for k, v in data["data"].items()}

            # Regular dict
            return {k: self._deserialize(v) for k, v in data.items()}

        return data

    def _reconstruct_class(self, class_path: str, data: dict[str, Any]) -> Any:
        """Reconstruct a class instance from module path and data.

        Args:
            class_path: Full module path to the class (e.g., "mymodule.MyClass")
            data: Dictionary of data to initialize the class

        Returns:
            Reconstructed class instance
        """
        # Split module path and class name
        parts = class_path.rsplit(".", 1)
        if len(parts) != 2:
            # Can't reconstruct, return as dict
            return data

        module_name, class_name = parts

        # Import the module and get the class
        import importlib

        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)

            # Try to instantiate
            if dataclasses.is_dataclass(cls):
                # Cast to Callable to satisfy type checker
                constructor: Callable[..., Any] = cls  # type: ignore[assignment]
                return constructor(**data)
            if hasattr(cls, "model_validate"):  # Pydantic v2
                return cls.model_validate(data)
            if hasattr(cls, "parse_obj"):  # Pydantic v1
                return cls.parse_obj(data)  # type: ignore[attr-defined]
            # Unknown type, return as dict
            return data
        except (ImportError, AttributeError, TypeError):
            # Can't reconstruct, return as dict
            return data
