# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for HTTP retry utility functions"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest

from fraim.core.utils.retry.http import parse_retry_header, should_retry_request


class MockException(Exception):
    """Mock exception class for testing"""

    def __init__(self, headers: Mapping[str, str] | None = None):
        super().__init__()
        if headers is not None:
            # Create a mock response object with headers
            self.response = Mock()
            self.response.headers = headers
        else:
            self.response = None  # type: ignore


class TestParseRetryHeader:
    """Test cases for parse_retry_header function"""

    def test_integer_seconds_retry_after_lowercase(self) -> None:
        """Test parsing integer seconds from lowercase retry-after header"""
        headers = {"retry-after": "120"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=120)

    def test_integer_seconds_retry_after_capitalized(self) -> None:
        """Test parsing integer seconds from capitalized Retry-After header"""
        headers = {"Retry-After": "60"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=60)

    def test_integer_seconds_zero(self) -> None:
        """Test parsing zero seconds"""
        headers = {"retry-after": "0"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=0)

    def test_integer_seconds_large_value(self) -> None:
        """Test parsing large integer seconds value"""
        headers = {"retry-after": "3600"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=3600)

    def test_http_date_format(self) -> None:
        """Test parsing HTTP-date format"""
        # Create a future date (1 hour from now)
        future_time = datetime.now(UTC) + timedelta(hours=1)
        http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        headers = {"retry-after": http_date}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        # Should be approximately 1 hour (allowing for small timing differences)
        assert result is not None
        assert 3590 <= result.total_seconds() <= 3610  # ~1 hour ± 10 seconds

    def test_http_date_format_past_date(self) -> None:
        """Test parsing HTTP-date format with past date (should return 0)"""
        # Create a past date (1 hour ago)
        past_time = datetime.now(UTC) - timedelta(hours=1)
        http_date = past_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        headers = {"retry-after": http_date}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=0)

    def test_http_date_format_capitalized_header(self) -> None:
        """Test parsing HTTP-date format with capitalized header"""
        future_time = datetime.now(UTC) + timedelta(minutes=30)
        http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S GMT")

        headers = {"Retry-After": http_date}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is not None
        assert 1790 <= result.total_seconds() <= 1810  # ~30 minutes ± 10 seconds

    def test_no_headers(self) -> None:
        """Test exception with no headers"""
        exception = MockException(headers=None)

        result = parse_retry_header(exception)

        assert result is None

    def test_empty_headers(self) -> None:
        """Test exception with empty headers"""
        headers: dict[str, str] = {}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_no_retry_after_header(self) -> None:
        """Test headers without retry-after"""
        headers = {"content-type": "application/json", "x-custom": "value"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_empty_retry_after_header(self) -> None:
        """Test empty retry-after header value"""
        headers = {"retry-after": ""}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_none_retry_after_header(self) -> None:
        """Test None retry-after header value"""
        headers: dict[str, Any] = {"retry-after": None}
        exception = MockException(headers)  # type: ignore

        result = parse_retry_header(exception)

        assert result is None

    def test_invalid_integer_format(self) -> None:
        """Test invalid integer format in retry-after header"""
        headers = {"retry-after": "not-a-number"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_invalid_date_format(self) -> None:
        """Test invalid date format in retry-after header"""
        headers = {"retry-after": "invalid-date-format"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_float_seconds_string(self) -> None:
        """Test float seconds as string (should fail integer parsing but not date parsing)"""
        headers = {"retry-after": "120.5"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_negative_integer_seconds(self) -> None:
        """Test negative integer seconds"""
        headers = {"retry-after": "-60"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=-60)

    def test_whitespace_in_header_value(self) -> None:
        """Test retry-after header with whitespace"""
        headers = {"retry-after": "  120  "}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=120)

    def test_both_header_cases_present_lowercase_priority(self) -> None:
        """Test when both retry-after and Retry-After are present (lowercase should take priority)"""
        headers = {"retry-after": "60", "Retry-After": "120"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=60)

    def test_only_capitalized_header_present(self) -> None:
        """Test when only Retry-After (capitalized) is present"""
        headers = {"Retry-After": "90"}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=90)

    def test_exception_without_response_attribute(self) -> None:
        """Test exception that doesn't have a response attribute"""
        exception = Exception("No response attribute")

        result = parse_retry_header(exception)

        assert result is None

    def test_response_without_headers_attribute(self) -> None:
        """Test exception with response that doesn't have headers attribute"""
        exception = MockException()
        exception.response = Mock()
        del exception.response.headers  # Remove headers attribute

        result = parse_retry_header(exception)

        assert result is None

    @pytest.mark.parametrize(
        "seconds_str,expected_seconds",
        [
            ("1", 1),
            ("30", 30),
            ("300", 300),
            ("3600", 3600),
            ("86400", 86400),  # 1 day
        ],
    )
    def test_various_integer_values(self, seconds_str: str, expected_seconds: int) -> None:
        """Test various valid integer values"""
        headers = {"retry-after": seconds_str}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result == timedelta(seconds=expected_seconds)

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "abc",
            "12.34",
            "1e5",
            "infinity",
            "NaN",
            "true",
            "false",
            "null",
            "{}",
            "[]",
        ],
    )
    def test_various_invalid_values(self, invalid_value: str) -> None:
        """Test various invalid header values"""
        headers = {"retry-after": invalid_value}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        assert result is None

    def test_http_date_without_timezone_assumes_utc(self) -> None:
        """Test HTTP-date without explicit timezone (should assume UTC)"""
        # Create a future time without timezone info
        future_time = datetime.now(UTC) + timedelta(hours=2)
        # Format without timezone (parsedate_to_datetime will return naive datetime)
        http_date = future_time.strftime("%a, %d %b %Y %H:%M:%S")

        headers = {"retry-after": http_date}
        exception = MockException(headers)

        result = parse_retry_header(exception)

        # Should be approximately 2 hours
        assert result is not None
        assert 7190 <= result.total_seconds() <= 7210  # ~2 hours ± 10 seconds

    def test_case_insensitive_header_lookup(self) -> None:
        """Test that header lookup handles case variations correctly"""
        # The function should check lowercase first, then capitalized
        headers = {"RETRY-AFTER": "180"}  # All caps - should not be found
        exception = MockException(headers)

        result = parse_retry_header(exception)

        # Should return None because the function only checks "retry-after" and "Retry-After"
        assert result is None


