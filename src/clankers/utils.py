from typing import Mapping


def required_string(config: Mapping[str, object], key: str) -> str:
    value = optional_string(config, key)
    if value is None:
        raise ValueError(f"missing required configuration value {key}")
    return value


def optional_string(config: Mapping[str, object], key: str) -> str | None:
    value = config.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"configuration value {key} must be a string")
    return value
