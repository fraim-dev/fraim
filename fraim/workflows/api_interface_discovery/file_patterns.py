# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
API Interface Discovery File Patterns

File patterns for identifying API interface and specification files.
"""

# API-focused file patterns
API_INTERFACE_FILE_PATTERNS = [
    # API & Schema files
    "openapi.json",
    "swagger.json",
    "*.openapi.yaml",
    "*.swagger.yaml",
    "*.graphql",
    "*.proto",
    "*.avsc",
    "*.avdl",
    # Source code files (most likely to contain API definitions)
    "*.py",
    "*.js",
    "*.ts",
    "*.tsx",
    "*.jsx",
    "*.java",
    "*.go",
    "*.rb",
    "*.php",
    "*.rs",
    "*.cs",
    "*.swift",
    "*.cpp",
    "*.c",
    "*.h",
    # Framework-specific files
    "settings.py",
    "urls.py",
    "views.py",
    "models.py",  # Django
    "app.py",
    "routes.py",
    "config.py",
    "*.blueprint.py",  # Flask
    "server.js",
    "app.js",
    "index.js",
    "main.js",
    "*.routes.js",  # Node.js
    "Application.java",
    "Controller.java",
    "Service.java",
    "*Controller.java",  # Spring
    "*.component.ts",
    "*.service.ts",
    "*.module.ts",
    "*.resolver.ts",  # Angular/NestJS
    # API documentation and configuration
    "*.yaml",
    "*.yml",
    "*.json",
    "*.toml",
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
]
