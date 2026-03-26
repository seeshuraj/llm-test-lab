from pathlib import Path
from typing import List
import yaml

from llm_test_lab_core.models import Scenario


def _parse_items(data) -> list:
    """Accept either a bare list or {scenarios: [...]} dict."""
    if isinstance(data, dict):
        data = data.get("scenarios", [])
    if not isinstance(data, list):
        raise ValueError("YAML must be a list of scenarios or have a top-level 'scenarios:' key")
    return data


def load_scenarios_from_yaml(path: str) -> List[Scenario]:
    p = Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        mark = getattr(e, 'problem_mark', None)
        location = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        raise ValueError(f"YAML syntax error{location}: {e.problem if hasattr(e, 'problem') else e}")
    try:
        return [Scenario(**item) for item in _parse_items(data)]
    except Exception as e:
        raise ValueError(f"Scenario validation error: {e}")


def load_scenarios_from_string(yaml_text: str) -> List[Scenario]:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        mark = getattr(e, 'problem_mark', None)
        location = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        raise ValueError(f"YAML syntax error{location}: {e.problem if hasattr(e, 'problem') else e}")
    try:
        return [Scenario(**item) for item in _parse_items(data)]
    except Exception as e:
        raise ValueError(f"Scenario validation error: {e}")
