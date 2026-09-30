"""Sentiment classifiers behind one interface: `predict(texts) -> probabilities[n][3]`.

Probabilities are always in canonical order (negative, neutral, positive).
Swapping BERT for Gemma (or any other backend) is a config change plus a new `models` row.
"""

from __future__ import annotations

from sentiment.classifier.base import Classifier, ModelInfo
from sentiment.config import Settings


def build_classifier(settings: Settings) -> Classifier:
    backend = settings.scorer_backend
    if backend == "local_hf":
        from sentiment.classifier.local_hf import LocalHFClassifier

        return LocalHFClassifier(
            settings.scorer_model,
            revision=settings.scorer_revision,
            max_length=settings.scorer_max_length,
            threads=settings.scorer_threads,
            micro_batch=settings.scorer_micro_batch,
        )
    if backend == "modal":
        from sentiment.classifier.remote import RemoteClassifier

        if not settings.modal_endpoint_url or not settings.modal_token:
            raise ValueError("SCORER_BACKEND=modal needs MODAL_ENDPOINT_URL and MODAL_TOKEN")
        return RemoteClassifier(
            name=settings.scorer_model,
            revision=settings.scorer_revision,
            endpoint_url=settings.modal_endpoint_url,
            token=settings.modal_token.get_secret_value(),
            timeout_s=settings.modal_timeout_s,
        )
    raise ValueError(f"Unknown SCORER_BACKEND: {backend}")


__all__ = ["Classifier", "ModelInfo", "build_classifier"]
