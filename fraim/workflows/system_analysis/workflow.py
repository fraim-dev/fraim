# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
System Analysis Workflow

Analyzes source code and documentation to extract system purpose, intended users, and business context.
This workflow addresses the Project Overview section of threat assessment questionnaires.
"""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Set

from pydantic import BaseModel

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkWorkflowInput, Workflow
from fraim.inputs.project import ProjectInput
from fraim.outputs import sarif
from fraim.workflows.registry import workflow

# File patterns for system analysis - focusing on documentation and key configuration files
FILE_PATTERNS = [
    # Documentation files
    "README.md",
    "readme.md",
    "README.txt",
    "readme.txt",
    "README.rst",
    "readme.rst",
    "CHANGELOG.md",
    "changelog.md",
    "INSTALL.md",
    "install.md",
    "CONTRIBUTING.md",
    "contributing.md",
    "LICENSE",
    "license",
    "LICENSE.md",
    "license.md",
    "*.md",
    "*.rst",
    "*.txt",
    # API documentation
    "*.yaml",
    "*.yml",
    "*.json",
    "openapi.json",
    "swagger.json",
    "api.json",
    "*.openapi.yaml",
    "*.swagger.yaml",
    # Configuration files that reveal system purpose
    "package.json",
    "setup.py",
    "pyproject.toml",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "composer.json",
    "Gemfile",
    "requirements.txt",
    "Pipfile",
    # Docker and deployment files
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    # Web application entry points
    "index.html",
    "app.py",
    "main.py",
    "__init__.py",
    "server.py",
    "app.js",
    "main.js",
    "index.js",
    "server.js",
    "main.go",
    "main.java",
    "Application.java",
    "*.component.ts",
    "*.component.js",
    "routes.py",
    "urls.py",
    "routes.js",
]

# Load prompts from YAML file
SYSTEM_ANALYSIS_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "system_analysis_prompts.yaml")
)


@dataclass
class SystemAnalysisInput(ChunkWorkflowInput):
    """Input for the System Analysis workflow."""

    business_context: Annotated[
        str, {"help": "Additional business context to consider during analysis"}
    ] = ""

    focus_areas: Annotated[
        Optional[List[str]],
        {"help": "Specific areas to focus on (e.g., authentication, data_processing, api_endpoints)"}
    ] = None


class SystemAnalysisResult(BaseModel):
    """Structured result from system analysis."""

    system_purpose: str
    intended_users: List[str]
    business_context: str
    key_features: List[str]
    user_roles: List[str]
    external_integrations: List[str]
    data_types: List[str]
    confidence_score: float


@dataclass
class SystemAnalysisChunkInput:
    """Input for analyzing a single chunk."""

    code: CodeChunk
    config: Config
    business_context: str = ""
    focus_areas: Optional[List[str]] = None


@workflow("system_analysis")
class SystemAnalysisWorkflow(Workflow[SystemAnalysisInput, Dict[str, Any]]):
    """
    Analyzes codebase and documentation to extract system purpose, intended users, and business context.

    This workflow examines:
    - Documentation files (README, API specs, etc.)
    - Configuration files that reveal system purpose
    - Application entry points and routing logic
    - Authentication and user management code
    - Business logic to understand core functionality
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config

        # Initialize LLM and analysis step
        self.llm = LiteLLM.from_config(self.config)
        analysis_parser = PydanticOutputParser(SystemAnalysisResult)
        self.analysis_step: LLMStep[SystemAnalysisChunkInput, SystemAnalysisResult] = LLMStep(
            self.llm,
            SYSTEM_ANALYSIS_PROMPTS["system"],
            SYSTEM_ANALYSIS_PROMPTS["user"],
            analysis_parser
        )

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for system analysis."""
        return FILE_PATTERNS

    def setup_project_input(self, input: SystemAnalysisInput) -> ProjectInput:
        """Setup project input for analysis."""
        from types import SimpleNamespace

        effective_globs = input.globs if input.globs is not None else self.file_patterns
        kwargs = SimpleNamespace(
            location=input.location,
            globs=effective_globs,
            limit=input.limit,
            chunk_size=input.chunk_size
        )
        return ProjectInput(config=self.config, kwargs=kwargs)

    async def process_chunks_concurrently(
        self,
        project: ProjectInput,
        input: SystemAnalysisInput,
        max_concurrent_chunks: int = 5,
    ) -> List[SystemAnalysisResult]:
        """Process chunks concurrently for system analysis."""
        results: List[SystemAnalysisResult] = []

        # Create semaphore to limit concurrent chunk processing
        semaphore = asyncio.Semaphore(max_concurrent_chunks)

        async def process_chunk_with_semaphore(chunk: CodeChunk) -> Optional[SystemAnalysisResult]:
            """Process a chunk with semaphore to limit concurrency."""
            async with semaphore:
                return await self._process_single_chunk(
                    chunk,
                    input.business_context,
                    input.focus_areas
                )

        # Process chunks as they stream in from the ProjectInput iterator
        active_tasks: Set[asyncio.Task] = set()

        for chunk in project:
            # Create task for this chunk and add to active tasks
            task = asyncio.create_task(process_chunk_with_semaphore(chunk))
            active_tasks.add(task)

            # If we've hit our concurrency limit, wait for some tasks to complete
            if len(active_tasks) >= max_concurrent_chunks:
                done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                for completed_task in done:
                    chunk_result = await completed_task
                    if chunk_result:
                        results.append(chunk_result)

        # Wait for any remaining tasks to complete
        if active_tasks:
            for future in asyncio.as_completed(active_tasks):
                chunk_result = await future
                if chunk_result:
                    results.append(chunk_result)

        return results

    async def _process_single_chunk(
        self,
        chunk: CodeChunk,
        business_context: str = "",
        focus_areas: Optional[List[str]] = None
    ) -> Optional[SystemAnalysisResult]:
        """Process a single chunk to extract system information."""
        try:
            self.config.logger.debug(
                f"Analyzing chunk: {Path(chunk.file_path)}")

            chunk_input = SystemAnalysisChunkInput(
                code=chunk,
                config=self.config,
                business_context=business_context,
                focus_areas=focus_areas
            )

            result = await self.analysis_step.run(chunk_input)

            # Only return results with high confidence
            if result.confidence_score >= 0.8:
                return result
            else:
                self.config.logger.debug(
                    f"Low confidence result ({result.confidence_score}) for {chunk.file_path}, skipping"
                )
                return None

        except Exception as e:
            self.config.logger.error(
                f"Failed to analyze chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}"
            )
            return None

    def _aggregate_results(self, chunk_results: List[SystemAnalysisResult]) -> Dict[str, Any]:
        """Aggregate results from multiple chunks into a comprehensive system analysis."""

        if not chunk_results:
            return {
                "system_purpose": "Unable to determine system purpose from available files",
                "intended_users": [],
                "business_context": "",
                "key_features": [],
                "user_roles": [],
                "external_integrations": [],
                "data_types": [],
                "confidence_score": 0.0,
                "analysis_summary": "No analyzable files found",
                "files_analyzed": 0,
                "total_chunks_processed": 0
            }

        # Aggregate all findings
        all_purposes = [
            r.system_purpose for r in chunk_results if r.system_purpose.strip()]
        all_users = []
        all_contexts = []
        all_features = []
        all_roles = []
        all_integrations = []
        all_data_types = []

        for result in chunk_results:
            all_users.extend(result.intended_users)
            if result.business_context.strip():
                all_contexts.append(result.business_context)
            all_features.extend(result.key_features)
            all_roles.extend(result.user_roles)
            all_integrations.extend(result.external_integrations)
            all_data_types.extend(result.data_types)

        # Smart deduplication with similarity matching
        unique_users = self._smart_deduplicate(all_users, max_items=7)
        unique_features = self._smart_deduplicate(all_features, max_items=10)
        unique_roles = self._smart_deduplicate(all_roles, max_items=6)
        unique_integrations = self._smart_deduplicate(
            all_integrations, max_items=8)
        unique_data_types = self._smart_deduplicate(
            all_data_types, max_items=10)

        # Select best system purpose (longest, most descriptive one)
        system_purpose = max(
            all_purposes, key=len) if all_purposes else "System purpose unclear"

        # Combine business contexts intelligently
        business_context = self._merge_contexts(all_contexts)

        # Calculate overall confidence (weighted average based on evidence quality)
        total_confidence = sum(r.confidence_score for r in chunk_results)
        avg_confidence = total_confidence / len(chunk_results)

        # Create comprehensive summary
        analysis_summary = self._create_analysis_summary(
            system_purpose, unique_users, unique_features, unique_roles, len(
                chunk_results)
        )

        return {
            "system_purpose": system_purpose,
            "intended_users": unique_users,
            "business_context": business_context,
            "key_features": unique_features,
            "user_roles": unique_roles,
            "external_integrations": unique_integrations,
            "data_types": unique_data_types,
            "confidence_score": avg_confidence,
            "analysis_summary": analysis_summary,
            "files_analyzed": len(chunk_results),
            "total_chunks_processed": len(chunk_results)
        }

    def _smart_deduplicate(self, items: List[str], max_items: int = 10) -> List[str]:
        """Intelligently deduplicate items with similarity matching."""
        if not items:
            return []

        # First pass: exact duplicates and normalize
        seen = set()
        normalized_items = []

        for item in items:
            if not item or not item.strip():
                continue

            # Normalize: strip, lower for comparison, but keep original case
            item = item.strip()
            normalized = item.lower()

            if normalized not in seen:
                seen.add(normalized)
                normalized_items.append(item)

        # Second pass: merge very similar items
        final_items: List[str] = []
        for item in normalized_items:
            is_duplicate = False
            for existing in final_items:
                # Check if items are very similar (substring or very close)
                if self._are_similar(item, existing):
                    is_duplicate = True
                    break

            if not is_duplicate:
                final_items.append(item)

        # Sort by length (longer descriptions first) and take top items
        final_items.sort(key=len, reverse=True)
        return final_items[:max_items]

    def _are_similar(self, item1: str, item2: str) -> bool:
        """Check if two items are similar enough to be considered duplicates."""
        item1_lower = item1.lower().strip()
        item2_lower = item2.lower().strip()

        # Exact match
        if item1_lower == item2_lower:
            return True

        # One is substring of the other
        if item1_lower in item2_lower or item2_lower in item1_lower:
            return True

        # Very similar after removing common words
        item1_clean = self._clean_for_comparison(item1_lower)
        item2_clean = self._clean_for_comparison(item2_lower)

        if item1_clean == item2_clean:
            return True

        return False

    def _clean_for_comparison(self, text: str) -> str:
        """Clean text for similarity comparison."""
        # Remove common filler words and normalize
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'via', 'through', 'using', 'user', 'users',
            'system', 'application', 'app', 'data', 'information', 'content',
            '(', ')', '[', ']', '-', ',', '.', ':', ';'
        }

        words = text.lower().split()
        cleaned_words = [w.strip('()[],-.:;')
                         for w in words if w.strip('()[],-.:;') not in common_words]
        return ' '.join(cleaned_words)

    def _merge_contexts(self, contexts: List[str]) -> str:
        """Intelligently merge business contexts, removing redundancy."""
        if not contexts:
            return ""

        # Deduplicate sentences and combine
        unique_sentences = []
        seen_content = set()

        for context in contexts:
            sentences = [s.strip() for s in context.replace(
                '.', '.\n').split('\n') if s.strip()]
            for sentence in sentences:
                sentence_clean = sentence.strip().lower()
                if sentence_clean not in seen_content and len(sentence) > 10:
                    seen_content.add(sentence_clean)
                    unique_sentences.append(sentence)

        # Combine and limit length
        combined = '. '.join(unique_sentences[:5])  # Max 5 sentences
        return combined

    def _create_analysis_summary(
        self,
        purpose: str,
        users: List[str],
        features: List[str],
        roles: List[str],
        files_analyzed: int
    ) -> str:
        """Create a human-readable summary of the analysis."""

        summary_parts = [
            f"Analyzed {files_analyzed} files to understand system characteristics.",
            f"System Purpose: {purpose}"
        ]

        if users:
            summary_parts.append(f"Intended Users: {', '.join(users[:5])}")
            if len(users) > 5:
                summary_parts[-1] += f" and {len(users) - 5} others"

        if features:
            summary_parts.append(f"Key Features: {', '.join(features[:3])}")
            if len(features) > 3:
                summary_parts[-1] += f" and {len(features) - 3} others"

        if roles:
            summary_parts.append(f"User Roles: {', '.join(roles[:3])}")
            if len(roles) > 3:
                summary_parts[-1] += f" and {len(roles) - 3} others"

        return " ".join(summary_parts)

    async def workflow(self, input: SystemAnalysisInput) -> Dict[str, Any]:
        """Main System Analysis workflow."""
        try:
            self.config.logger.info("Starting System Analysis workflow")

            # 1. Setup project input
            project = self.setup_project_input(input)

            # 2. Process chunks concurrently
            chunk_results = await self.process_chunks_concurrently(
                project=project,
                input=input,
                max_concurrent_chunks=input.max_concurrent_chunks
            )

            # 3. Aggregate results
            final_result = self._aggregate_results(chunk_results)

            self.config.logger.info(
                f"System Analysis completed. Analyzed {final_result['files_analyzed']} files. "
                f"Confidence: {final_result['confidence_score']:.2f}"
            )

            output_dir = getattr(self.config, "output_dir", None)
            if output_dir:
                import os
                import datetime

                os.makedirs(output_dir, exist_ok=True)
                app_name = getattr(self.config, "project_path", "application")
                app_name = os.path.basename(
                    app_name.rstrip(os.sep)) or "application"
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"system_analysis_{app_name}_{timestamp}.json"
                output_path = os.path.join(output_dir, output_filename)
                try:
                    import json
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(final_result, f, indent=2)
                    self.config.logger.info(
                        f"System analysis results written to {output_path}")
                except Exception as write_exc:
                    self.config.logger.error(
                        f"Failed to write system analysis results: {write_exc}")

            return final_result

        except Exception as e:
            self.config.logger.error(f"Error during system analysis: {str(e)}")
            raise e
