# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Terraform-specific tools for Infrastructure as Code analysis.

These tools provide specialized functionality for analyzing Terraform configurations,
including module source tracing, input variable analysis, and security validation.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from fraim.core.tools import BaseTool, ToolError


class AnalyzeTerraformModulesArgs(BaseModel):
    """Arguments for analyzing Terraform modules."""
    project_path: str = Field(description="Path to the Terraform project root")
    file_pattern: Optional[str] = Field(default="*.tf", description="File pattern to search (default: *.tf)")


class ResolveTerraformModuleSourceArgs(BaseModel):
    """Arguments for resolving Terraform module sources."""
    source: str = Field(description="The module source string to resolve")
    project_path: str = Field(description="Path to the current Terraform project root")
    calling_file_path: Optional[str] = Field(default=None, description="Path of the file that references this module (for relative path resolution)")


class TraceTerraformVariablesArgs(BaseModel):
    """Arguments for tracing Terraform variables."""
    module_path: str = Field(description="Path to the Terraform module directory")
    input_variables: Optional[Dict[str, Any]] = Field(default=None, description="Specific input variables to trace (optional)")


class TerraformModuleInfo(BaseModel):
    """Information about a Terraform module block."""
    name: str = Field(description="Name of the module")
    source: str = Field(description="Source location of the module")
    version: Optional[str] = Field(default=None, description="Version constraint if specified")
    inputs: Dict[str, str] = Field(default_factory=dict, description="Input variables passed to the module")
    file_path: str = Field(description="Path to the file containing this module")
    line_number: int = Field(description="Line number where the module block starts")


