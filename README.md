# Fraim - A Security Engineer's AI Toolkit
[![PyPI - Version](https://img.shields.io/pypi/v/fraim?style=flat&logo=python&logoColor=whitesmoke)](https://pypi.org/project/fraim/)
[![GitHub Action - Version](https://img.shields.io/github/v/release/fraim-dev/fraim-action?style=flat&logo=githubactions&logoColor=whitesmoke&label=github%20action)](https://github.com/marketplace/actions/fraim-security)
[![GitHub Repo stars](https://img.shields.io/github/stars/fraim-dev/fraim?style=flat&logo=github)](https://github.com/fraim-dev/fraim/stargazers)
[![Build](https://img.shields.io/github/actions/workflow/status/fraim-dev/fraim/ci.yml?branch=main&style=flat)](https://github.com/fraim-dev/fraim/actions/workflows/ci.yml)


## 🔭 Overview

Fraim gives security engineers AI-powered workflows to help them leverage the power of AI to solve REAL business needs. The workflows in this project are companions to a security engineer to help them find, detect, fix, and flag vulnerabilities across the development lifecycle.
You can run Fraim as a CLI or inside Github Actions.

## 🚩 Risk Flagger

Most security teams do not have visibility into the code changes happening on a day-to-day basis, and it is unrealistic to review every change. Risk Flagger solves this by requesting review on a Pull Request only if a "risk" is identified. These "risks" can be defined to match your specific use cases (ie "Flag any changes that make changes to authentication").

**Perfect for**:
- Security teams with no visibility into code changes
- Teams needing to focus limited security resources on the highest-priority risks
- Organizations wanting to implement "security left" practices

```bash
# Basic risk flagger with built-in risks
fraim run risk_flagger --model anthropic/claude-sonnet-4-20250514 --diff --base <base_sha> --head <head_sha> --approver security

# Custom risk considerations inline
fraim run risk_flagger --model anthropic/claude-sonnet-4-20250514 --diff --base <base_sha> --head <head_sha> --custom-risk-list-json '{"Database Changes": "All changes to a database should be flagged, similarly any networking changes that might affect the database should be flagged."}' --custom-risk-list-action replace --approver security

# Custom risk considerations
fraim run risk_flagger --model anthropic/claude-sonnet-4-20250514 --diff --base <base_sha> --head <head_sha> --custom-risk-list-filepath ./custom-risks.yaml --approver security
```

NOTE: we recommend using the Anthropic or OpenAI latest models for this workflow.


<img src="assets/risk-flagger-preview.png" alt="Risk Flagger Preview" width="500"/>

## 🛡️ Code Security Analysis

Most security teams rely on signature-based scanners and scattered linters that miss context and overwhelm engineers with noise. Code Security Analysis applies LLM-powered, context-aware review to surface real vulnerabilities across languages (e.g. injection, authentication/authorization flaws, insecure cryptography, secret exposure, and unsafe configurations), explaining impact and suggesting fixes. It integrates cleanly into CI via SARIF output and can run on full repos or just diffs to keep PRs secure without slowing delivery.

**Perfect for**:
- Security teams needing comprehensive vulnerability coverage
- Organizations requiring compliance with secure coding standards
- Teams wanting to catch vulnerabilities before they reach production

```bash
# Comprehensive code analysis
fraim run code --location https://github.com/username/repo-name

# Focus on recent changes
fraim run code --location . --diff --base main --head HEAD
```

## 🏗️ Infrastructure as Code (IAC) Analysis  

Cloud misconfigurations often slip through because policy-as-code checks and scattered linters miss context across modules, environments, and providers. Infrastructure as Code Analysis uses LLM-powered, context-aware review of Terraform, CloudFormation, and Kubernetes manifests to spot risky defaults, excessive permissions, insecure networking and storage, and compliance gaps—explaining impact and proposing safer configurations. It integrates cleanly into CI via SARIF and can run on full repos or just diffs to prevent drift without slowing delivery.

**Perfect for**:
- DevOps teams managing cloud infrastructure
- Organizations with strict compliance requirements
- Teams implementing Infrastructure as Code practices
- Security teams overseeing cloud security posture

```bash
# Analyze infrastructure configurations
fraim run iac --location https://github.com/username/repo-name
```

## 🚀 Getting Started

### Github Action Quick Start

NOTE: This example assumes you are using an Anthropic based model.

Set your API key as a Secret in your repo. - Settings -> Secrets and Variables -> New Repository Secret -> ANTHROPIC_API_KEY
Define your workflow inside your repo at .github/workflows/<action_name>.yml

```yaml
name: AI Security Scan
on:
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
      security-events: write # Required for uploading SARIF
      pull-requests: write # Required for PR comments and annotations

    steps:
      - name: Run Fraim Security Scan
        uses: fraim-dev/fraim-action@v0
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          workflows: "code"
```

### CLI Quick Start

#### Prerequisites

- **Python 3.12+**
- **[pipx](https://pipx.pypa.io/stable/installation/) installation tool**
- **API Key** for your chosen AI provider (Google Gemini, OpenAI, etc.)

#### Installation

NOTE: These instructions are for Linux based systems, see [docs](https://docs.fraim.dev/installation) for Windows installation instructions

1. **Install Fraim**:

```bash
pipx install fraim
```

2. **Configure your AI provider**:

   #### Google Gemini

   1. Get an API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   2. Export it in your environment:
      ```
      export GEMINI_API_KEY=your_api_key_here
      ```

   #### OpenAI

   3. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   4. Export it in your environment:
      ```
      export OPENAI_API_KEY=your_api_key_here
      ```

### Common CLI Arguments

#### Global Options (apply to all commands)

- `--debug`: Enable debug logging for troubleshooting
- `--show-logs SHOW_LOGS`: Print logs to standard error output  
- `--log-output LOG_OUTPUT`: Specify directory for log files
- `--observability langfuse`: Enable LLM observability and analytics

#### Workflow Options (apply to most workflows)

- `--location LOCATION`: Repository URL or local path to analyze
- `--model MODEL`: AI model to use (default varies by workflow, e.g., `gemini/gemini-2.5-flash`)
- `--temperature TEMPERATURE`: Model temperature setting (0.0-1.0, default: 0)
- `--chunk-size CHUNK_SIZE`: Number of lines per processing chunk
- `--limit LIMIT`: Maximum number of files to scan
- `--globs GLOBS`: File patterns to include in analysis
- `--max-concurrent-chunks MAX_CONCURRENT_CHUNKS`: Control parallelism

#### Git Diff Options

- `--diff`: Analyze only git diff instead of full repository
- `--head HEAD`: Git head commit for diff (default: HEAD)
- `--base BASE`: Git base commit for diff (default: empty tree)

#### Pull Request Integration  

- `--pr-url PR_URL`: URL of pull request to analyze
- `--approver APPROVER`: GitHub username/group to notify

### Observability

Fraim supports optional observability and tracing through [Langfuse](https://langfuse.com), which helps track workflow performance, debug issues, and analyze AI model usage.

To enable observability:

1. **Install with observability support**:

```bash
pipx install 'fraim[langfuse]'
```

2. **Enable observability during execution**:

```bash
fraim --observability langfuse run code --location /code
```

This will trace your workflow execution, LLM calls, and performance metrics in Langfuse for analysis and debugging.

## 💬 Community & Support

Join our growing community of security professionals using Fraim:

- **Documentation**: Visit [docs.fraim.dev](https://docs.fraim.dev) for comprehensive guides and tutorials
- **Schedule a Demo**: [Book time with our team](https://calendly.com/fraim-dev/fraim-intro) - We'd love to help! Schedule a call for anything related to Fraim (debugging, new integrations, customizing workflows, or even just to chat)
- **Slack Community**: [Join our Slack](https://join.slack.com/t/fraimworkspace/shared_invite/zt-38cunxtki-B80QAlLj7k8JoPaaYWUKNA) - Get help, share ideas, and connect with other security minded people looking to use AI to help their team succeed
- **Issues**: Report bugs and request features via GitHub Issues
- **Contributing**: See the [contributing guide](CONTRIBUTING.md) for more information.

## 🛠️ "Fraim"-work Development

### Building Custom Workflows

Fraim makes it easy to create custom security workflows tailored to your organization's specific needs:

### Key Framework Components

- **Workflow Engine**: Orchestrates AI agents and tools in flexible, composable patterns
- **LLM Integrations**: Support for multiple AI providers with seamless switching
- **Tool System**: Extensible security analysis tools that can be combined and customized
- **Input Connectors**: Git repositories, file systems, APIs, and custom data sources
- **Output Formatters**: JSON, SARIF, HTML reports, and custom output formats

### Configuration System

Fraim uses a flexible configuration system that allows you to:

- Customize AI model parameters for optimal performance
- Configure workflow-specific settings and thresholds
- Set up custom data sources and input methods
- Define custom output formats and destinations
- Manage API keys and authentication

See the `fraim/config/` directory for configuration options.

#### 1. Define Input and Output Types

```python
# workflows/<name>/workflow.py
@dataclass
class MyWorkflowInput:
    """Input for the custom workflow."""
    code: Contextual[str]
    config: Config

type MyWorkflowOutput = List[sarif.Result]
```

#### 2. Create Workflow Class

```python
# workflows/<name>/workflow.py

# Define file patterns for your workflow
FILE_PATTERNS = [
    '*.config', '*.ini', '*.yaml', '*.yml', '*.json'
]

# Load prompts from YAML files
PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "my_prompts.yaml"))

@workflow('my_custom_workflow')
class MyCustomWorkflow(Workflow[MyWorkflowInput, MyWorkflowOutput]):
    """Analyzes custom configuration files for security issues"""

    def __init__(self, config: Config, *args, **kwargs):
        super().__init__(config, *args, **kwargs)

        # Construct an LLM instance
        llm = LiteLLM.from_config(config)

        # Construct the analysis step
        parser = PydanticOutputParser(sarif.RunResults)
        self.analysis_step = LLMStep(llm, PROMPTS["system"], PROMPTS["user"], parser)

    async def workflow(self, input: MyWorkflowInput) -> MyWorkflowOutput:
        """Main workflow execution"""

        # 1. Analyze the configuration file
        analysis_results = await self.analysis_step.run({"code": input.code})

        # 2. Filter results by confidence threshold
        filtered_results = self.filter_results_by_confidence(
            analysis_results.results, input.config.confidence
        )

        return filtered_results

    def filter_results_by_confidence(self, results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
        """Filter results by confidence."""
        return [result for result in results if result.properties.confidence > confidence_threshold]
```

#### 3. Create Prompt Files

Create `my_prompts.yaml` in the same directory:

```yaml
system: |
  You are a configuration security analyzer.

  Your job is to analyze configuration files for security misconfigurations and vulnerabilities.

  <vulnerability_types>
    Valid vulnerability types (use EXACTLY as shown):

    - Hardcoded Credentials
    - Insecure Defaults
    - Excessive Permissions
    - Unencrypted Storage
    - Weak Cryptography
    - Missing Security Headers
    - Debug Mode Enabled
    - Exposed Secrets
    - Insecure Protocols
    - Missing Access Controls
  </vulnerability_types>

  {{ output_format }}

user: |
  Analyze the following configuration file for security issues:

  {{ code }}
```

## Stargazers

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=fraim-dev/fraim&type=Date&theme=dark" />
  <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=fraim-dev/fraim&type=Date" />
  <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=fraim-dev/fraim&type=Date" />
</picture>

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

_Fraim is built by security teams, for security teams. Help us make AI-powered security accessible to everyone._
