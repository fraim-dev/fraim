# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Format Slack messages for risks.
"""

import hashlib

from jinja2 import Environment

from fraim.actions.github import parse_pr_url
from fraim.outputs import sarif

# =============================== Helper functions for Jinja Template ===============================


def render_pr_name(pr_url: str | None) -> str:
    """Get the PR name from the URL."""
    if not pr_url:
        return ""
    owner, repo, pr_number = parse_pr_url(pr_url.strip())
    return f"{owner}/{repo}#{pr_number}"


def render_location(location: sarif.PhysicalLocation) -> str:
    """Returns a formatted string for the location."""
    file = location.artifactLocation.uri

    start_line = location.region.startLine
    end_line = location.region.endLine

    return f"{file}:{start_line}-{end_line}"


def render_location_gh_url(pr_url: str | None, location: sarif.PhysicalLocation) -> str:
    """Returns a formatted string for the location URL."""
    file = location.artifactLocation.uri
    file_hash = hashlib.sha256(file.encode()).hexdigest()

    start_line = location.region.startLine
    end_line = location.region.endLine

    if pr_url:
        return f"{pr_url}/files#diff-{file_hash}R{start_line}-R{end_line}"
    return f"{file}:{start_line}-{end_line}"


def render_severity_circle(severity: str) -> str:
    """Map severity level to colored circle emoji.

    Args:
        severity: The severity level string ("critical", "high", "medium", "low")

    Returns:
        Colored circle emoji corresponding to the severity
    """
    severity_lower = severity.lower().strip()
    if severity_lower in ["critical", "high"]:
        return "🔴"  # Red circle
    if severity_lower == "medium":
        return "🟠"  # Orange circle
    if severity_lower == "low":
        return "🟡"  # Yellow circle
    return "⚪"  # White circle for unknown severity


# Register the helper functions with the Jinja template
env = Environment(autoescape=False)
env.globals["render_severity_circle"] = render_severity_circle
env.globals["render_pr_name"] = render_pr_name
env.globals["render_location"] = render_location
env.globals["render_location_gh_url"] = render_location_gh_url


# =============================== Template for Slack message ===============================

SLACK_MESSAGE_TEMPLATE = """
{
    "blocks": [
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🔍 Fraim '{{ workflow_name }}' found *{{ risks | length }}* issues{% if pr_url %} in pull request *<{{ pr_url }}|{{ render_pr_name(pr_url) }}>*{% endif %}"
            }
        }{% if risks %},{% endif %}
{%- for risk in risks[:max_risks] %}
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*{{ risk.properties.risk_type }}*"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "{{ render_severity_circle(risk.properties.risk_severity) }} {{ risk.properties.risk_severity }} with {{ risk.properties.confidence * 10 }}% confidence"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": {{ risk.message.text.strip() | tojson }}
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "📍 <{{ render_location_gh_url(pr_url, risk.locations[0].physicalLocation) }}|{{ render_location(risk.locations[0].physicalLocation) }}>"
                }
            ]
        }{% if not loop.last or risks | length > max_risks %}
        ,
        {
            "type": "divider"
        },
        {% endif %}
{%- endfor %}
{% if risks | length > max_risks %}
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_... and {{ risks | length - max_risks }} more risk{{ 's' if risks | length - max_risks > 1 else '' }}_."
            }
        }
{% endif %}
    ]
}
"""

# The maximum number of risks to include in the Slack message. Slack limits the number of blocks in message to 50.
# Each risk uses 5 blocks, but we want to reserve room for the title block and a truncation message.
MAX_RISKS = 8


def format_slack_message(risks: list[sarif.Result], workflow_name: str | None = None, pr_url: str | None = None) -> str:
    """Format a list of risks into a Slack message using Slack mrkdwn format.

    Args:
        risks: List of SARIF Result objects with risk overlay properties
        pr_url: Optional URL of the pull request to include as a hyperlink

    Returns:
        A formatted string suitable for Slack messages
    """

    # Render the Jinja template
    template = env.from_string(SLACK_MESSAGE_TEMPLATE)

    return template.render(
        max_risks=MAX_RISKS,
        risks=risks,
        pr_url=pr_url,
        workflow_name=workflow_name,
    ).strip()
