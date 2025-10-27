# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Hashing utilities for caching and data integrity"""

import dataclasses
import hashlib
import json
from typing import Any


def compute_hash(data: Any) -> str:
    """Compute a stable SHA-256 hash of arbitrary data.

    Args:
        data: Any Python object to hash

    Returns:
        Hex string of the hash
    """
    normalized = _normalize_for_hash(data)
    json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def _normalize_for_hash(obj: Any) -> Any:
    """Normalize an object to a JSON-serializable form for hashing.

    Handles:
    - Dataclasses → dict
    - Dicts → sorted dict
    - Lists/tuples → lists
    - Pydantic models → dict
    - Other objects → class name + repr (best effort)
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if dataclasses.is_dataclass(obj):
        return {
            "__dataclass__": obj.__class__.__name__,
            "data": _normalize_for_hash(dataclasses.asdict(obj)),  # type: ignore[arg-type]
        }

    if isinstance(obj, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(obj.items())}

    if isinstance(obj, (list, tuple)):
        return [_normalize_for_hash(item) for item in obj]

    # Handle Pydantic models
    if hasattr(obj, "model_dump"):
        return {
            "__pydantic__": obj.__class__.__name__,
            "data": _normalize_for_hash(obj.model_dump()),
        }

    # Handle objects with __dict__
    if hasattr(obj, "__dict__"):
        return {
            "__class__": obj.__class__.__name__,
            "data": _normalize_for_hash(obj.__dict__),
        }

    # Fallback: use repr
    return {
        "__repr__": obj.__class__.__name__,
        "value": repr(obj),
    }
