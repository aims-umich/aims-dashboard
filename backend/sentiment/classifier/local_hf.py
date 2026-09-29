"""A Hugging Face sequence classifier running in-process on CPU (the launch model)."""

from __future__ import annotations

import logging

from sentiment.classifier.base import ModelInfo, canonical_order

log = logging.getLogger(__name__)


class LocalHFClassifier:
    def __init__(self, checkpoint: str, *, revision: str, max_length: int = 512, threads: int = 1) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(max(1, threads))
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(checkpoint, revision=revision)
        self._model = AutoModelForSequenceClassification.from_pretrained(checkpoint, revision=revision)
        self._model.eval()
        self._order = canonical_order(self._model.config.id2label)
        self._max_length = max_length
        self.info = ModelInfo(name=checkpoint, revision=revision, backend="local_hf")
        log.info("classifier loaded", extra={"model": checkpoint, "revision": revision, "threads": threads})

    def predict(self, texts: list[str]) -> list[tuple[float, float, float]]:
        if not texts:
            return []
        torch = self._torch
        # Sort by length so each padded batch wastes as little compute as possible.
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        inputs = self._tokenizer(
            [texts[i] for i in order],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._max_length,
        )
        with torch.inference_mode():
            probs = torch.softmax(self._model(**inputs).logits.float(), dim=-1)[:, self._order]
        results: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)] * len(texts)
        for row, original in zip(probs.tolist(), order, strict=True):
            results[original] = (row[0], row[1], row[2])
        return results
