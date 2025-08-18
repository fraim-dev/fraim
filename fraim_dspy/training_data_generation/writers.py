import csv
import json
import logging
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Set

from .serialization import LiteralDumper, LiteralString
import yaml  # type: ignore[import-untyped]
from . import models as _models
from .models import CVEData, CodeChange


logger = logging.getLogger(__name__)


def _get_cve_data_fieldnames() -> List[str]:
    """Get all field names from the CVEData class and its nested dataclasses.

    Returns a stable, sorted list of field names.
    """
    field_set: Set[str] = set()
    for f in fields(CVEData):
        field_set.add(f.name)
    # Add fields from nested CodeChange class
    for f in fields(CodeChange):
        field_set.add(f.name)
    return sorted(field_set)


def _convert_cve_data_to_dict(data: CVEData) -> Dict[str, Any]:
    """Convert a CVEData object to a dictionary suitable for CSV/YAML writing.

    Handles nested CodeChange objects and list fields.
    """
    result = {}
    for f in fields(CVEData):
        value = getattr(data, f.name)
        if f.name == 'code_changes' and value:
            # Convert list of CodeChange objects to list of dicts
            code_changes = []
            for change in value:
                change_dict = {}
                for cf in fields(CodeChange):
                    change_dict[cf.name] = getattr(change, cf.name)
                code_changes.append(change_dict)
            result[f.name] = json.dumps(code_changes)
        elif isinstance(value, list):
            # Convert other list fields to JSON strings
            result[f.name] = json.dumps(value)
        else:
            result[f.name] = value
    return result


def write_scanner_csv(data: List[CVEData], file_path: Path) -> None:
    if not data:
        logger.warning("No scanner training data to write")
        return
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = _get_cve_data_fieldnames()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_convert_cve_data_to_dict(item) for item in data)
    logger.info(f"Wrote {len(data)} scanner training examples to {file_path}")

def write_scanner_yaml(data: List[CVEData], file_path: Path) -> None:
    if not data:
        logger.warning("No scanner training data to write (YAML)")
        return
    yaml_items: List[Dict[str, Any]] = []
    # Get all possible fields from models and data
    
    for item in data:
        yaml_item = _convert_cve_data_to_dict(item)
        # Convert multiline strings to literal strings for better YAML readability
        for field, value in yaml_item.items():
            if isinstance(value, str) and len(value.splitlines()) > 1:
                yaml_item[field] = LiteralString(value)
        yaml_items.append(yaml_item)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(
            yaml_items,
            f,
            Dumper=LiteralDumper,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )
    logger.info(f"Wrote {len(yaml_items)} scanner training examples to {file_path}")
