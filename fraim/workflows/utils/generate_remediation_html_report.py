# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
"""
Utility for generating HTML reports from remediation workflow results.

This module provides functionality to create detailed, actionable HTML reports
from remediation data, organizing remediations by type and providing clear 
instructions for implementation.
"""

import json
import logging
import os
import secrets
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional

from jinja2 import Environment, BaseLoader, select_autoescape

from fraim.outputs.sarif import Result, SarifReport


class RemediationHTMLGenerator:
    """Generate HTML reports specifically for remediation workflow output."""

    def __init__(self) -> None:
        # Use in-memory templates instead of file system
        self.jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @classmethod
    def generate_remediation_html_report(
        cls, 
        sarif_report: SarifReport, 
        repo_name: str, 
        output_path: str,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """Generate HTML report from SARIF remediation results."""
        generator = cls()
        try:
            html_content = generator._generate_html_content_from_sarif(sarif_report, repo_name)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            if logger:
                logger.info(f"Generated remediation HTML report: {output_path}")
        except Exception as e:
            if logger:
                logger.error(f"Failed to generate remediation HTML report: {str(e)}")
            raise

    def _generate_html_content_from_sarif(self, sarif_report: SarifReport, repo_name: str) -> str:
        """Generate HTML content from SARIF report data."""
        processed_data = self._process_remediation_data(sarif_report)
        
        template_context = {
            "repo_name": repo_name or "Wiz Findings",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "script_nonce": self._generate_nonce(),
            "style_nonce": self._generate_nonce(),
            "remediations": processed_data["remediations"],
            "summary": processed_data["summary"],
            "css_styles": self._get_css_styles(),
            "javascript": self._get_javascript(),
        }
        
        template = self.jinja_env.from_string(self._get_html_template())
        return template.render(**template_context)

    def _process_remediation_data(self, sarif_report: SarifReport) -> Dict[str, Any]:
        """Process SARIF data to extract remediation information."""
        runs = sarif_report.runs
        if not runs:
            raise ValueError("SARIF report must contain at least one run")

        all_remediations = []
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        type_counts = {"code": 0, "cli": 0, "configuration": 0, "manual": 0}
        
        for run in runs:
            results = run.results or []
            
            for result in results:
                remediation_data = self._extract_remediation_from_result(result)
                if remediation_data:
                    all_remediations.append(remediation_data)
                    
                    # Update counts
                    severity = remediation_data.get("severity", "medium")
                    remediation_type = remediation_data.get("type", "manual")
                    
                    if severity in severity_counts:
                        severity_counts[severity] += 1
                    if remediation_type in type_counts:
                        type_counts[remediation_type] += 1

        # Group remediations by type
        grouped_remediations = self._group_remediations_by_type(all_remediations)
        
        summary = {
            "total_remediations": len(all_remediations),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "grouped_remediations": grouped_remediations,
        }

        return {
            "remediations": all_remediations,
            "summary": summary,
        }

    def _extract_remediation_from_result(self, result: Result) -> Optional[Dict[str, Any]]:
        """Extract remediation data from a SARIF result."""
        try:
            # Extract basic information
            message_text = result.message.text or "Untitled Remediation"
            
            # Try to extract action details from message if structured
            title = message_text
            action_details = {}
            
            if " | ACTION_DETAILS: " in message_text:
                try:
                    title, action_details_json = message_text.split(" | ACTION_DETAILS: ", 1)
                    action_details = json.loads(action_details_json)
                except (ValueError, json.JSONDecodeError):
                    # If parsing fails, use the whole message as title
                    pass
            
            description = title  # Use title as description
            
            # Extract severity from level
            severity_map = {
                "error": "critical",
                "warning": "high", 
                "note": "medium",
                "none": "low"
            }
            severity = severity_map.get(result.level or "note", "medium")
            
            # Try to extract additional details from properties
            properties = result.properties.model_dump() if result.properties else {}
            
            # Default remediation data
            remediation_data: Dict[str, Any] = {
                "id": f"rem_{hash(title)}", 
                "title": title,
                "description": description,
                "severity": severity,
                "type": action_details.get("type", "manual"),  # Use type from action details
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending",
                "confidence": properties.get("confidence", 7) if properties.get("confidence") else 7,
                "action_details": action_details  # Use parsed action details
            }
            
            # If no action details were parsed, try to infer from title/description
            if not action_details:
                remediation_data.update(self._infer_remediation_type_and_details(title, description, properties))
            
            return remediation_data
            
        except Exception:
            return None

    def _infer_remediation_type_and_details(self, title: str, description: str, properties: Dict) -> Dict[str, Any]:
        """Infer remediation type and extract action details from available data."""
        title_lower = title.lower()
        desc_lower = description.lower()
        
        # Code remediation indicators
        if any(keyword in title_lower or keyword in desc_lower for keyword in 
               ["fix", "update", "change", "modify", "replace", "code"]):
            return {
                "type": "code",
                "action_details": {
                    "description": description,
                    "file_path": properties.get("file_path", "Unknown file"),
                    "change_description": title
                }
            }
        
        # CLI remediation indicators  
        elif any(keyword in title_lower or keyword in desc_lower for keyword in 
                 ["install", "run", "execute", "command", "npm", "pip", "yarn", "update"]):
            return {
                "type": "cli", 
                "action_details": {
                    "description": description,
                    "command": self._extract_command_from_text(title + " " + description),
                    "requires_sudo": "sudo" in desc_lower
                }
            }
        
        # Configuration remediation indicators
        elif any(keyword in title_lower or keyword in desc_lower for keyword in 
                 ["config", "setting", "parameter", "environment", "env"]):
            return {
                "type": "configuration",
                "action_details": {
                    "description": description,
                    "config_type": "configuration file",
                    "change_description": title
                }
            }
        
        # Default to manual
        else:
            return {
                "type": "manual",
                "action_details": {
                    "description": description,
                    "steps": [title]
                }
            }

    def _extract_command_from_text(self, text: str) -> str:
        """Try to extract a command from text."""
        # Look for common command patterns
        import re
        
        # Look for command-like patterns
        command_patterns = [
            r'(?:run|execute|install)\s+([^\n.]+)',
            r'`([^`]+)`',  # Code blocks
            r'npm\s+[^\n]+',
            r'pip\s+[^\n]+', 
            r'yarn\s+[^\n]+',
            r'apt\s+[^\n]+',
            r'brew\s+[^\n]+',
        ]
        
        for pattern in command_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if pattern.startswith('(?:') else match.group(0)
        
        return text.strip()

    def _group_remediations_by_type(self, remediations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group remediations by their type."""
        grouped: Dict[str, List[Dict[str, Any]]] = {"code": [], "cli": [], "configuration": [], "manual": []}
        
        for remediation in remediations:
            rem_type = remediation.get("type", "manual")
            if rem_type in grouped:
                grouped[rem_type].append(remediation)
            else:
                grouped["manual"].append(remediation)
        
        return grouped

    def _generate_nonce(self) -> str:
        """Generate a random nonce for CSP."""
        return base64.b64encode(secrets.token_bytes(32)).decode("ascii")

    def _get_html_template(self) -> str:
        """Return the HTML template for remediation reports."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ repo_name }} - Remediation Report</title>
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-{{ script_nonce }}'; style-src 'nonce-{{ style_nonce }}'; font-src 'self' data:; img-src 'none'; connect-src 'none'; media-src 'none'; object-src 'none'; child-src 'none'; frame-src 'none'; worker-src 'none'; form-action 'none'; base-uri 'none'; manifest-src 'none';">
    <style nonce="{{ style_nonce }}">
        {{ css_styles }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 {{ repo_name }} - Remediation Report</h1>
        <div class="timestamp">Generated on {{ timestamp }}</div>
    </div>
    
    <div class="container">
        <div class="summary-section">
            <h2>Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{ summary.total_remediations }}</div>
                    <div class="stat-label">Total Remediations</div>
                </div>
                {% for type, count in summary.type_counts.items() %}
                <div class="stat-card type-{{ type }}">
                    <div class="stat-number">{{ count }}</div>
                    <div class="stat-label">{{ type.title() }}</div>
                </div>
                {% endfor %}
            </div>
            
            <div class="severity-breakdown">
                <h3>By Severity</h3>
                <div class="severity-bars">
                    {% for severity, count in summary.severity_counts.items() %}
                    {% if count > 0 %}
                    <div class="severity-bar">
                        <span class="severity-label {{ severity }}">{{ severity.title() }}</span>
                        <div class="bar-container">
                            <div class="bar {{ severity }}" style="width: {{ (count / summary.total_remediations * 100) if summary.total_remediations > 0 else 0 }}%"></div>
                        </div>
                        <span class="severity-count">{{ count }}</span>
                    </div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>
        </div>

        <div class="remediations-section">
            <h2>Remediations by Type</h2>
            
            {% for type, remediations in summary.grouped_remediations.items() %}
            {% if remediations %}
            <div class="remediation-group">
                <h3 class="group-header">
                    <span class="type-icon type-{{ type }}">
                        {% if type == 'code' %}💻
                        {% elif type == 'cli' %}⌨️
                        {% elif type == 'configuration' %}⚙️
                        {% else %}📋{% endif %}
                    </span>
                    {{ type.title() }} Remediations ({{ remediations|length }})
                </h3>
                
                {% for remediation in remediations %}
                <div class="remediation-card {{ remediation.severity }}">
                    <div class="remediation-header">
                        <h4>{{ remediation.title }}</h4>
                        <div class="remediation-meta">
                            <span class="severity-badge {{ remediation.severity }}">{{ remediation.severity.title() }}</span>
                            <span class="confidence-badge">{{ remediation.confidence }}/10</span>
                        </div>
                    </div>
                    
                    <div class="remediation-steps">
                        {% if remediation.type == 'code' %}
                        <div class="steps-container code-steps">
                            <div class="step-header">🔧 Code Changes Required</div>
                            <div class="step-item">
                                <div class="step-number">1</div>
                                <div class="step-content">
                                    <strong>Edit file:</strong> <code class="inline-code">{{ remediation.action_details.get('file_path', 'Unknown file') }}</code>
                                </div>
                            </div>
                            <div class="step-item">
                                <div class="step-number">2</div>
                                <div class="step-content">
                                    <strong>Apply change:</strong> {{ remediation.action_details.get('change_description', remediation.title) }}
                                </div>
                            </div>
                        </div>
                        
                        {% elif remediation.type == 'cli' %}
                        <div class="steps-container cli-steps">
                            <div class="step-header">⌨️ Command to Execute</div>
                            <div class="step-item">
                                <div class="step-number">1</div>
                                <div class="step-content">
                                    <div class="command-block">
                                        <code class="command">{{ remediation.action_details.get('command', remediation.title) }}</code>
                                        <button class="copy-btn" onclick="copyToClipboard(this)" data-text="{{ remediation.action_details.get('command', remediation.title) }}">📋 Copy</button>
                                    </div>
                                    {% if remediation.action_details.get('requires_sudo') %}
                                    <div class="warning">⚠️ Requires administrator privileges</div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                        
                        {% elif remediation.type == 'configuration' %}
                        <div class="steps-container config-steps">
                            <div class="step-header">⚙️ Configuration Update</div>
                            <div class="step-item">
                                <div class="step-number">1</div>
                                <div class="step-content">
                                    <strong>Configuration type:</strong> {{ remediation.action_details.get('config_type', 'Configuration file') }}
                                </div>
                            </div>
                            <div class="step-item">
                                <div class="step-number">2</div>
                                <div class="step-content">
                                    <strong>Required change:</strong> {{ remediation.action_details.get('change_description', remediation.title) }}
                                </div>
                            </div>
                        </div>
                        
                        {% else %}
                        <div class="steps-container manual-steps">
                            <div class="step-header">📋 Manual Steps</div>
                            {% for step in remediation.action_details.get('steps', [remediation.title]) %}
                            <div class="step-item">
                                <div class="step-number">{{ loop.index }}</div>
                                <div class="step-content">{{ step }}</div>
                            </div>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            {% endfor %}
        </div>
    </div>

    <script nonce="{{ script_nonce }}">
        {{ javascript }}
    </script>
</body>
</html>'''

    def _get_css_styles(self) -> str:
        """Return CSS styles for the remediation report."""
        return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        .timestamp {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .summary-section {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            text-align: center;
            padding: 1.5rem;
            border-radius: 8px;
            background: #f8f9fa;
            border: 2px solid #e9ecef;
        }

        .stat-card.type-code { border-color: #007bff; }
        .stat-card.type-cli { border-color: #28a745; }
        .stat-card.type-configuration { border-color: #ffc107; }
        .stat-card.type-manual { border-color: #6c757d; }

        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .severity-breakdown h3 {
            margin-bottom: 1rem;
            color: #333;
        }

        .severity-bars {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .severity-bar {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .severity-label {
            min-width: 80px;
            font-weight: 600;
            font-size: 0.9rem;
        }

        .severity-label.critical { color: #dc3545; }
        .severity-label.high { color: #fd7e14; }
        .severity-label.medium { color: #ffc107; }
        .severity-label.low { color: #20c997; }
        .severity-label.info { color: #6f42c1; }

        .bar-container {
            flex: 1;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }

        .bar {
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }

        .bar.critical { background: #dc3545; }
        .bar.high { background: #fd7e14; }
        .bar.medium { background: #ffc107; }
        .bar.low { background: #20c997; }
        .bar.info { background: #6f42c1; }

        .severity-count {
            min-width: 30px;
            text-align: right;
            font-weight: 600;
        }

        .remediations-section {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .remediation-group {
            margin-bottom: 2rem;
        }

        .group-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
            color: #333;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 0.5rem;
        }

        .type-icon {
            font-size: 1.5rem;
        }

        .remediation-card {
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin-bottom: 1rem;
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .remediation-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .remediation-card.critical { border-left: 4px solid #dc3545; }
        .remediation-card.high { border-left: 4px solid #fd7e14; }
        .remediation-card.medium { border-left: 4px solid #ffc107; }
        .remediation-card.low { border-left: 4px solid #20c997; }
        .remediation-card.info { border-left: 4px solid #6f42c1; }

        .remediation-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 1rem;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }

        .remediation-header h4 {
            color: #333;
            margin-bottom: 0.5rem;
        }

        .remediation-meta {
            display: flex;
            gap: 0.5rem;
            flex-shrink: 0;
        }

        .severity-badge, .confidence-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .severity-badge.critical { background: #dc3545; color: white; }
        .severity-badge.high { background: #fd7e14; color: white; }
        .severity-badge.medium { background: #ffc107; color: black; }
        .severity-badge.low { background: #20c997; color: white; }
        .severity-badge.info { background: #6f42c1; color: white; }

        .confidence-badge {
            background: #6c757d;
            color: white;
        }

        .remediation-steps {
            padding: 1rem;
        }

        .steps-container {
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            overflow: hidden;
        }

        .step-header {
            background: #007bff;
            color: white;
            padding: 0.75rem 1rem;
            font-weight: 600;
            font-size: 1rem;
        }

        .code-steps .step-header { background: #007bff; }
        .cli-steps .step-header { background: #28a745; }
        .config-steps .step-header { background: #ffc107; color: #000; }
        .manual-steps .step-header { background: #6c757d; }

        .step-item {
            display: flex;
            align-items: flex-start;
            padding: 1rem;
            border-bottom: 1px solid #e9ecef;
        }

        .step-item:last-child {
            border-bottom: none;
        }

        .step-number {
            background: #007bff;
            color: white;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.8rem;
            margin-right: 1rem;
            flex-shrink: 0;
        }

        .code-steps .step-number { background: #007bff; }
        .cli-steps .step-number { background: #28a745; }
        .config-steps .step-number { background: #ffc107; color: #000; }
        .manual-steps .step-number { background: #6c757d; }

        .step-content {
            flex: 1;
            line-height: 1.6;
        }

        .inline-code {
            background: #e9ecef;
            color: #495057;
            padding: 0.125rem 0.375rem;
            border-radius: 3px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9rem;
        }

        .command-block {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.5rem 0;
        }

        .command {
            background: #2d3748;
            color: #e2e8f0;
            padding: 0.75rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            overflow-x: auto;
            flex: 1;
            border: none;
            font-size: 0.9rem;
        }

        .copy-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 0.5rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: background-color 0.2s;
        }

        .copy-btn:hover {
            background: #218838;
        }

        .copy-btn:active {
            background: #1e7e34;
        }

        .warning {
            color: #856404;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
        }

        ol {
            margin-left: 1.5rem;
        }

        ol li {
            margin-bottom: 0.5rem;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 1rem;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .remediation-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .remediation-meta {
                margin-top: 0.5rem;
            }
        }
        '''

    def _get_javascript(self) -> str:
        """Return JavaScript for interactive features."""
        return '''
        // Copy to clipboard functionality
        function copyToClipboard(button) {
            const text = button.getAttribute('data-text');
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(() => {
                    showCopyFeedback(button);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                    fallbackCopy(text, button);
                });
            } else {
                fallbackCopy(text, button);
            }
        }

        function fallbackCopy(text, button) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                showCopyFeedback(button);
            } catch (err) {
                console.error('Fallback copy failed: ', err);
            }
            document.body.removeChild(textArea);
        }

        function showCopyFeedback(button) {
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            button.style.background = '#20c997';
            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '#28a745';
            }, 2000);
        }

        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            // Animate severity bars on page load
            setTimeout(() => {
                const bars = document.querySelectorAll('.bar');
                bars.forEach(bar => {
                    const width = bar.style.width;
                    bar.style.width = '0%';
                    setTimeout(() => {
                        bar.style.width = width;
                    }, 100);
                });
            }, 500);

            // Add hover effects to step items
            const stepItems = document.querySelectorAll('.step-item');
            stepItems.forEach(item => {
                item.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#f1f3f4';
                });
                item.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '';
                });
            });
        });
        '''


def generate_remediation_html_report(
    results: List[Result], 
    repo_name: str, 
    output_dir: str, 
    logger: logging.Logger
) -> str:
    """
    Generate an HTML report for remediation workflow results.
    
    Args:
        results: List of SARIF Results from remediation workflow
        repo_name: Name of the repository
        output_dir: Directory to write the report to
        logger: Logger instance
        
    Returns:
        Path to the generated HTML report file
    """
    from fraim.outputs.sarif import create_sarif_report
    
    # Create SARIF report from results
    sarif_report = create_sarif_report(results)
    
    # Generate filename
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_repo_name = "".join(c if c.isalnum() else "_" for c in repo_name).strip("_")
    html_filename = f"fraim_remediation_report_{safe_repo_name}_{current_time}.html"
    html_output_file = os.path.join(output_dir, html_filename)
    
    # Generate the report
    RemediationHTMLGenerator.generate_remediation_html_report(
        sarif_report=sarif_report,
        repo_name=repo_name,
        output_path=html_output_file,
        logger=logger
    )
    
    return html_output_file 