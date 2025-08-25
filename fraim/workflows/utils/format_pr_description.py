from typing import List

from fraim.outputs.risk import Risk


def format_pr_description(risks: List[Risk]) -> str:
    """Format a list of risks into a PR description with bulleted lists.

    Args:
        risks: List of Risk objects to format

    Returns:
        A formatted string suitable for a PR description
    """
    if not risks:
        return "No risks were identified in this PR."

    description = "# Security Risk Review Required\n\n"
    description += "The following security risks have been identified and require review:\n\n"

    # Group risks by risk type for better organization
    risks_by_type: dict[str, List[Risk]] = {}
    for risk in risks:
        if risk.risk_type not in risks_by_type:
            risks_by_type[risk.risk_type] = []
        risks_by_type[risk.risk_type].append(risk)

    # Format each risk type and its risks
    for risk_type, type_risks in risks_by_type.items():
        description += f"## {risk_type}\n\n"
        for risk in type_risks:
            description += f"### {risk.risk} (Severity: {risk.risk_severity})\n\n"
            description += f"**Location**: `{risk.file_path}:{risk.line_number}`\n\n"
            description += "**Explanation**:\n"
            # Split explanation into bullet points if it contains multiple sentences
            explanations = [e.strip() for e in risk.explanation.split(".") if e.strip()]
            for explanation in explanations:
                if explanation:
                    description += f"* {explanation}.\n"
            description += f"\n**Confidence**: {risk.confidence * 10}%\n\n"
            description += "---\n\n"

    description += "\nPlease review these risks and ensure appropriate mitigations are in place before approving."
    return description
