"""A classifier served over HTTPS, such as Gemma-7B on a Modal GPU (Phase 4 of the plan).

The endpoint takes {"texts": [...]} with a bearer token and returns
{"probs": [[p_neg, p_neu, p_pos], ...]} in the same order.
"""

from __future__ import annotations

import httpx

from sentiment.classifier.base import ModelInfo


class RemoteClassifier:
    def __init__(self, *, name: str, revision: str, endpoint_url: str, token: str, timeout_s: float) -> None:
        self.info = ModelInfo(name=name, revision=revision, backend="modal")
        self._client = httpx.Client(
            base_url=endpoint_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_s,
        )

    def predict(self, texts: list[str]) -> list[tuple[float, float, float]]:
        if not texts:
            return []
        response = self._client.post("", json={"texts": texts})
        response.raise_for_status()
        probs = response.json()["probs"]
        if len(probs) != len(texts):
            raise ValueError(f"Remote classifier returned {len(probs)} rows for {len(texts)} texts")
        return [(float(p[0]), float(p[1]), float(p[2])) for p in probs]
