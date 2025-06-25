# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Simple Python file for testing TreeSitter tools.
Contains basic functions, classes, and variables.
Do not change this file without updating the tests.
"""

def hello_world():
    """Simple hello world function"""
    return "Hello, World!"

def add_numbers(a, b):
    """Add two numbers together"""
    return a + b

def greet_person(name, greeting="Hello"):
    """Greet a person with optional greeting"""
    return f"{greeting}, {name}!"

class Calculator:
    """A simple calculator class"""

    def __init__(self, initial_value=0):
        self.value = initial_value

    def add(self, num):
        """Add a number to the current value"""
        self.value += num
        return self.value

    def multiply(self, num):
        """Multiply the current value by a number"""
        self.value *= num
        return self.value

    def reset(self):
        """Reset the calculator to zero"""
        self.value = 0

class Person:
    """A person class for testing"""

    def __init__(self, name, age):
        self.name = name
        self.age = age

    def get_info(self):
        return f"{self.name} is {self.age} years old"

# Global variables for testing
CONSTANT_VALUE = 42
PI = 3.14159
message = "This is a test message"
numbers = [1, 2, 3, 4, 5]
person_data = {"name": "Alice", "age": 30}

# Function calls for testing symbol usage
result = add_numbers(10, 20)
calc = Calculator(100)
calc.add(50)

if __name__ == "__main__":
    print(hello_world())
    print(greet_person("World"))
    person = Person("Bob", 25)
    print(person.get_info())
