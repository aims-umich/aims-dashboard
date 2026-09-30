from __future__ import annotations

from sentiment.classifier.base import ModelInfo


class FakeClassifier:
    """Deterministic stand-in for BERT: 'good' -> positive, 'bad' -> negative, else neutral."""

    def __init__(self, name: str = "fake/model", revision: str = "r1") -> None:
        self.info = ModelInfo(name=name, revision=revision, backend="fake")
        self.calls: list[list[str]] = []

    def predict(self, texts: list[str]) -> list[tuple[float, float, float]]:
        self.calls.append(list(texts))
        out = []
        for text in texts:
            lowered = text.lower()
            if "good" in lowered:
                out.append((0.05, 0.15, 0.8))
            elif "bad" in lowered:
                out.append((0.7, 0.2, 0.1))
            else:
                out.append((0.2, 0.6, 0.2))
        return out
