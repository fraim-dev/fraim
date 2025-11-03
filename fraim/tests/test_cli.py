# SPDX-License-Identifier: MIT
import argparse
from dataclasses import dataclass

from fraim.cli import workflow_options_to_cli_args


@dataclass
class SampleOptions:
    optional_number: int | None = None
    optional_list: list[str] | None = None
    flag: bool = False


def test_workflow_options_supports_pep604_optional() -> None:
    cli_args = workflow_options_to_cli_args(SampleOptions)

    opt_number = cli_args["--optional-number"]
    assert opt_number["default"] is None
    assert opt_number["required"] is False
    assert opt_number["type"] is int

    opt_list = cli_args["--optional-list"]
    assert opt_list["default"] is None
    assert opt_list["required"] is False
    assert opt_list["nargs"] == "+"

    flag_cfg = cli_args["--flag"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--flag", **flag_cfg)
    parsed = parser.parse_args([])
    assert parsed.flag is False
