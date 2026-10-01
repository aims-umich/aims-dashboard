from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sentiment import LABELS


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    revision: str
    backend: str


# [start, end, score]: a word's character span in the text and how hard it pushed the prediction,
# from -1 (toward negative) to +1 (toward positive), relative to the text's strongest word.
Span = tuple[int, int, float]


class Classifier(Protocol):
    info: ModelInfo

    def predict(self, texts: list[str]) -> list[tuple[float, float, float]]:
        """Return (p_negative, p_neutral, p_positive) for each text, in order."""
        ...


class Explainer(Protocol):
    """A classifier that can also say which words drove each prediction (optional)."""

    def explain(self, texts: list[str]) -> list[list[Span]]:
        """Return the most influential words of each text, strongest first."""
        ...


def canonical_order(id2label: dict[int, str]) -> list[int]:
    """Column indices that reorder a model's outputs into (negative, neutral, positive)."""
    by_name = {str(name).lower(): int(idx) for idx, name in id2label.items()}
    missing = [label for label in LABELS if label not in by_name]
    if missing:
        raise ValueError(f"Model labels {sorted(by_name)} do not cover {missing}")
    return [by_name[label] for label in LABELS]
