# Fraim

A flexible framework for security teams to build and deploy AI-powered workflows that complement their existing security operations.

## 🔭 Overview

Fraim empowers security teams to easily create, customize, and deploy AI workflows tailored to their specific security needs. Rather than providing a one-size-fits-all solution, Fraim gives teams the building blocks to construct intelligent automation that integrates seamlessly with their existing security stack.
Fraim comes built as a CLI, but you can also run workflows via our Github Action.

## ❓ Why Fraim?

- **Framework-First Approach**: Build custom AI workflows instead of using rigid, pre-built tools
- **Security Team Focused**: Designed specifically for security operations and threat analysis
- **Extensible Architecture**: Easily add new workflows, data sources, and AI models

## 🔎 Preview

![UI Preview](assets/ui-preview.gif)
_Output of running the `code` workflow_

## Github Action Quick Start

NOTE: This example assumes you are using a Gemini based model. If you’d like to use an OpenAI based model, replace references of GEMINI with OPENAI and specify an OpenAI model in the action arguments.

Set your API key as a Secret in your repo. - Settings -> Secrets and Variables -> New Repository Secret -> GEMINI_API_KEY
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
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          workflows: "code"
```

## 🚀 CLI Quick Start

### Prerequisites

- **Python 3.12+**
- **[pipx](https://pipx.pypa.io/stable/installation/) installation tool**
- **API Key** for your chosen AI provider (Google Gemini, OpenAI, etc.)

### Installation

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

### Basic Usage

```bash
# Run code security analysis on a Git repository
fraim code --location https://github.com/username/repo-name

# Analyze local directory
fraim code --location /path/to/code
```

## 💬 Community & Support

Join our growing community of security professionals using Fraim:

- **Documentation**: Visit [docs.fraim.dev](https://docs.fraim.dev) for comprehensive guides and tutorials
- **Schedule a Demo**: [Book time with our team](https://calendly.com/fraim-dev/fraim-intro) - We'd love to help! Schedule a call for anything related to Fraim (debugging, new integrations, customizing workflows, or even just to chat)
- **Slack Community**: [Join our Slack](https://join.slack.com/t/fraimworkspace/shared_invite/zt-38cunxtki-B80QAlLj7k8JoPaaYWUKNA) - Get help, share ideas, and connect with other security minded people looking to use AI to help their team succeed
- **Issues**: Report bugs and request features via GitHub Issues
- **Contributing**: See the [contributing guide](CONTRIBUTING.md) for more information.

## 📖 Documentation

### Running Workflows

```bash

# Adjust performance settings
fraim code --location /code --chunk-size 1000

# Enable debug logging
fraim --debug code --location /code

# Custom output location
fraim --output /path/to/results/ code --location /code
```

### Observability

Fraim supports optional observability and tracing through [Langfuse](https://langfuse.com), which helps track workflow performance, debug issues, and analyze AI model usage.

To enable observability:

1. **Install with observability support**:

```bash
pipx install 'fraim[langfuse]'
```

2. **Enable observability during execution**:

```bash
fraim --observability langfuse code --location /code
```

This will trace your workflow execution, LLM calls, and performance metrics in Langfuse for analysis and debugging.

### Configuration

Fraim uses a flexible configuration system that allows you to:

- Customize AI model parameters
- Configure workflow-specific settings
- Set up custom data sources
- Define output formats

See the `fraim/config/` directory for configuration options.

### Key Components

- **Workflow Engine**: Orchestrates AI agents and tools
- **LLM Integrations**: Support for multiple AI providers
- **Tool System**: Extensible security analysis tools
- **Input Connectors**: Git repositories, file systems, APIs
- **Output Formatters**: JSON, SARIF, HTML reports

## 🔧 Available Workflows

Fraim includes several pre-built workflows that demonstrate the framework's capabilities:

### Code Security Analysis

_Status: Available_
_Workflow Name: code_

Automated source code vulnerability scanning using AI-powered analysis. Detects common security issues across multiple programming languages including SQL injection, XSS, CSRF, and more.

Example

```
fraim code --location https://github.com/username/repo-name
```

### Infrastructure as Code (IAC) Analysis

_Status: Available_
_Workflow Name: iac_

Analyzes infrastructure configuration files for security misconfigurations and compliance violations.

Example

```
fraim iac --location https://github.com/username/repo-name
```

## 🛠️ Building Custom Workflows

Fraim makes it easy to create custom security workflows:

### 1. Define Input and Output Types

```python
# workflows/<name>/workflow.py
@dataclass
class MyWorkflowInput:
    """Input for the custom workflow."""
    code: Contextual[str]
    config: Config

type MyWorkflowOutput = List[sarif.Result]
```

### 2. Create Workflow Class

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

### 3. Create Prompt Files

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

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

_Fraim is built by security teams, for security teams. Help us make AI-powered security accessible to everyone._
