"""A Hugging Face sequence classifier running in-process on CPU (the launch model)."""

from __future__ import annotations

import logging
import re

from sentiment.classifier.base import ModelInfo, Span, canonical_order
from sentiment.text import FUNCTION_WORDS

log = logging.getLogger(__name__)


class LocalHFClassifier:
    def __init__(
        self, checkpoint: str, *, revision: str, max_length: int = 512, threads: int = 1, micro_batch: int = 1
    ) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(max(1, threads))
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(checkpoint, revision=revision)
        self._model = AutoModelForSequenceClassification.from_pretrained(checkpoint, revision=revision)
        self._model.eval()
        # Explanations need gradients for the input only, never for the weights.
        self._model.requires_grad_(False)
        self._order = canonical_order(self._model.config.id2label)
        self._max_length = max_length
        # On a CPU core, padding a batch to its longest text costs more than batching saves:
        # measured on the 1-OCPU Ampere VM, 1 text per forward pass scored 2.3x faster than 32.
        self._micro_batch = max(1, micro_batch)
        self.info = ModelInfo(name=checkpoint, revision=revision, backend="local_hf")
        log.info("classifier loaded", extra={"model": checkpoint, "revision": revision, "threads": threads})

    def predict(self, texts: list[str]) -> list[tuple[float, float, float]]:
        results: list[tuple[float, float, float]] = []
        for start in range(0, len(texts), self._micro_batch):
            results.extend(self._forward(texts[start : start + self._micro_batch]))
        return results

    def _forward(self, texts: list[str]) -> list[tuple[float, float, float]]:
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

    def explain(self, texts: list[str]) -> list[list[Span]]:
        return [self._explain_one(text) for text in texts]

    def _explain_one(self, text: str, *, steps: int = 16, top: int = 5, floor: float = 0.25) -> list[Span]:
        """Integrated gradients (Sundararajan et al. 2017) for the positive-minus-negative logit.

        The baseline replaces every word piece with [PAD] and keeps [CLS] and [SEP]; all `steps` points on
        the path run as one batch. Word pieces are summed into whole words. A word scores above zero when it
        pushed the text toward positive and below zero toward negative, scaled so the strongest word is +/-1.
        Function words, punctuation, and words weaker than `floor` of the strongest are left out.
        """
        torch = self._torch
        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
            return_offsets_mapping=True,
        )
        offsets = encoded.pop("offset_mapping")[0].tolist()
        word_ids = encoded.word_ids(0)
        input_ids = encoded["input_ids"]
        embed = self._model.get_input_embeddings()
        special = torch.tensor([word is None for word in word_ids])
        baseline_ids = input_ids.clone()
        baseline_ids[0, ~special] = self._tokenizer.pad_token_id
        with torch.no_grad():
            actual = embed(input_ids)
            baseline = embed(baseline_ids)
        alphas = torch.linspace(1 / steps, 1, steps).view(-1, 1, 1)
        path = (baseline + alphas * (actual - baseline)).requires_grad_(True)
        extra = {k: v.expand(steps, -1) for k, v in encoded.items() if k != "input_ids"}
        negative, _, positive = self._order
        with torch.enable_grad():
            logits = self._model(inputs_embeds=path, **extra).logits.float()
            (logits[:, positive] - logits[:, negative]).sum().backward()
        token_scores = ((actual - baseline)[0] * path.grad.mean(0)).sum(-1).tolist()
        words: dict[int, list[float]] = {}
        for index, word in enumerate(word_ids):
            if word is None:
                continue
            start, end = offsets[index]
            if word in words:
                words[word][1] = end
                words[word][2] += token_scores[index]
            else:
                words[word] = [start, end, token_scores[index]]
        candidates = [w for w in words.values() if _is_content_word(text[int(w[0]) : int(w[1])])]
        strongest = max((abs(w[2]) for w in candidates), default=0.0)
        if strongest == 0:
            return []
        ranked = sorted(candidates, key=lambda w: abs(w[2]), reverse=True)
        return [
            (int(start), int(end), round(score / strongest, 3))
            for start, end, score in ranked[:top]
            if abs(score) >= floor * strongest
        ]


_WORDLIKE = re.compile(r"[A-Za-z]{3,}")


def _is_content_word(word: str) -> bool:
    return bool(_WORDLIKE.search(word)) and word.lower() not in FUNCTION_WORDS
