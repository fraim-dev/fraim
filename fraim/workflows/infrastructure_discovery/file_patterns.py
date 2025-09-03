# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery File Patterns

File patterns for identifying infrastructure and deployment configuration files.
"""

# Infrastructure-focused file patterns
INFRASTRUCTURE_FILE_PATTERNS = [
    # Infrastructure & Container files
    "Dockerfile",
    ".dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.k8s.yaml",
    "*.k8s.yml",
    "deployment.yaml",
    "service.yaml",
    "ingress.yaml",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "terraform.tfstate",
    # Infrastructure Configuration files
    "*.yaml",
    "*.yml",
    "*.json",
    "*.toml",
    "*.ini",
    "*.conf",
    "*.config",
    "*.properties",
    "*.env",
    ".env*",
    "*.settings",
    # Build & Package files (reveal deployment structure)
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
    # "Makefile",  # Temporarily disabled due to LLM processing issues
    # "makefile",
    "*.mk",
    # Orchestration and CI/CD files
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    "skaffold.yaml",
    "helm/**/*.yaml",
    "helm/**/*.yml",
]
