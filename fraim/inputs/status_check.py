# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
import os
from collections.abc import Iterator
from typing import Self

from fraim.core.contextuals.status_check import GithubStatusCheck
from fraim.inputs.input import Input

logger = logging.getLogger(__name__)


class StatusCheck(Input):
    # TODO: Can this be a buffered file, to avoid the read here?
    def __init__(self, path: str):
        self.path = path

    def root_path(self) -> str:
        return str(self.path)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        pass

    def __iter__(self) -> Iterator[GithubStatusCheck]:
        if not os.path.isfile(self.path):
            logger.error(f"Path is not file: {self.path}")
            return

        logger.info(f"Reading file: {self.path}")
        with open(self.path) as f:
            yield GithubStatusCheck(f.read())


# See: https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28
#
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
