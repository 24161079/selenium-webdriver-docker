from dataclasses import dataclass
from typing import Optional


@dataclass
class ComboBoxIds:
    grade: Optional[str] = None
    class_room: Optional[str] = None
    subject: Optional[str] = None


@dataclass
class Selection:
    grade: str
    class_room: str
    subject: str


@dataclass
class StudentData:
    name: str
    frequency_scores: list[float]
    midterm_score: float | None
    finalterm_score: float | None
    comment: str
