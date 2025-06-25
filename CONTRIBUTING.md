## 🤝 Contributing

We welcome contributions to Fraim! Here's how to get started:

### Development Setup

1. **Fork the repository**
2. **Create a development environment**:
```bash
git clone https://github.com/fraim-dev/fraim.git
cd fraim
uv sync --dev
```

3. **Install pre-commit hooks**:
```bash
uv run pre-commit install
```

### Contributing Guidelines

- **Code Style**: Follow PEP 8 and use the included linting tools
- **Testing**: Add tests for new functionality
- **Documentation**: Update documentation for new features
- **Workflows**: Test new workflows thoroughly before submitting

### Types of Contributions

- **New Workflows**: Add workflows for different security use cases
- **Tool Integrations**: Connect with existing security tools
- **Bug Fixes**: Fix issues and improve stability
- **Documentation**: Improve guides and examples

### Submitting Changes

1. Create a feature branch (`git checkout -b feature/amazing-feature`)
2. Make your changes with appropriate tests
3. Ensure all tests pass (`uv run pytest`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to your branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request
