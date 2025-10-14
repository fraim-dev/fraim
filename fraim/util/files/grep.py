# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Literal

from .basepath import BasePathFS


async def grep(
    fs: BasePathFS,
    pattern: str,
    path: str | Path = ".",
    *,
    timeout: int | None = 30,
    head_limit: int | None = None,
    glob: str | None = None,
    output_mode: Literal["content", "files_with_matches", "count"] = "content",
    file_type: str | None = None,
    context_before: int | None = None,  # -B
    context_after: int | None = None,  # -A
    context_around: int | None = None,  # -C
    case_insensitive: bool = False,  # -i
    multiline: bool = False,
) -> str:
    """Run ripgrep confined to the file system root.

    Args:
        fs: BasePathFS instance to use for path resolution
        pattern: The regular expression pattern to search for (maps to `rg --regexp PATTERN`)
        path: File or directory to search in (defaults to current dir)
        head_limit: Limit output to first N lines/entries (maps to `| head -N`)
        glob: Glob pattern to filter files (e.g. `*.js`, `*.{ts,tsx}`) (maps to `rg --glob GLOB`)
        output_mode: Output format - `content` outputs matches with `-A/-B/-C context` and -n , "files_with_matches" shows file paths, or "count"
        file_type: File type to search (e.g. "js", "py", "rust") (maps to `rg --type TYPE`)
        context_before: Number of lines to show before each match (maps to `rg -B N`)
        context_after: Number of lines to show after each match (maps to `rg -A N`)
        context_around: Number of lines to show before and after each match (maps to `rg -C N`)
        case_insensitive: Enable case insensitive search (maps to `rg -i`)
        multiline: Enable multiline mode where . matches newlines (maps to `rg -U --multiline-dotall`)
        timeout: Timeout in seconds
        ripgrep_bin: Path to ripgrep binary

    Returns:
        Ripgrep output as string. Empty string if no matches found.

    Raises:
        ValueError: If incompatible argument combinations are provided (e.g., context options with non-content output modes)
        CalledProcessError: On ripgrep errors (exit code > 1)
        FileNotFoundError: If target path doesn't exist
        PermissionError: If path is outside sandbox
    """

    # Ensure the target path exists and is underneath the base path
    target_abs = fs.resolve(path, must_exist=True)
    target_rel = target_abs.relative_to(fs.root)

    args = _build_cmd(
        ripgrep_bin="rg",  # Do not allow this to be controlled by an attacker.
        pattern=pattern,
        target_rel=target_rel,
        output_mode=output_mode,
        file_type=file_type,
        glob=glob,
        context_before=context_before,
        context_after=context_after,
        context_around=context_around,
        case_insensitive=case_insensitive,
        multiline=multiline,
    )

    # Keep the environment minimal - only PATH to find rg
    env = {"PATH": os.environ.get("PATH", "")}

    # Execute subprocess with optional timeout (None = wait forever)
    proc = await asyncio.wait_for(
        asyncio.create_subprocess_exec(
            *args,
            cwd=str(fs.root),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        ),
        timeout=timeout,
    )
    assert proc.stdout is not None  # We used PIPE, so this is guaranteed
    assert proc.stderr is not None  # We used PIPE, so this is guaranteed

    # Consume stdout and stderr concurrently
    head_result = _head(proc.stdout, head_limit)
    stderr = proc.stderr.read()

    # Run process until we have the results
    stdout, complete = await head_result
    results = stdout.decode("utf-8", errors="replace")

    # Attempt to explicitly terminate if _head returned early due to head_limit
    if not complete:
        try:
            proc.terminate()
        except ProcessLookupError:
            # Process already finished, that's fine
            pass

    # Consume the complete error stream
    errors = (await stderr).decode("utf-8", errors="replace")

    # Get the return code
    await proc.wait()
    returncode = proc.returncode or 0

    # ripgrep returns 0 if matches found, 1 if none, >1 on error
    if returncode == 0:
        return results
    if returncode == 1:
        return ""  # no matches
    if returncode == -15 and not complete:
        return results  # we intentionally terminated early due to head_limit
    # On actual errors, surface stderr
    raise ValueError(f"ripgrep failed with return code {returncode}: {errors}")


def _build_cmd(
    ripgrep_bin: str,
    pattern: str,
    target_rel: Path,
    output_mode: Literal["content", "files_with_matches", "count"],
    file_type: str | None,
    glob: str | None,
    context_before: int | None,
    context_after: int | None,
    context_around: int | None,
    case_insensitive: bool,
    multiline: bool,
) -> list[str]:
    """Build the ripgrep command.

    Returns:
        List of command arguments for ripgrep
    """
    args = [ripgrep_bin, "--no-follow", "--color", "never"]

    # Output mode options
    if output_mode == "files_with_matches":
        args.append("--files-with-matches")
    elif output_mode == "count":
        args.append("--count")
    else:  # content mode (default)
        args.append("--line-number")

    # Context options (only for content mode)
    if output_mode == "content":
        if context_around is not None:
            args.extend(["-C", str(context_around)])
        else:
            if context_before is not None:
                args.extend(["-B", str(context_before)])
            if context_after is not None:
                args.extend(["-A", str(context_after)])
    # Context options are not supported for non-content modes
    elif context_before is not None or context_after is not None or context_around is not None:
        raise ValueError(
            f"Context options (-B/-A/-C) are only supported with output_mode='content', "
            f"but got output_mode='{output_mode}'. "
            f"Remove context options or use output_mode='content'."
        )

    # Case sensitivity
    if case_insensitive:
        args.append("-i")

    # Multiline mode
    if multiline:
        args.extend(["-U", "--multiline-dotall"])

    # File type filter
    if file_type:
        args.extend(["--type", file_type])

    # Glob pattern
    if glob:
        args.extend(["--glob", glob])

    # Pattern
    args.extend(["--regexp", pattern])

    # Add target path
    args.extend([str(target_rel)])

    return args


async def _head(stream: asyncio.StreamReader, count: int | None) -> tuple[bytes, bool]:
    """Return the first N lines of the stream.

    Args:
        stream: The asyncio StreamReader to read from
        count: Maximum number of lines to keep (None means no limit)

    Returns:
        First N lines of output and a boolean indicating if the stream was read completely
    """
    if count is None or count <= 0:
        # No limit, read everything
        return await stream.read(), True

    complete = False
    lines = []
    line_count = 0

    while line_count < count:
        line_bytes = await stream.readline()
        if not line_bytes:  # EOF
            complete = True
            break

        lines.append(line_bytes)  # line already includes \n or \r\n
        line_count += 1

    return b"".join(lines), complete
