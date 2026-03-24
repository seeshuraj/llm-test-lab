from pathlib import Path
from typing import List
import yaml

from llm_test_lab_core.models import Scenario


def load_scenarios_from_yaml(path: str) -> List[Scenario]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    # expect a list of dicts
    return [Scenario(**item) for item in data]
