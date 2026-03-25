from pathlib import Path
from typing import List
import yaml

from llm_test_lab_core.models import Scenario


def load_scenarios_from_yaml(path: str) -> List[Scenario]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return [Scenario(**item) for item in data]


def load_scenarios_from_string(yaml_text: str) -> List[Scenario]:
    data = yaml.safe_load(yaml_text)
    return [Scenario(**item) for item in data]