class TerraformModuleAnalyzer(BaseTool):
    """Analyze Terraform modules and extract module blocks with their sources and inputs."""
    
    name: str = "analyze_terraform_modules"
    description: str = """
    Find and analyze all Terraform module blocks in the project.
    
    This tool scans Terraform files to identify module blocks, extract their source
    locations, version constraints, and input variables. Use this to understand
    module dependencies and trace data flow through module boundaries.
    
    Returns detailed information about each module including source, inputs, and location.
    """
    args_schema: Type[BaseModel] = AnalyzeTerraformModulesArgs

    async def _run(self, project_path: str, file_pattern: str = "*.tf") -> List[TerraformModuleInfo]:
        """Extract module information from Terraform files."""
        try:
            project_root = Path(project_path)
            if not project_root.exists():
                raise ToolError(f"Project path does not exist: {project_path}")
            
            terraform_files = list(project_root.rglob(file_pattern))
            modules: List[TerraformModuleInfo] = []
            
            for tf_file in terraform_files:
                try:
                    with open(tf_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    file_modules = self._parse_modules_from_content(content, str(tf_file))
                    modules.extend(file_modules)
                except Exception:
                    # Log warning but continue processing other files
                    continue
            
            return modules
            
        except Exception as e:
            raise ToolError(f"Failed to analyze Terraform modules: {str(e)}")

    def _parse_modules_from_content(self, content: str, file_path: str) -> List[TerraformModuleInfo]:
        """Parse module blocks from Terraform file content."""
        modules: List[TerraformModuleInfo] = []
        
        # Regular expression to find module blocks
        module_pattern = re.compile(r'^\s*module\s+"([^"]+)"\s*{', re.MULTILINE)
        
        for match in module_pattern.finditer(content):
            module_name = match.group(1)
            start_pos = match.start()
            line_number = content[:start_pos].count('\n') + 1
            
            # Find the end of the module block
            brace_count = 0
            in_module = False
            module_content = ""
            
            for char in content[match.start():]:
                if char == '{':
                    brace_count += 1
                    in_module = True
                elif char == '}':
                    brace_count -= 1
                
                module_content += char
                
                if in_module and brace_count == 0:
                    break
            
            # Parse module attributes
            module_info = self._parse_module_attributes(module_content, module_name, file_path, line_number)
            if module_info:
                modules.append(module_info)
        
        return modules

    def _parse_module_attributes(self, module_content: str, module_name: str, file_path: str, line_number: int) -> Optional[TerraformModuleInfo]:
        """Parse attributes from a module block."""
        try:
            source = None
            version = None
            inputs: Dict[str, str] = {}
            
            # Extract source
            source_match = re.search(r'source\s*=\s*"([^"]+)"', module_content)
            if source_match:
                source = source_match.group(1)
            
            # Extract version
            version_match = re.search(r'version\s*=\s*"([^"]+)"', module_content)
            if version_match:
                version = version_match.group(1)
            
            # Extract input variables (simple key = value pairs)
            input_pattern = re.compile(r'(\w+)\s*=\s*([^=\n]+?)(?=\n\s*\w+\s*=|\n\s*}|$)', re.MULTILINE | re.DOTALL)
            for input_match in input_pattern.finditer(module_content):
                key = input_match.group(1).strip()
                value = input_match.group(2).strip()
                
                # Skip source and version as they're handled separately
                if key not in ['source', 'version']:
                    inputs[key] = value
            
            if source:
                return TerraformModuleInfo(
                    name=module_name,
                    source=source,
                    version=version,
                    inputs=inputs,
                    file_path=file_path,
                    line_number=line_number
                )
            
            return None
            
        except Exception:
            # Skip malformed module blocks
            return None


class TerraformModuleSourceResolver(BaseTool):
    """Resolve Terraform module sources to their actual file paths or URLs."""
    
    name: str = "resolve_terraform_module_source"
    description: str = """
    Resolve a Terraform module source to its actual location and type.
    
    This tool takes a module source string and determines:
    - Whether it's a local path, Git repository, or registry module
    - The actual file system path (for local modules)
    - Repository URL and subdirectory (for Git modules)
    - Registry information (for registry modules)
    
    Use this after finding modules to understand where their code actually resides.
    """
    args_schema: Type[BaseModel] = ResolveTerraformModuleSourceArgs

    async def _run(self, source: str, project_path: str, calling_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Resolve module source to actual location."""
        try:
            result: Dict[str, Any] = {
                "source": source,
                "type": "unknown",
                "resolved_path": None,
                "repository_url": None,
                "subdirectory": None,
                "registry": None,
                "version": None
            }
            
            # Local path
            if source.startswith('./') or source.startswith('../') or not ('://' in source or source.count('/') >= 2):
                result["type"] = "local"
                
                if calling_file_path:
                    base_dir = os.path.dirname(calling_file_path)
                else:
                    base_dir = project_path
                
                resolved_path = os.path.normpath(os.path.join(base_dir, source))
                result["resolved_path"] = resolved_path
                
                # Check if path exists
                result["exists"] = os.path.exists(resolved_path)
                if not result["exists"]:
                    result["error"] = f"Local module path does not exist: {resolved_path}"
            
            # Git repository
            elif source.startswith('git::') or '.git' in source:
                result["type"] = "git"
                
                # Parse git source
                if source.startswith('git::'):
                    git_url = source[5:]  # Remove 'git::'
                else:
                    git_url = source
                
                # Extract subdirectory if present
                if '?' in git_url:
                    git_url, params = git_url.split('?', 1)
                    if 'ref=' in params:
                        result["version"] = params.split('ref=')[1].split('&')[0]
                
                if '//' in git_url:
                    repo_url, subdirectory = git_url.split('//', 1)
                    result["repository_url"] = repo_url
                    result["subdirectory"] = subdirectory
                else:
                    result["repository_url"] = git_url
            
            # Registry module
            elif source.count('/') >= 2 and not source.startswith('./') and not source.startswith('../'):
                result["type"] = "registry"
                
                # Parse registry module (namespace/name/provider or hostname/namespace/name/provider)
                parts = source.split('/')
                if len(parts) == 3:
                    # Public registry: namespace/name/provider
                    result["registry"] = {
                        "hostname": "registry.terraform.io",
                        "namespace": parts[0],
                        "name": parts[1],
                        "provider": parts[2]
                    }
                elif len(parts) >= 4:
                    # Private registry: hostname/namespace/name/provider
                    result["registry"] = {
                        "hostname": parts[0],
                        "namespace": parts[1],
                        "name": parts[2],
                        "provider": parts[3]
                    }
            
            return result
            
        except Exception as e:
            raise ToolError(f"Failed to resolve module source '{source}': {str(e)}")


class TerraformVariableTracer(BaseTool):
    """Trace Terraform variables through module boundaries to understand data flow."""
    
    name: str = "trace_terraform_variables"
    description: str = """
    Trace Terraform variables through a module to understand input validation and usage.
    
    This tool analyzes a Terraform module directory to:
    - Find all variable definitions (variables.tf or *.tf files)
    - Extract variable types, defaults, and validation rules
    - Identify how variables are used within the module
    - Check for potential security issues in variable handling
    
    Use this to understand what inputs a module expects and how they are processed.
    """
    args_schema: Type[BaseModel] = TraceTerraformVariablesArgs

    async def _run(self, module_path: str, input_variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trace variables through a Terraform module."""
        try:
            module_dir = Path(module_path)
            if not module_dir.exists():
                raise ToolError(f"Module path does not exist: {module_path}")
            
            result: Dict[str, Any] = {
                "module_path": module_path,
                "variable_definitions": [],
                "variable_usage": {},
                "security_concerns": [],
                "input_analysis": {}
            }
            
            # Find all Terraform files in the module
            tf_files = list(module_dir.glob("*.tf"))
            
            # Parse variable definitions and usage
            for tf_file in tf_files:
                with open(tf_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Simple variable parsing
                variables = self._parse_variables(content, str(tf_file))
                result["variable_definitions"].extend(variables)
                
                # Simple usage analysis
                usage = self._find_variable_usage(content, str(tf_file))
                for var_name, usages in usage.items():
                    if var_name not in result["variable_usage"]:
                        result["variable_usage"][var_name] = []
                    result["variable_usage"][var_name].extend(usages)
            
            # Analyze input variables if provided
            if input_variables:
                for var_name, var_value in input_variables.items():
                    result["input_analysis"][var_name] = {
                        "name": var_name,
                        "provided_value": str(var_value),
                        "has_definition": any(v["name"] == var_name for v in result["variable_definitions"]),
                        "security_issues": self._check_security_issues(str(var_value))
                    }
            
            return result
            
        except Exception as e:
            raise ToolError(f"Failed to trace variables in module '{module_path}': {str(e)}")

    def _parse_variables(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Parse variable definitions from content."""
        variables: List[Dict[str, Any]] = []
        
        # Find variable blocks
        var_pattern = re.compile(r'variable\s+"([^"]+)"\s*{([^}]+)}', re.MULTILINE | re.DOTALL)
        
        for match in var_pattern.finditer(content):
            var_name = match.group(1)
            var_block = match.group(2)
            
            var_info = {
                "name": var_name,
                "file_path": file_path,
                "line_number": content[:match.start()].count('\n') + 1,
                "type": None,
                "default": None,
                "description": None,
                "sensitive": False
            }
            
            # Extract type
            type_match = re.search(r'type\s*=\s*([^\n]+)', var_block)
            if type_match:
                var_info["type"] = type_match.group(1).strip()
            
            # Extract default
            default_match = re.search(r'default\s*=\s*([^\n]+)', var_block)
            if default_match:
                var_info["default"] = default_match.group(1).strip()
            
            # Extract description
            desc_match = re.search(r'description\s*=\s*"([^"]*)"', var_block)
            if desc_match:
                var_info["description"] = desc_match.group(1)
            
            # Check if sensitive
            sensitive_match = re.search(r'sensitive\s*=\s*true', var_block)
            if sensitive_match:
                var_info["sensitive"] = True
            
            variables.append(var_info)
        
        return variables

    def _find_variable_usage(self, content: str, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """Find variable usage in content."""
        usage: Dict[str, List[Dict[str, Any]]] = {}
        
        # Find variable references (var.variable_name)
        var_refs = re.finditer(r'var\.(\w+)', content)
        
        for ref in var_refs:
            var_name = ref.group(1)
            line_number = content[:ref.start()].count('\n') + 1
            
            if var_name not in usage:
                usage[var_name] = []
            
            usage[var_name].append({
                "file_path": file_path,
                "line_number": line_number,
                "context": self._get_line_context(content, ref.start())
            })
        
        return usage

    def _get_line_context(self, content: str, position: int) -> str:
        """Get the line context around a position."""
        lines = content[:position].split('\n')
        if lines:
            return lines[-1].strip()
        return ""

    def _check_security_issues(self, value: str) -> List[str]:
        """Check for security issues in a variable value."""
        issues: List[str] = []
        
        # Check for potentially sensitive data
        sensitive_patterns = [
            r'(?i)(password|passwd|secret|key|token|credential)',
            r'[A-Za-z0-9+/]{20,}={0,2}',  # Base64-like strings
            r'sk-[a-zA-Z0-9]{20,}',  # API key patterns
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, value):
                issues.append("Potentially sensitive data detected")
                break
        
        # Check for injection patterns
        injection_patterns = [
            r'[\$`]',  # Shell injection
            r'<script|javascript:',  # XSS patterns
            r'(\|\||&&|\;)',  # Command chaining
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                issues.append("Potential injection pattern detected")
                break
        
        return issues


class TerraformTools:
    """Collection of Terraform-specific analysis tools."""
    
    def __init__(self) -> None:
        self.tools = [
            TerraformModuleAnalyzer(),
            TerraformModuleSourceResolver(),
            TerraformVariableTracer()
        ] 