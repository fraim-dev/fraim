# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.


from dataclasses import dataclass
from typing import Annotated

from fraim.core.llms import LiteLLM


@dataclass
class LLMOptions:
    """Base input for chunk-based workflows."""

    model: Annotated[str, {"help": "Model to use for initial scan (default: gemini/gemini-2.5-flash)"}] = (
        "gemini/gemini-2.5-flash"
    )

    temperature: Annotated[float, {"help": "Temperature setting for the model (0.0-1.0, default: 0)"}] = 0


class LLMMixin:
    def __init__(self, args: LLMOptions):
        super().__init__()  # type: ignore

        self.llm = LiteLLM(
            model=args.model,
            additional_model_params={"temperature": args.temperature},
        )
