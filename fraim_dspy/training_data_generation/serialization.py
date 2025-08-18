from typing import Any
import yaml  # type: ignore[import-untyped]


class LiteralString(str):
    """String type that will be dumped as a YAML literal block (|)."""


class LiteralDumper(yaml.SafeDumper):
    pass


def _literal_str_representer(dumper: "LiteralDumper", data: "LiteralString") -> Any:  # type: ignore[name-defined]
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')


LiteralDumper.add_representer(LiteralString, _literal_str_representer)
