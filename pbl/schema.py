# pbl/schema.py
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Stage:
    phase: str
    stage_id: str
    title: str

@dataclass(frozen=True)
class PBLStructure:
    theme: str
    stages: List[Stage]
