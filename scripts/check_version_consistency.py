#!/usr/bin/env python3
"""
CI script to verify version consistency between pyproject.toml and __init__.py
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent


def get_pyproject_version() -> str:
    """Extract version from pyproject.toml"""
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    with open(pyproject_path) as f:
        content = f.read()

    # Look for version = "x.y.z" pattern
    version_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not version_match:
        raise ValueError("Could not find version in pyproject.toml")

    return version_match.group(1)


def get_init_version() -> str:
    """Extract version from fraim/__init__.py"""
    init_path = project_root / "fraim" / "__init__.py"

    if not init_path.exists():
        raise FileNotFoundError(f"__init__.py not found at {init_path}")

    with open(init_path) as f:
        content = f.read()

    # Look for __version__ = "x.y.z" pattern
    version_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not version_match:
        raise ValueError("Could not find __version__ in __init__.py")

    return version_match.group(1)


def main() -> int:
    """Main function to check version consistency"""
    try:
        pyproject_version = get_pyproject_version()
        init_version = get_init_version()

        print(f"pyproject.toml version: {pyproject_version}")
        print(f"__init__.py version:   {init_version}")

        if pyproject_version == init_version:
            print("✅ Version consistency check PASSED")
            return 0
        print("❌ Version consistency check FAILED")
        print(f"Versions do not match: pyproject.toml='{pyproject_version}' vs __init__.py='{init_version}'")
        return 1

    except Exception as e:
        print(f"❌ Error during version check: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
