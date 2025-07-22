#!/usr/bin/env python3
"""
Test script for terraform variable resolution functionality.

This script creates a test terraform configuration and verifies that the
TerraformVariableValueResolver can properly resolve variable values through
the complete chain from usage to final value.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from terraform_tools import TerraformVariableValueResolver


async def test_variable_resolution():
    """Test the variable resolution functionality with a realistic scenario."""
    
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create main.tf with variable usage
        main_tf = temp_path / "main.tf"
        main_tf.write_text("""
resource "aws_s3_bucket" "example" {
  bucket = "$${var.bucket_name}-$${var.environment}-$${random_string.bucket_suffix.result}"
  
  public_access_block {
    block_public_acls = var.enable_public_access
  }
}

resource "random_string" "bucket_suffix" {
  length = 8
  special = false
  upper = false
}
""")
        
        # Create variables.tf with variable definitions
        variables_tf = temp_path / "variables.tf"
        variables_tf.write_text("""
variable "bucket_name" {
  type        = string
  description = "Base name for the S3 bucket"
  default     = "default-bucket"
}

variable "environment" {
  type        = string
  description = "Environment name"
  default     = "dev"
}

variable "enable_public_access" {
  type        = bool
  description = "Whether to enable public access"
  default     = false
}
""")
        
        # Create terraform.tfvars with variable assignments
        tfvars = temp_path / "terraform.tfvars"
        tfvars.write_text("""
bucket_name = "company"
environment = "prod"
enable_public_access = true
""")
        
        # Test the resolver
        resolver = TerraformVariableValueResolver()
        
        print("Testing variable resolution...")
        print(f"Test directory: {temp_dir}")
        print()
        
        # Test 1: Resolve simple variable
        print("=== Test 1: Simple variable resolution ===")
        result = await resolver._run(
            module_path=str(temp_path),
            variable_expression="var.enable_public_access"
        )
        
        print(f"Found {len(result['resolutions'])} resolutions")
        if result['resolutions']:
            resolution = result['resolutions'][0]
            print(f"Variable: {resolution.variable_name}")
            print(f"Final value: {resolution.final_value}")
            print("Resolution chain:")
            for step in resolution.resolution_chain:
                print(f"  - {step.file_path}:{step.line_number}: {step.step_type} = {step.resolved_value}")
        print()
        
        # Test 2: Resolve complex expression
        print("=== Test 2: Complex expression resolution ===")
        result = await resolver._run(
            module_path=str(temp_path),
            variable_expression="${var.bucket_name}-${var.environment}"
        )
        
        if result['resolutions']:
            resolution = result['resolutions'][0]
            print(f"Expression: {resolution.initial_expression}")
            print(f"Final value: {resolution.final_value}")
            print("Resolution chain:")
            for step in resolution.resolution_chain:
                print(f"  - {step.file_path}:{step.line_number}: {step.variable_name} = {step.resolved_value}")
        print()
        
        # Test 3: Resolve all variables
        print("=== Test 3: All variables resolution ===")
        result = await resolver._run(module_path=str(temp_path))
        
        print(f"Found {len(result['variable_assignments'])} variable assignments")
        print(f"Found {len(result['variable_definitions'])} variable definitions")
        print(f"Found {len(result['resolutions'])} resolutions")
        print()
        
        for resolution in result['resolutions']:
            print(f"Variable: {resolution.variable_name}")
            print(f"Final value: {resolution.final_value}")
            if resolution.errors:
                print(f"Errors: {resolution.errors}")
            print()


if __name__ == "__main__":
    asyncio.run(test_variable_resolution()) 