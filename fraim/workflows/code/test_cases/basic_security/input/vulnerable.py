#!/usr/bin/env python3
"""
Simple Python code for testing security analysis.
"""

def process_user_input(user_input):
    # result = subprocess.run(f"echo {user_input}", shell=True, capture_output=True)
    return f"Processed: {user_input}"

if __name__ == "__main__":
    user_data = "test input"
    output = process_user_input(user_data)
    print(output) 