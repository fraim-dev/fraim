# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path


class BufferedFile:
    def __init__(self, path: str, body: str):
        self.path = path
        self.body = body
