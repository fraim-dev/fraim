# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Configuration management for Gemini Scan.
"""

import logging
import multiprocessing as mp
import os
from typing import Optional


class Config:
    """Configuration class for Gemini Scan."""

    def __init__(
        self,
        mcp_port: int = 8765,
        model: str = "gemini/gemini-2.5-flash",
        scan_dir: str = "",
        temperature: float = 0,
        max_iterations: int = 50,
        host: str = "localhost",
        debug_mode: bool = False,
        processes: Optional[int] = None,
        prompt: Optional[str] = None,
        limit: Optional[int] = None,
        chunk_size: int = 500,
        confidence: int = 7,
        project_path: str = "",
    ):
        """
        Initialize configuration.

        Args:
            model: Name of the model to use (e.g., "gemini/gemini-2.5-flash", "openai/gpt-4")
            scan_dir: Directory to store scan outputs
            debug_mode: Whether to enable debug logging
            processes: Number of processes to use
            chunk_size: Number of lines per chunk
            logger: Logger instance
            max_iterations: Maximum number of tool calling iterations
            # project_path: Path to the project being scanned (set during scan)
            temperature: Temperature for model generation
            # limit: Limit the number of files to scan
            confidence: Minimum confidence threshold (1-10) for filtering findings
        """
        self.model = model

        # Validate that the correct API key environment variable is set
        api_key = self._get_api_key_for_model(model)
        if not api_key:
            provider = self._get_provider_from_model(model)
            env_var = self._get_env_var_for_provider(provider)
            raise ValueError(f"API key must be provided via {env_var} environment variable for {provider} models")

        self.scan_dir = scan_dir
        self.debug_mode = debug_mode
        self.processes = processes or mp.cpu_count() // 2
        self.chunk_size = chunk_size
        self.max_iterations = max_iterations
        self.temperature = temperature
        # self.limit = limit
        self.confidence = confidence
        self.project_path = project_path

        # Set up scan directory
        os.makedirs(self.scan_dir, exist_ok=True)

        # Set up logging files
        self.tool_calls_log = os.path.join(self.scan_dir, "tool_calls.log")
        self.interactions_log = os.path.join(self.scan_dir, "interactions.log")
        self.triage_log = os.path.join(self.scan_dir, "triage.log")
        self.false_positives_log = os.path.join(self.scan_dir, "false_positives.log")

        # Create log files with headers
        with open(self.tool_calls_log, "w") as f:
            f.write("timestamp,tool_name,parameters,result\n")

        with open(self.interactions_log, "w") as f:
            f.write("timestamp,conversation_id,message\n")

        with open(self.triage_log, "w") as f:
            f.write("timestamp,vulnerability_type,file_path,line_start,line_end,action\n")

        with open(self.false_positives_log, "w") as f:
            f.write("timestamp,vulnerability_type,file_path,line_start,line_end,reason,full_response\n")

        # Set up logging configuration
        self._setup_logging()
        self.logger = logging.getLogger()

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Create formatters
        console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Set log level based on debug mode
        log_level = logging.DEBUG if self.debug_mode else logging.INFO

        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # Add file handlers if scan_dir is set
        if self.scan_dir:
            # Main log file
            main_log = os.path.join(self.scan_dir, "fraim_scan.log")
            file_handler = logging.FileHandler(main_log)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

            # Triage log file
            triage_handler = logging.FileHandler(self.triage_log)
            triage_handler.setLevel(log_level)
            triage_handler.setFormatter(file_formatter)
            root_logger.addHandler(triage_handler)

        # Silence noisy third-party loggers (LiteLLM is handled in the LiteLLM wrapper)
        third_party_loggers = [
            "httpx",
            "urllib3",
            "urllib3.connectionpool",
        ]

        for logger_name in third_party_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    def _get_provider_from_model(self, model: str) -> str:
        """Extract the provider from the model name."""
        if "/" in model:
            return model.split("/")[0]
        return "unknown"

    def _get_env_var_for_provider(self, provider: str) -> str:
        """Get the expected environment variable name for a provider."""
        provider_env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "cohere": "COHERE_API_KEY",
            "azure": "AZURE_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
        }
        return provider_env_map.get(provider.lower(), f"{provider.upper()}_API_KEY")

    def _get_api_key_for_model(self, model_name: str) -> Optional[str]:
        """Get the API key for a given model from environment variables."""
        provider = self._get_provider_from_model(model_name)
        env_var = self._get_env_var_for_provider(provider)
        return os.environ.get(env_var)
