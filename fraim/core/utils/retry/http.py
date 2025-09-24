# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Utility functions for HTTP retry logic and extracting retry-after duration from LiteLLM RateLimitError"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, cast

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore


def parse_retry_header(exception: BaseException) -> timedelta | None:
    """
    Extracts a normalized retry-after duration from an exception with an HTTP response.

    Works with requests, httpx, and aiohttp response objects.

    Returns:
        timedelta until retry, or None if not available.
    """
    headers = _get_headers(exception)
    if headers is None:
        return None

    retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if not retry_after:
        return None

    # Case: integer seconds
    try:
        seconds = int(retry_after)
        return timedelta(seconds=seconds)
    except (ValueError, TypeError):
        pass

    # Case: HTTP-date (e.g. "Wed, 21 Oct 2015 07:28:00 GMT")
    try:
        dt = parsedate_to_datetime(str(retry_after))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        seconds = max(0, int((dt - datetime.now(UTC)).total_seconds()))
        return timedelta(seconds=seconds)
    except (ValueError, TypeError):
        pass

    return None


def should_retry_request(exception: BaseException) -> bool:
    """
    Determine if the request should be retried based on the exception type (for network errors) and
    HTTP status codes (for API errors).

    Retries on:
    - HTTP status codes: 408 (Request Timeout), 409 (Conflict), 429 (Too Many Requests), 500+ (Server Errors)
    - aiohttp connection/timeout errors
    - httpx.TransportError
    - requests connection/timeout errors
    """

    # Check for HTTP status codes (this covers all retriable LiteLLM exceptions)
    status_code = _get_status_code(exception)
    if status_code is not None and (status_code in (408, 409, 429) or status_code >= 500):
        return True

    # Check for aiohttp errors (if aiohttp is available)
    if aiohttp is not None:
        if isinstance(
            exception,
            (
                aiohttp.ClientConnectorError,
                aiohttp.ServerTimeoutError,
                aiohttp.ClientOSError,
                aiohttp.ClientPayloadError,
            ),
        ):
            return True

    # Check for httpx transport errors
    if httpx is not None:
        if isinstance(exception, httpx.TransportError):
            return True

    # Check for requests errors (if requests is available)
    if requests is not None:
        if isinstance(exception, (requests.ConnectionError, requests.Timeout)):
            return True

    return False


def _get_response(exception: BaseException) -> Any | None:
    """
    Get the response from an exception with an HTTP response

    Handles requests, httpx, and aiohttp exceptions.
    """

    # All HTTP requests exceptions will extend Exception
    if not isinstance(exception, Exception):
        return None

    return getattr(exception, "response", None)


def _get_headers(exception: BaseException) -> Mapping[str, str] | None:
    """
    Get the response headers from an exception with an HTTP response.

    Handles requests, httpx, and aiohttp exceptions.
    """

    response = _get_response(exception)
    if response is None:
        return None

    headers = getattr(response, "headers", None)
    if headers is None:
        return None

    return cast("Mapping[str, str]", headers)


def _get_status_code(exception: BaseException) -> int | None:
    """
    Get the status code from an exception with an HTTP response

    Handles requests, httpx, and aiohttp exceptions.
    """

    response = _get_response(exception)
    if response is None:
        return None

    return getattr(response, "status_code", None) or getattr(response, "status", None)
