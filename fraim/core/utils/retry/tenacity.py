# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Utility functions for Tenacity to retry HTTP requests"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import ParamSpec, TypeVar

import tenacity
from tenacity import RetryCallState, after_log, before_log, before_sleep_log
from tenacity.wait import wait_base

from .http import parse_retry_header, should_retry_request

logger = logging.getLogger(__name__)


class WaitRetryAfter(wait_base):
    """
    A tenacity wait strategy that respects HTTP Retry-After headers for intelligent backoff.

    Parses both integer seconds and HTTP-date formats from the retry-after header per RFC 7231.

    Tenacity wait_base classes define how long to wait between retry attempts. Common strategies
    include fixed delays, exponential backoff, or random jitter. This custom wait strategy
    implements server-directed backoff by parsing Retry-After headers from HTTP responses.

    This should be used when making HTTP requests to APIs that may return rate limiting or
    temporary unavailability responses (HTTP 429, 503, etc.) with Retry-After headers.
    By respecting these headers, we avoid overwhelming the server and reduce unnecessary
    retry attempts that would likely fail again immediately.

    The fallback parameter provides the wait strategy to use when the exception server-directed
    backoff is not available:
    - no response headers
    - retry-after is missing or malformed

    Exponential backoff is a good default fallback strategy.
    """

    def __init__(self, fallback: wait_base) -> None:
        self.fallback = fallback

    def __call__(self, retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None

        if exc is not None:
            retry_delay = parse_retry_header(exc)
            if retry_delay is not None:
                return float(retry_delay.total_seconds())

        # Fallback to normal policy
        return float(self.fallback(retry_state))


P = ParamSpec("P")
T = TypeVar("T")


def with_retry(
    func: Callable[P, T],
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_predicate: Callable[[BaseException], bool] = should_retry_request,
) -> Callable[P, T]:
    """
    Wraps a function to be retriable, respecting HTTP Retry-After headers with exponential backoff fallback.

    Args:
        func: The function to make retriable
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay in seconds to cap exponential backoff (default: 60.0)
        retry_predicate: Function that determines if an exception should trigger a retry.
                        Defaults to `should_retry_request` which retries on network errors and retriable API errors.

    Returns:
        A wrapped function that will retry on failure with intelligent backoff

    Examples:
        >>> # As a decorator with default retry logic
        >>> @with_retry(max_retries=3, base_delay=2.0)
        ... def api_call():
        ...     return requests.get("https://api.example.com/data")

        >>> # Wrap the function and call it directly
        >>> result = with_retry(
        ...     make_request,
        ...     max_retries=3,
        ...     base_delay=2.0
        ... )("https://api.example.com/data", timeout=60)
    """
    wait_strategy = WaitRetryAfter(fallback=tenacity.wait_exponential(multiplier=base_delay, max=max_delay))

    # Use the provided retry predicate
    retry_condition = tenacity.retry_if_exception(retry_predicate)

    # Create the retry decorator
    retry_decorator = tenacity.retry(
        retry=retry_condition,
        stop=tenacity.stop_after_attempt(max_retries + 1),  # tenacity counts initial attempt
        wait=wait_strategy,
        reraise=True,
        before=before_log(logger, logging.DEBUG),
        before_sleep=before_sleep_log(logger, logging.INFO),
        after=after_log(logger, logging.DEBUG),
    )

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return retry_decorator(func)(*args, **kwargs)

    return wrapper
