# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import inspect
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, get_type_hints

from pydantic import BaseModel, create_model


def merge_models(
    base_module: ModuleType, overlay_module: ModuleType, register_in_caller: bool = True
) -> SimpleNamespace:
    """
    Merge Pydantic models from a base module with overlays from an overlay module.

    This function creates a new set of Pydantic models by combining base models with
    their corresponding overlay models. The overlay models can add new fields, modify
    existing field types, or change default values. The function handles recursive
    model relationships, ensuring that nested BaseModel references are also properly
    overlaid.

    This function enables extending base model definitions without direct modification.
    Common use cases include:

    - **Workflow-specific extensions**: Allow workflows to augment base SARIF models
        with additional fields (confidence scores, remediation, custom metadata)

    - **Plugin architectures**: Enable plugins to extend core models while
        maintaining system compatibility

    - **Environment/domain customizations**: Adapt models for different environments
        or allow domain experts to add specialized fields

    Args:
        base_module: A Python module containing Pydantic BaseModel classes that serve
            as the foundation models.
        overlay_module: A Python module containing Pydantic BaseModel classes that
            define modifications to apply to the base models. Models in this module
            should have the same names as their corresponding base models.
        register_in_caller: If True, register the enhanced models in the calling module
            for proper pickling support. Defaults to True.

    Returns:
        SimpleNamespace: An object containing the merged models as attributes. Each
            attribute name corresponds to a model name from the base module, and the
            value is the merged Pydantic model class.

    Raises:
        ValueError: If a model referenced in the overlay module is not found in the
            base module.

    Behavior:
        - Only processes classes that inherit from Pydantic's BaseModel
        - Base models without corresponding overlay models are included unchanged
        - Overlay models completely override base model fields (field-level merging)
        - Recursively processes nested BaseModel references in field types
        - Handles complex types including List, Tuple, Dict, Set, and Union types
        - Uses caching to handle circular model references efficiently
        - Preserves full Field metadata including descriptions, constraints, and validation rules
        - Registers enhanced models in the calling module for pickling support

    Example:
        >>> # output/sarif.py
        >>> class Result(BaseModel):
        ...     message: str
        ...     level: str = "warning"

        >>> # workflows/code/sarif_extensions.py
        >>> class Result(BaseModel):
        ...     message: str
        ...     level: str = "warning"
        ...     confidence: int = 5
        ...     remediation: Optional[str] = None

        >>> import outputs.sarif, workflows.code.sarif_extensions
        >>> output = merge_models(outputs.sarif, workflows.code.sarif_extensions)
        >>> # output.Result now includes confidence and remediation fields
        >>> # for workflow-specific SARIF result processing
    """
    merged_cache: dict[str, type[BaseModel]] = {}
    result: SimpleNamespace = SimpleNamespace()

    # Get the calling module for registration
    cur_frame = inspect.currentframe()
    if not cur_frame:
        raise ValueError("No current frame found")
    caller_frame = cur_frame.f_back
    if not caller_frame:
        raise ValueError("No caller frame found")
    caller_module = inspect.getmodule(caller_frame)
    if not caller_module:
        raise ValueError("No caller module found")

    base_classes = {
        name: obj for name, obj in vars(base_module).items() if inspect.isclass(obj) and issubclass(obj, BaseModel)
    }

    overlay_classes = {
        name: obj for name, obj in vars(overlay_module).items() if inspect.isclass(obj) and issubclass(obj, BaseModel)
    }

    def resolve_model(name: str) -> type[BaseModel]:
        if name in merged_cache:
            return merged_cache[name]

        base_cls = base_classes.get(name)
        overlay_cls = overlay_classes.get(name)

        if base_cls is None:
            raise ValueError(f"Model {name} not found in base module")

        fields: dict[str, tuple[Any, Any]] = {}

        # Start from base model fields
        base_hints = get_type_hints(base_cls, include_extras=True)
        for fname, f in base_cls.model_fields.items():
            fields[fname] = (base_hints[fname], f)

        # Apply overlay (if present)
        if overlay_cls:
            overlay_hints = get_type_hints(overlay_cls, include_extras=True)
            for fname, f in overlay_cls.model_fields.items():
                fields[fname] = (overlay_hints[fname], f)

        # Recursively rebind BaseModel fields to their overlays
        for fname, (typ, field_info) in fields.items():
            origin = getattr(typ, "__origin__", None)
            args = getattr(typ, "__args__", ())

            def resolve_typ(t: Any) -> Any:
                if inspect.isclass(t) and issubclass(t, BaseModel):
                    tname = t.__name__
                    if tname in base_classes:
                        return resolve_model(tname)
                return t

            if origin in (
                list,
                tuple,
                dict,
                set,
                Union := getattr(sys.modules["typing"], "Union", None),
            ):  # TODO: just import typing.Union...
                rebased = tuple(resolve_typ(t) for t in args)
                fields[fname] = (origin[rebased], field_info)  # type: ignore[index]
            else:
                fields[fname] = (resolve_typ(typ), field_info)

        merged: type[BaseModel] = create_model(name, __base__=base_cls, **fields)  # type: ignore[call-overload]

        # Register the model in the calling module for pickling support
        if register_in_caller and caller_module:
            setattr(caller_module, name, merged)
            merged.__module__ = caller_module.__name__
            merged.__qualname__ = name

        merged_cache[name] = merged
        return merged

    # Build full model set with overlays
    for name in base_classes:
        setattr(result, name, resolve_model(name))

    return result
