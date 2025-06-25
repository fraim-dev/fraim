# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Complex Python file for testing advanced TreeSitter patterns.
Contains decorators, async functions, context managers, and more.
Do not change this file without updating the tests.
"""

import asyncio
import functools
from typing import List, Dict, Optional, Union
from contextlib import contextmanager
from dataclasses import dataclass

# Decorator definitions

def timing_decorator(func):
    """A simple timing decorator"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import time

        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result

    return wrapper


def retry(max_attempts=3):
    """Retry decorator with configurable attempts"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    print(f"Attempt {attempt + 1} failed: {e}")
            return None

        return wrapper

    return decorator


# Dataclass for testing

@dataclass
class Employee:
    name: str
    age: int
    department: str
    salary: Optional[float] = None

    def get_annual_salary(self) -> float:
        return self.salary * 12 if self.salary else 0.0


# Async functions

async def fetch_data(url: str) -> Dict:
    """Simulate fetching data from an API"""
    await asyncio.sleep(0.1)  # Simulate network delay
    return {"url": url, "status": "success", "data": [1, 2, 3]}


async def process_multiple_urls(urls: List[str]) -> List[Dict]:
    """Process multiple URLs concurrently"""
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results


# Context manager

@contextmanager
def managed_resource(resource_name: str):
    """A context manager for resource management"""
    print(f"Acquiring resource: {resource_name}")
    try:
        yield f"resource_{resource_name}"
    finally:
        print(f"Releasing resource: {resource_name}")


# Class with advanced features

class DataProcessor:
    """Advanced data processor with various patterns"""

    def __init__(self, config: Dict):
        self._config = config
        self._cache = {}

    @property
    def config(self) -> Dict:
        return self._config.copy()

    @config.setter
    def config(self, value: Dict):
        self._config = value
        self._cache.clear()

    @timing_decorator
    def process_data(self, data: List[Union[int, str]]) -> List:
        """Process data with timing"""
        return [self._transform_item(item) for item in data]

    def _transform_item(self, item: Union[int, str]) -> str:
        """Transform a single item"""
        if isinstance(item, int):
            return f"number_{item}"
        return f"string_{item}"

    @staticmethod
    def validate_config(config: Dict) -> bool:
        """Validate configuration dictionary"""
        required_keys = ["processing_mode", "output_format"]
        return all(key in config for key in required_keys)

    @classmethod
    def create_default(cls) -> "DataProcessor":
        """Create processor with default configuration"""
        default_config = {"processing_mode": "batch", "output_format": "json", "max_workers": 4}
        return cls(default_config)


# Generator function

def fibonacci_generator(n: int):
    """Generate fibonacci sequence up to n numbers"""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# Lambda and higher-order functions
transform_functions = {
    "upper": lambda x: x.upper() if isinstance(x, str) else str(x).upper(),
    "double": lambda x: x * 2 if isinstance(x, (int, float)) else len(str(x)) * 2,
    "reverse": lambda x: x[::-1] if isinstance(x, str) else str(x)[::-1],
}

def apply_transformation(data: List, transform_name: str) -> List:
    """Apply a transformation function to data"""
    transform_func = transform_functions.get(transform_name)
    if not transform_func:
        raise ValueError(f"Unknown transformation: {transform_name}")
    return [transform_func(item) for item in data]


# Exception handling patterns

class CustomError(Exception):
    """Custom exception for testing"""

    def __init__(self, message: str, error_code: int = None):
        super().__init__(message)
        self.error_code = error_code


@retry(max_attempts=2)
def risky_operation(should_fail: bool = False):
    """Operation that might fail"""
    if should_fail:
        raise CustomError("Operation failed intentionally", error_code=500)
    return "Success!"

# Usage examples
if __name__ == "__main__":
    # Test dataclass
    emp = Employee("John Doe", 30, "Engineering", 5000.0)
    print(f"Annual salary: {emp.get_annual_salary()}")

    # Test processor
    processor = DataProcessor.create_default()
    result = processor.process_data([1, "hello", 42, "world"])
    print(f"Processed: {result}")

    # Test generator
    fib_numbers = list(fibonacci_generator(10))
    print(f"Fibonacci: {fib_numbers}")

    # Test transformation
    data = ["hello", "world", 123]
    transformed = apply_transformation(data, "upper")
    print(f"Transformed: {transformed}")

    # Test context manager
    with managed_resource("database") as resource:
        print(f"Using {resource}")

    # Test async (would need asyncio.run in real usage)
    # asyncio.run(fetch_data("https://api.example.com/data"))
