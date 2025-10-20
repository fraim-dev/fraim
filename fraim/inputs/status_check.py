# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from fraim.core.contextuals.status_check import GithubStatusCheck
from fraim.inputs.input import Input

logger = logging.getLogger(__name__)


class StatusCheckInput(Input):
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> "StatusCheckInput":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return None

    def root_path(self) -> str:
        return str(self.path)

    def __iter__(self) -> Iterator[GithubStatusCheck]:
        if not self.path.is_file():
            return
        logger.info(f"Reading file: {self.path}")
        yield GithubStatusCheck(self.path.read_text(encoding="utf-8"))


# {
#     "action": "completed",
#     "check_run": {
#         "id": 1286253418,
#         "name": "build (18.x)",
#         "head_sha": "a4a39d2c46f2729a21b339245a46f7c025c8d0a9",
#         "status": "completed",
#         "conclusion": "success",
#         "started_at": "2025-10-16T16:20:12Z",
#         "completed_at": "2025-10-16T16:21:42Z",
#         "output": {
#             "title": "Build successful!",
#             "summary": "All build steps passed.",
#             "text": "Detailed build logs can be found here...",
#             "annotations_count": 0,
#             "annotations_url": "..."
#         },
#         "check_suite": {
#             "id": 1185332261
#         },
#         "app": {
#             "id": 1,
#             "name": "GitHub Actions"
#         }
#     },
#     "repository": {
#         "full_name": "your-org/your-repo"
#     }
# }
