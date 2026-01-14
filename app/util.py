from typing import Any


def parse_filter_string(filter_str: str) -> dict:
    """
    Convert a string like `name__ic=target,tag=hello` to a dictionary
    {"name__ic": "target", "tag": "hello"}
    Currently, it doesn't support different data types, everything is a string
    """
    if not filter_str:
        return {}

    netbox_obj_filter = {}
    expected_filter_parts = 2
    parts = filter_str.split(",")
    for part in parts:
        value_parts = part.split("=")
        if len(value_parts) != expected_filter_parts:
            raise ValueError(f"filter {part} cannot be parsed correctly")

        key, value = value_parts
        netbox_obj_filter[key.strip()] = value.strip()

    return netbox_obj_filter


def netbox_value_to_default(value: Any) -> Any:
    """
    Convert current NetBox value to its default
    """
    if isinstance(value, str):
        return ""

    if isinstance(value, list):
        return []

    if isinstance(value, dict):
        return None

    if isinstance(value, int):
        return None

    return None
