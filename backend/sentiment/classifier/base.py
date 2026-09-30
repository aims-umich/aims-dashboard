from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sentiment import LABELS


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    revision: str
    backend: str


class Classifier(Protocol):
    info: ModelInfo

    def predict(self, texts: list[str]) -> list[tuple[float, float, float]]:
        """Return (p_negative, p_neutral, p_positive) for each text, in order."""
        ...


def canonical_order(id2label: dict[int, str]) -> list[int]:
    """Column indices that reorder a model's outputs into (negative, neutral, positive)."""
    by_name = {str(name).lower(): int(idx) for idx, name in id2label.items()}
    missing = [label for label in LABELS if label not in by_name]
    if missing:
        raise ValueError(f"Model labels {sorted(by_name)} do not cover {missing}")
    return [by_name[label] for label in LABELS]
