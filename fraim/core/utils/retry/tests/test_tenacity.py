# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for tenacity retry utilities"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

# Import real httpx for testing
import httpx
import pytest
import tenacity
from tenacity import RetryCallState

from ..tenacity import WaitRetryAfter, with_retry


class MockHTTPStatusError(Exception):
    """Mock HTTPStatusError for testing that's compatible with httpx structure"""

    def __init__(self, message: str, response: Any) -> None:
        super().__init__(message)
        self.response = response


class TestWaitRetryAfter:
    """Test the WaitRetryAfter wait strategy"""

    def test_init(self) -> None:
        """Test WaitRetryAfter initialization"""
        fallback = tenacity.wait_fixed(2.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)
        assert wait_strategy.fallback is fallback

    def test_call_with_retry_after_seconds(self) -> None:
        """Test WaitRetryAfter with retry-after header in seconds"""
        fallback = tenacity.wait_fixed(2.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        # Mock an HTTP exception with retry-after header
        response = Mock()
        response.headers = {"retry-after": "30"}
        exc = MockHTTPStatusError("HTTP Error", response)
        exc.response = response

        # Mock retry state
        outcome = Mock()
        outcome.exception.return_value = exc
        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = outcome

        result = wait_strategy(retry_state)
        assert result == 30.0

    def test_call_with_retry_after_http_date(self) -> None:
        """Test WaitRetryAfter with retry-after header as HTTP date"""
        fallback = tenacity.wait_fixed(2.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        # Create a future date (30 seconds from now)
        future_time = datetime.now(UTC) + timedelta(seconds=30)
        http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        response = Mock()
        response.headers = {"retry-after": http_date}
        exc = MockHTTPStatusError("HTTP Error", response)
        exc.response = response

        outcome = Mock()
        outcome.exception.return_value = exc
        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = outcome

        result = wait_strategy(retry_state)
        # Should be approximately 30 seconds (allow some tolerance for test execution time)
        assert 25 <= result <= 35

    def test_call_with_malformed_retry_after(self) -> None:
        """Test WaitRetryAfter falls back when retry-after header is malformed"""
        fallback = tenacity.wait_fixed(5.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        response = Mock()
        response.headers = {"retry-after": "invalid"}
        exc = MockHTTPStatusError("HTTP Error", response)
        exc.response = response

        outcome = Mock()
        outcome.exception.return_value = exc
        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = outcome

        result = wait_strategy(retry_state)
        assert result == 5.0  # Should use fallback

    def test_call_without_retry_after_header(self) -> None:
        """Test WaitRetryAfter falls back when no retry-after header present"""
        fallback = tenacity.wait_fixed(3.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        response = Mock()
        response.headers = {}
        exc = MockHTTPStatusError("HTTP Error", response)
        exc.response = response

        outcome = Mock()
        outcome.exception.return_value = exc
        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = outcome

        result = wait_strategy(retry_state)
        assert result == 3.0  # Should use fallback

    def test_call_with_non_http_exception(self) -> None:
        """Test WaitRetryAfter falls back for non-HTTP exceptions"""
        fallback = tenacity.wait_fixed(4.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        exc = ValueError("Some error")
        outcome = Mock()
        outcome.exception.return_value = exc
        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = outcome

        result = wait_strategy(retry_state)
        assert result == 4.0  # Should use fallback

    def test_call_with_no_exception(self) -> None:
        """Test WaitRetryAfter falls back when no exception in outcome"""
        fallback = tenacity.wait_fixed(6.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        outcome = Mock()
        outcome.exception.return_value = None
        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = outcome

        result = wait_strategy(retry_state)
        assert result == 6.0  # Should use fallback

    def test_call_with_no_outcome(self) -> None:
        """Test WaitRetryAfter falls back when no outcome in retry state"""
        fallback = tenacity.wait_fixed(7.0)
        wait_strategy = WaitRetryAfter(fallback=fallback)

        retry_state = Mock(spec=RetryCallState)
        retry_state.outcome = None

        result = wait_strategy(retry_state)
        assert result == 7.0  # Should use fallback


class TestWithRetry:
    """Test the with_retry decorator"""

    def test_successful_function_call(self) -> None:
        """Test with_retry doesn't interfere with successful calls"""

        def successful_func(x: int, y: int) -> int:
            return x + y

        wrapped_func = with_retry(successful_func)
        result = wrapped_func(2, 3)
        assert result == 5

    def test_function_with_kwargs(self) -> None:
        """Test with_retry works with keyword arguments"""

        def func_with_kwargs(a: int, b: int = 10, c: int = 20) -> int:
            return a + b + c

        wrapped_func = with_retry(func_with_kwargs)
        result = wrapped_func(5, c=30)
        assert result == 45

    def test_retry_on_retriable_exception(self) -> None:
        """Test with_retry retries on retriable exceptions"""
        call_count = 0

        def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Network error")
            return "success"

        wrapped_func = with_retry(failing_func, max_retries=2, base_delay=0.01)  # Fast retry for testing
        result = wrapped_func()
        assert result == "success"
        assert call_count == 3  # Initial call + 2 retries

    def test_max_retries_exceeded(self) -> None:
        """Test with_retry gives up after max retries"""
        call_count = 0

        def always_failing_func() -> str:
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Network error")

        wrapped_func = with_retry(always_failing_func, max_retries=2, base_delay=0.01)
        with pytest.raises(httpx.ConnectError):
            wrapped_func()

        assert call_count == 3  # Initial call + 2 retries

    def test_non_retriable_exception_not_retried(self) -> None:
        """Test with_retry doesn't retry non-retriable exceptions"""
        call_count = 0

        def func_with_non_retriable_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retriable")

        wrapped_func = with_retry(func_with_non_retriable_error, max_retries=3, base_delay=0.01)
        with pytest.raises(ValueError):
            wrapped_func()

        assert call_count == 1  # Should not retry

    def test_custom_retry_predicate(self) -> None:
        """Test with_retry with custom retry predicate"""
        call_count = 0

        def custom_predicate(exc: BaseException) -> bool:
            return isinstance(exc, ValueError)

        def func_with_custom_predicate() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Custom retriable error")
            return "success"

        wrapped_func = with_retry(
            func_with_custom_predicate, max_retries=2, base_delay=0.01, retry_predicate=custom_predicate
        )
        result = wrapped_func()
        assert result == "success"
        assert call_count == 3

    def test_custom_retry_predicate_rejects(self) -> None:
        """Test custom retry predicate can reject retries"""
        call_count = 0

        def strict_predicate(exc: BaseException) -> bool:
            return False  # Never retry

        def func_with_strict_predicate() -> str:
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Network error")

        wrapped_func = with_retry(
            func_with_strict_predicate, max_retries=3, base_delay=0.01, retry_predicate=strict_predicate
        )
        with pytest.raises(httpx.ConnectError):
            wrapped_func()

        assert call_count == 1  # Should not retry

    def test_retry_configuration_parameters(self) -> None:
        """Test with_retry respects configuration parameters"""
        # This test verifies the decorator is created with correct parameters
        # We'll mock tenacity.retry to check the parameters
        with patch("fraim.core.utils.retry.tenacity.tenacity.retry") as mock_retry:
            mock_retry.return_value = lambda f: f  # Return function unchanged

            def test_func() -> str:
                return "test"

            with_retry(test_func, max_retries=10, base_delay=2.0, max_delay=120.0)

            # Verify tenacity.retry was called with correct parameters
            mock_retry.assert_called_once()
            call_kwargs = mock_retry.call_args[1]

            # Check stop condition
            assert hasattr(call_kwargs["stop"], "max_attempt_number")
            # max_retries=10 means 11 total attempts (initial + 10 retries)

            # Check wait strategy is WaitRetryAfter
            assert isinstance(call_kwargs["wait"], WaitRetryAfter)

            # Check reraise is True
            assert call_kwargs["reraise"] is True

    def test_function_preserves_metadata(self) -> None:
        """Test with_retry preserves function metadata"""

        def original_func() -> str:
            """Original docstring"""
            return "original"

        wrapped_func = with_retry(original_func)

        assert wrapped_func.__name__ == "original_func"
        assert wrapped_func.__doc__ == "Original docstring"

    def test_as_wrapper_function(self) -> None:
        """Test using with_retry as a wrapper function (not decorator)"""

        def original_func(x: int) -> int:
            return x * 2

        wrapped_func = with_retry(original_func, max_retries=2, base_delay=0.01)

        result = wrapped_func(5)
        assert result == 10

    def test_wait_strategy_integration(self) -> None:
        """Test that WaitRetryAfter is properly integrated with retry logic"""
        call_count = 0
        retry_delays = []

        def mock_sleep(delay: float) -> None:
            retry_delays.append(delay)

        def func_with_retry_after() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Create a 429 response with retry-after header
                response = Mock()
                response.status_code = 429
                response.headers = {"retry-after": "1"}
                exc = MockHTTPStatusError("HTTP Error", response)
                exc.response = response
                raise exc
            return "success"

        wrapped_func = with_retry(func_with_retry_after, max_retries=2, base_delay=0.5, max_delay=2.0)
        with patch("time.sleep", side_effect=mock_sleep):
            result = wrapped_func()

        assert result == "success"
        assert call_count == 3
        # Should have used retry-after delay of 1 second for retries
        assert len(retry_delays) == 2
        for delay in retry_delays:
            assert delay == 1.0  # From retry-after header

    def test_exponential_backoff_fallback(self) -> None:
        """Test exponential backoff is used when no retry-after header"""
        call_count = 0
        retry_delays = []

        def mock_sleep(delay: float) -> None:
            retry_delays.append(delay)

        def func_without_retry_after() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Network error without retry-after header
                raise httpx.ConnectError("Network error")
            return "success"

        wrapped_func = with_retry(func_without_retry_after, max_retries=2, base_delay=1.0, max_delay=10.0)
        with patch("time.sleep", side_effect=mock_sleep):
            result = wrapped_func()

        assert result == "success"
        assert call_count == 3
        # Should have used exponential backoff
        assert len(retry_delays) == 2
        # First retry: base_delay * 2^0 = 1.0
        # Second retry: base_delay * 2^1 = 2.0
        assert retry_delays[0] == 1.0
        assert retry_delays[1] == 2.0