class MockExceptionWithStatus(Exception):
    """Mock exception class with status code for testing should_retry_request"""

    def __init__(self, status_code: int | None = None, status: int | None = None):
        super().__init__()
        self.response = Mock()
        if status_code is not None:
            self.response.status_code = status_code
            # Ensure status returns None when not set
            self.response.status = None
        elif status is not None:
            self.response.status = status
            # Ensure status_code returns None when not set
            self.response.status_code = None
        else:
            # No status code attributes - make sure both return None
            self.response.status_code = None
            self.response.status = None


class TestShouldRetryRequest:
    """Test cases for should_retry_request function"""

    def test_no_request_attribute(self) -> None:
        """Test exception without request attribute"""
        exception = Exception("No request")
        result = should_retry_request(exception)
        assert result is False

    def test_aiohttp_client_connector_error(self) -> None:
        """Test aiohttp ClientConnectorError is retriable"""
        try:
            import aiohttp

            exception = aiohttp.ClientConnectorError(connection_key=Mock(), os_error=OSError())
            result = should_retry_request(exception)
            assert result is True
        except ImportError:
            pytest.skip("aiohttp not available")

    def test_aiohttp_server_timeout_error(self) -> None:
        """Test aiohttp ServerTimeoutError is retriable"""
        try:
            import aiohttp

            exception = aiohttp.ServerTimeoutError()
            result = should_retry_request(exception)
            assert result is True
        except ImportError:
            pytest.skip("aiohttp not available")

    def test_aiohttp_client_os_error(self) -> None:
        """Test aiohttp ClientOSError is retriable"""
        try:
            import aiohttp

            exception = aiohttp.ClientOSError()
            result = should_retry_request(exception)
            assert result is True
        except ImportError:
            pytest.skip("aiohttp not available")

    def test_aiohttp_client_payload_error(self) -> None:
        """Test aiohttp ClientPayloadError is retriable"""
        try:
            import aiohttp

            exception = aiohttp.ClientPayloadError()
            result = should_retry_request(exception)
            assert result is True
        except ImportError:
            pytest.skip("aiohttp not available")

    def test_aiohttp_non_retriable_error(self) -> None:
        """Test that non-retriable aiohttp errors return False"""
        try:
            import aiohttp

            exception = aiohttp.InvalidURL("invalid")
            result = should_retry_request(exception)
            assert result is False
        except ImportError:
            pytest.skip("aiohttp not available")

    def test_httpx_transport_error(self) -> None:
        """Test httpx TransportError is retriable"""
        try:
            import httpx

            # Create a simple object without status attributes
            class MockRequest:
                pass

            mock_request = MockRequest()
            exception = httpx.TransportError("Transport error")
            exception._request = mock_request  # type: ignore[assignment] # Set the internal request
            result = should_retry_request(exception)
            assert result is True
        except ImportError:
            pytest.skip("httpx not available")

    def test_httpx_non_retriable_error(self) -> None:
        """Test that non-retriable httpx errors return False"""
        try:
            import httpx

            exception = httpx.InvalidURL("invalid")
            result = should_retry_request(exception)
            assert result is False
        except ImportError:
            pytest.skip("httpx not available")

    def test_generic_exception_not_retriable(self) -> None:
        """Test that generic exceptions are not retriable"""
        exception = ValueError("Some error")
        result = should_retry_request(exception)
        assert result is False

    def test_base_exception_not_retriable(self) -> None:
        """Test that BaseException (non-Exception) is not retriable"""
        exception = KeyboardInterrupt()
        result = should_retry_request(exception)
        assert result is False

    @pytest.mark.parametrize(
        "status_code,expected",
        [
            (408, True),  # Request Timeout
            (409, True),  # Conflict
            (429, True),  # Too Many Requests
            (500, True),  # Internal Server Error
            (501, True),  # Not Implemented
            (502, True),  # Bad Gateway
            (503, True),  # Service Unavailable
            (504, True),  # Gateway Timeout
            (505, True),  # HTTP Version Not Supported
            (507, True),  # Insufficient Storage
            (508, True),  # Loop Detected
            (510, True),  # Not Extended
            (511, True),  # Network Authentication Required
            (599, True),  # Network Connect Timeout Error (unofficial)
            (200, False),  # OK
            (201, False),  # Created
            (400, False),  # Bad Request
            (401, False),  # Unauthorized
            (403, False),  # Forbidden
            (404, False),  # Not Found
            (405, False),  # Method Not Allowed
            (406, False),  # Not Acceptable
            (407, False),  # Proxy Authentication Required
            (410, False),  # Gone
            (411, False),  # Length Required
            (412, False),  # Precondition Failed
            (413, False),  # Payload Too Large
            (414, False),  # URI Too Long
            (415, False),  # Unsupported Media Type
            (416, False),  # Range Not Satisfiable
            (417, False),  # Expectation Failed
            (418, False),  # I'm a teapot
            (421, False),  # Misdirected Request
            (422, False),  # Unprocessable Entity
            (423, False),  # Locked
            (424, False),  # Failed Dependency
            (425, False),  # Too Early
            (426, False),  # Upgrade Required
            (428, False),  # Precondition Required
            (431, False),  # Request Header Fields Too Large
            (451, False),  # Unavailable For Legal Reasons
        ],
    )
    def test_status_code_retriability(self, status_code: int, expected: bool) -> None:
        """Test comprehensive status code retriability mapping"""
        exception = MockExceptionWithStatus(status_code=status_code)
        result = should_retry_request(exception)
        assert result == expected, f"Status code {status_code} retriability should be {expected}"

    def test_status_attribute_instead_of_status_code(self) -> None:
        """Test that status attribute works when status_code is not available"""
        exception = MockExceptionWithStatus(status=429)
        result = should_retry_request(exception)
        assert result is True

    def test_no_status_code_or_status(self) -> None:
        """Test exception with no status code or status attribute"""
        exception = MockExceptionWithStatus()
        result = should_retry_request(exception)
        assert result is False
