from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass(frozen=True)
class SsqDraw:
    issue: str
    draw_date: date
    reds: List[int]
    blue: int


@dataclass(frozen=True)
class DltDraw:
    issue: str
    draw_date: date
    fronts: List[int]
    backs: List[int]


@dataclass(frozen=True)
class SsqCombination:
    reds: List[int]
    blue: int


@dataclass(frozen=True)
class DltCombination:
    fronts: List[int]
    backs: List[int]

