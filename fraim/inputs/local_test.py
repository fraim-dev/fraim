import logging
from pathlib import Path

import pytest

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.inputs.local import Local

TEST_DATA_DIR = Path(__name__).parent / "test_data"


class MockConfig(Config):
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.project_path = TEST_DATA_DIR


@pytest.fixture
def local() -> Local:
    return Local(
        config=MockConfig(),
        root_path=str(TEST_DATA_DIR),
        globs=["*.py"],
        exclude_globs=["*.min.js", "*.min.css"],
    )


@pytest.fixture
def project_files(local: Local) -> list[CodeChunk]:
    result = list(local)
    assert len(result) > 0
    assert isinstance(result[0], CodeChunk)
    return result


@pytest.fixture
def project_paths(project_files: list[CodeChunk]) -> list[str]:
    result = [p.file_path for p in project_files]
    assert len(result) > 0
    assert isinstance(result[0], str)
    return result


def test_local_globs(project_paths: list[str]) -> None:
    assert "included.py" in project_paths


def test_local_exclude_globs(project_paths: list[str]) -> None:
    assert "excluded.min.js" not in project_paths
