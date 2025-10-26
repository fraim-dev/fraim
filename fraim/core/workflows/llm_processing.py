# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
from dataclasses import dataclass
from typing import Annotated

from fraim.core.llms import LiteLLM

logger = logging.getLogger(__name__)


@dataclass
class LLMOptions:
    """Base input for chunk-based workflows."""

    model: Annotated[str, {"help": "Model to use for initial scan (default: anthropic/claude-sonnet-4-0)"}] = (
        "anthropic/claude-sonnet-4-0"
    )

    temperature: Annotated[float, {"help": "Temperature setting for the model (0.0-1.0, default: 0)"}] = 0


class LLMMixin:
    def __init__(self, args: LLMOptions):
        # Workaround for GPT-5 models, which don't support temperature
        if "gpt-5" in args.model:
            logger.warning("GPT-5 models don't support temperature, setting temperature to 1")
            args.temperature = 1

        self.llm = LiteLLM(
            model=args.model,
            additional_model_params={"temperature": args.temperature},
        )
