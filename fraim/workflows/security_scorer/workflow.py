# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Security Scorer Workflow

Analyzes repository security hygiene and calculates a comprehensive security score.
"""

import logging
import os
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, Field

from fraim.core.history import EventRecord, HistoryRecord
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import Workflow
from fraim.core.workflows.llm_processing import LLMMixin, LLMOptions
from fraim.tools.filesystem import FilesystemTools

logger = logging.getLogger(__name__)

SCORING_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "prompts.yaml"))


class CategoryScore(BaseModel):
    """Score for a specific security category."""

    score: float = Field(ge=0, le=100, description="Category score from 0-100")
    reasoning: str = Field(description="Detailed explanation of the score")
    key_findings: list[str] = Field(description="Key findings from this category")
    recommendations: list[str] = Field(description="Recommendations for this category")


class RepoHygieneScore(CategoryScore):
    """Repository and build hygiene score."""
    pass


class DependencySupplyChainScore(CategoryScore):
    """Dependency and supply chain security score."""
    pass


class SecretsConfigScore(CategoryScore):
    """Secrets and configuration management score."""
    pass


class AppSecControlsScore(CategoryScore):
    """Application security controls score."""
    pass


class MemoryLanguageSafetyScore(CategoryScore):
    """Memory and language safety score."""
    pass


class CICDGuardsScore(CategoryScore):
    """CI/CD security guards score."""
    pass


class AdjustmentsScore(CategoryScore):
    """Adjustments score for fine-tuning."""
    pass


class CategoryBreakdown(BaseModel):
    """Breakdown of scores by category."""

    repo_hygiene: RepoHygieneScore = Field(description="Repository and build hygiene (weight: 20%)")
    dependency_supply_chain: DependencySupplyChainScore = Field(description="Dependency supply chain security (weight: 20%)")
    secrets_config: SecretsConfigScore = Field(description="Secrets and configuration (weight: 15%)")
    appsec_controls: AppSecControlsScore = Field(description="Application security controls (weight: 20%)")
    memory_language_safety: MemoryLanguageSafetyScore = Field(description="Memory/language safety (weight: 10%)")
    cicd_guards: CICDGuardsScore = Field(description="CI/CD security guards (weight: 15%)")
    adjustments: AdjustmentsScore = Field(description="Adjustments (weight: 10%)")


class SecurityScoreResult(BaseModel):
    """Result from security scoring analysis."""

    overall_score: int = Field(ge=1, le=100, description="Overall security score from 1-100")
    category_breakdown: CategoryBreakdown = Field(description="Detailed breakdown by category")
    key_factors: list[str] = Field(description="Key factors that influenced the overall score")
    recommendations: list[str] = Field(description="Top recommendations for improving security posture")


@dataclass
class ScoringInput:
    pass


@dataclass
class SecurityScorerWorkflowOptions(LLMOptions):
    """Options for the Security Scorer workflow."""

    project_path: Annotated[str, {"help": "Path to the repository to analyze"}] = "./"
    output_file: Annotated[str, {"help": "Path to save the security score report (optional)"}] = "fraim_output"


def aggregate_security_score(breakdown: CategoryBreakdown) -> int:
    """
    Deterministically aggregate category scores into an overall security score.
    
    Formula: Overall = Practices * 0.90 + Adjustments * 0.10
    
    Practices categories (90% of total):
    - Repo Hygiene: 20% = 0.20 * 0.90 = 0.18
    - Dependency Supply Chain: 20% = 0.20 * 0.90 = 0.18
    - Secrets Config: 15% = 0.15 * 0.90 = 0.135
    - AppSec Controls: 20% = 0.20 * 0.90 = 0.18
    - Memory/Language Safety: 10% = 0.10 * 0.90 = 0.09
    - CI/CD Guards: 15% = 0.15 * 0.90 = 0.135
    
    Adjustments: 10% = 0.10
    
    Args:
        breakdown: CategoryBreakdown with individual category scores
        
    Returns:
        Overall security score (1-100)
    """
    # Practices categories contribute 90% of the score
    practices_score = (
        breakdown.repo_hygiene.score * 0.18 +
        breakdown.dependency_supply_chain.score * 0.18 +
        breakdown.secrets_config.score * 0.135 +
        breakdown.appsec_controls.score * 0.18 +
        breakdown.memory_language_safety.score * 0.09 +
        breakdown.cicd_guards.score * 0.135
    )
    
    # Adjustments contribute 10% of the score
    adjustments_score = breakdown.adjustments.score * 0.10
    
    # Calculate final score and clamp to 1-100 range
    overall = practices_score + adjustments_score
    return max(1, min(100, int(round(overall))))


class SecurityScorerWorkflow(LLMMixin, Workflow[SecurityScorerWorkflowOptions, SecurityScoreResult]):
    """
    Analyzes repository security hygiene and calculates a comprehensive security score.

    This workflow:
    1. Explores the repository structure using FilesystemTools
    2. Analyzes each security category independently
    3. Aggregates category scores deterministically
    4. Provides detailed reasoning and recommendations per category
    5. Returns the comprehensive security score result
    """

    name = "security_scorer"

    def __init__(self, args: SecurityScorerWorkflowOptions) -> None:
        super().__init__(args)

        # Validate that the project path exists
        if not args.project_path or not os.path.exists(args.project_path):
            raise FileNotFoundError(f"Project path not found: {args.project_path}")

        # Configure filesystem tools for all scoring steps
        scoring_tools = FilesystemTools(args.project_path)
        scoring_llm = self.llm.with_tools(scoring_tools, 50)

        # Create individual scoring steps for each category
        self.repo_hygiene_step: LLMStep[ScoringInput, RepoHygieneScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["repo_hygiene_system"],
            SCORING_PROMPTS["repo_hygiene_user"],
            PydanticOutputParser(RepoHygieneScore),
        )

        self.dependency_supply_chain_step: LLMStep[ScoringInput, DependencySupplyChainScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["dependency_supply_chain_system"],
            SCORING_PROMPTS["dependency_supply_chain_user"],
            PydanticOutputParser(DependencySupplyChainScore),
        )

        self.secrets_config_step: LLMStep[ScoringInput, SecretsConfigScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["secrets_config_system"],
            SCORING_PROMPTS["secrets_config_user"],
            PydanticOutputParser(SecretsConfigScore),
        )

        self.appsec_controls_step: LLMStep[ScoringInput, AppSecControlsScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["appsec_controls_system"],
            SCORING_PROMPTS["appsec_controls_user"],
            PydanticOutputParser(AppSecControlsScore),
        )

        self.memory_language_safety_step: LLMStep[ScoringInput, MemoryLanguageSafetyScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["memory_language_safety_system"],
            SCORING_PROMPTS["memory_language_safety_user"],
            PydanticOutputParser(MemoryLanguageSafetyScore),
        )

        self.cicd_guards_step: LLMStep[ScoringInput, CICDGuardsScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["cicd_guards_system"],
            SCORING_PROMPTS["cicd_guards_user"],
            PydanticOutputParser(CICDGuardsScore),
        )

        self.adjustments_step: LLMStep[ScoringInput, AdjustmentsScore] = LLMStep(
            scoring_llm,
            SCORING_PROMPTS["adjustments_system"],
            SCORING_PROMPTS["adjustments_user"],
            PydanticOutputParser(AdjustmentsScore),
        )

    async def run(self) -> SecurityScoreResult:
        """
        Main Security Scorer workflow.

        Returns:
            SecurityScoreResult containing the security score and analysis
        """
        repo_name = os.path.basename(self.args.project_path.rstrip(os.sep))
        scoring_input = ScoringInput()

        # Step 1: Analyze Repository Hygiene
        hygiene_record = HistoryRecord(description="Analyzing repository hygiene")
        self.history.append_record(hygiene_record)
        repo_hygiene = await self.repo_hygiene_step.run(hygiene_record.history, scoring_input)
        hygiene_record.history.append_record(
            EventRecord(description=f"Repository hygiene score: {repo_hygiene.score:.1f}/100")
        )

        # Step 2: Analyze Dependency Supply Chain
        dependency_record = HistoryRecord(description="Analyzing dependency supply chain")
        self.history.append_record(dependency_record)
        dependency_supply_chain = await self.dependency_supply_chain_step.run(
            dependency_record.history, scoring_input
        )
        dependency_record.history.append_record(
            EventRecord(description=f"Dependency supply chain score: {dependency_supply_chain.score:.1f}/100")
        )

        # Step 3: Analyze Secrets and Configuration
        secrets_record = HistoryRecord(description="Analyzing secrets and configuration")
        self.history.append_record(secrets_record)
        secrets_config = await self.secrets_config_step.run(secrets_record.history, scoring_input)
        secrets_record.history.append_record(
            EventRecord(description=f"Secrets and config score: {secrets_config.score:.1f}/100")
        )

        # Step 4: Analyze Application Security Controls
        appsec_record = HistoryRecord(description="Analyzing application security controls")
        self.history.append_record(appsec_record)
        appsec_controls = await self.appsec_controls_step.run(appsec_record.history, scoring_input)
        appsec_record.history.append_record(
            EventRecord(description=f"Application security controls score: {appsec_controls.score:.1f}/100")
        )

        # Step 5: Analyze Memory and Language Safety
        memory_record = HistoryRecord(description="Analyzing memory and language safety")
        self.history.append_record(memory_record)
        memory_language_safety = await self.memory_language_safety_step.run(
            memory_record.history, scoring_input
        )
        memory_record.history.append_record(
            EventRecord(description=f"Memory/language safety score: {memory_language_safety.score:.1f}/100")
        )

        # Step 6: Analyze CI/CD Guards
        cicd_record = HistoryRecord(description="Analyzing CI/CD security guards")
        self.history.append_record(cicd_record)
        cicd_guards = await self.cicd_guards_step.run(cicd_record.history, scoring_input)
        cicd_record.history.append_record(
            EventRecord(description=f"CI/CD guards score: {cicd_guards.score:.1f}/100")
        )

        # Step 7: Calculate Adjustments
        adjustments_record = HistoryRecord(description="Calculating adjustments")
        self.history.append_record(adjustments_record)
        adjustments = await self.adjustments_step.run(adjustments_record.history, scoring_input)
        adjustments_record.history.append_record(
            EventRecord(description=f"Adjustments score: {adjustments.score:.1f}/100")
        )

        # Step 8: Aggregate scores deterministically
        category_breakdown = CategoryBreakdown(
            repo_hygiene=repo_hygiene,
            dependency_supply_chain=dependency_supply_chain,
            secrets_config=secrets_config,
            appsec_controls=appsec_controls,
            memory_language_safety=memory_language_safety,
            cicd_guards=cicd_guards,
            adjustments=adjustments,
        )

        overall_score = aggregate_security_score(category_breakdown)

        # Collect key factors and recommendations from all categories
        all_key_factors = []
        all_recommendations = []
        
        for category_name, category_score in [
            ("Repository Hygiene", repo_hygiene),
            ("Dependency Supply Chain", dependency_supply_chain),
            ("Secrets & Config", secrets_config),
            ("AppSec Controls", appsec_controls),
            ("Memory/Language Safety", memory_language_safety),
            ("CI/CD Guards", cicd_guards),
        ]:
            all_key_factors.extend([f"[{category_name}] {f}" for f in category_score.key_findings[:2]])
            all_recommendations.extend([f"[{category_name}] {r}" for r in category_score.recommendations[:2]])

        score_result = SecurityScoreResult(
            overall_score=overall_score,
            category_breakdown=category_breakdown,
            key_factors=all_key_factors[:10],  # Top 10 key factors
            recommendations=all_recommendations[:10],  # Top 10 recommendations
        )

        # Get total cost from history
        total_cost = self.history.get_total_cost()

        # Display results
        self._display_results(repo_name, score_result, total_cost)

        return score_result

    def _display_results(self, repo_name: str, result: SecurityScoreResult, total_cost: float) -> None:
        """Display formatted security scoring results."""
        print(f"\n{'='*80}")
        print(f"Security Score for {repo_name}: {result.overall_score}/100")
        print(f"{'='*80}")
        
        print(f"\n{'─'*80}")
        print("CATEGORY BREAKDOWN")
        print(f"{'─'*80}")
        
        categories = [
            ("Repository Hygiene (20%)", result.category_breakdown.repo_hygiene),
            ("Dependency Supply Chain (20%)", result.category_breakdown.dependency_supply_chain),
            ("Secrets & Configuration (15%)", result.category_breakdown.secrets_config),
            ("Application Security Controls (20%)", result.category_breakdown.appsec_controls),
            ("Memory/Language Safety (10%)", result.category_breakdown.memory_language_safety),
            ("CI/CD Security Guards (15%)", result.category_breakdown.cicd_guards),
            ("Adjustments (10%)", result.category_breakdown.adjustments),
        ]
        
        for category_name, category_score in categories:
            print(f"\n{category_name}: {category_score.score:.1f}/100")
            print(f"  Reasoning: {category_score.reasoning[:200]}{'...' if len(category_score.reasoning) > 200 else ''}")
        
        print(f"\n{'─'*80}")
        print("TOP KEY FACTORS")
        print(f"{'─'*80}")
        for i, factor in enumerate(result.key_factors, 1):
            print(f"{i}. {factor}")
        
        print(f"\n{'─'*80}")
        print("TOP RECOMMENDATIONS")
        print(f"{'─'*80}")
        for i, rec in enumerate(result.recommendations, 1):
            print(f"{i}. {rec}")
        
        print(f"\n{'─'*80}")
        print(f"Total cost: ${total_cost:.6f}")
        print(f"{'='*80}\n")

