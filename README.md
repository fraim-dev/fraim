# Fraim

A flexible framework for security teams to build and deploy AI-powered workflows that complement their existing security operations.

## 🔭 Overview

Fraim empowers security teams to easily create, customize, and deploy AI workflows tailored to their specific security needs. Rather than providing a one-size-fits-all solution, Fraim gives teams the building blocks to construct intelligent automation that integrates seamlessly with their existing security stack.

## ❓ Why Fraim?

- **Framework-First Approach**: Build custom AI workflows instead of using rigid, pre-built tools
- **Security Team Focused**: Designed specifically for security operations and threat analysis
- **Extensible Architecture**: Easily add new workflows, data sources, and AI models

## 💬 Community & Support

Join our growing community of security professionals using Fraim:

- **Documentation**: Visit [docs.fraim.dev](https://docs.fraim.dev) for comprehensive guides and tutorials
- **Schedule a Demo**: [Book time with our team](https://calendly.com/fraim-dev/fraim-intro) - We'd love to help! Schedule a call for anything related to Fraim (debugging, new integrations, customizing workflows, or even just to chat)
- **Slack Community**: [Join our Slack](https://join.slack.com/t/fraimworkspace/shared_invite/zt-38cunxtki-B80QAlLj7k8JoPaaYWUKNA) - Get help, share ideas, and connect with other security minded people looking to use AI to help their team succeed
- **Issues**: Report bugs and request features via GitHub Issues
- **Contributing**: See the [contributing guide](CONTRIBUTING.md) for more information.

## 🔎 Preview

![CLI Preview](assets/cli-preview.gif)
*Example run of the CLI*


![UI Preview](assets/ui-preview.gif)
*Output of running the `code` workflow*

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/) package manager**
- **API Key** for your chosen AI provider (Google Gemini, OpenAI, etc.)

### Installation

1. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Clone and setup Fraim**:
```bash
git clone https://github.com/fraim-dev/fraim.git
cd fraim
uv sync
```

3. **Configure your AI provider**:
```bash
# For Google Gemini
echo "GEMINI_API_KEY=your_api_key_here" > .env

# For OpenAI
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### Basic Usage

```bash
# Run code security analysis on a Git repository
uv run fraim --repo https://github.com/username/repo-name --workflows code

# Analyze local directory
uv run fraim --path /path/to/code --workflows code
```

## 📖 Documentation

### Running Workflows

```bash
# Specify particular workflows
uv run fraim --path /code --modules code,iac

# Adjust performance settings
uv run fraim --path /code --processes 4 --chunk-size 1000

# Enable debug logging
uv run fraim --path /code --debug

# Custom output location
uv run fraim --path /code --output /path/to/results/
```

### Observability

Fraim supports optional observability and tracing through [Langfuse](https://langfuse.com), which helps track workflow performance, debug issues, and analyze AI model usage.

To enable observability:

1. **Install with observability support**:
```bash
uv sync --group langfuse
```

2. **Enable observability during execution**:
```bash
uv run fraim --path /code --workflows code --observability langfuse
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
*Status: Available*
*Workflow Name: scan*

Automated source code vulnerability scanning using AI-powered analysis. Detects common security issues across multiple programming languages including SQL injection, XSS, CSRF, and more.

Example
```
uv run fraim --repo https://github.com/username/repo-name --workflows code
```

### Infrastructure as Code (IAC) Analysis
*Status: Available*
*Workflow Name: iac*

Analyzes infrastructure configuration files for security misconfigurations and compliance violations.

Example
```
uv run fraim --repo https://github.com/username/repo-name --workflows iac
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

@workflow('my_custom_workflow', file_patterns=FILE_PATTERNS)
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

*Fraim is built by security teams, for security teams. Help us make AI-powered security accessible to everyone.*
