import os

import pytest

from sentiment.classifier.base import canonical_order


def test_canonical_order_reorders_by_label_name():
    assert canonical_order({0: "negative", 1: "neutral", 2: "positive"}) == [0, 1, 2]
    assert canonical_order({0: "POSITIVE", 1: "negative", 2: "neutral"}) == [1, 2, 0]


def test_canonical_order_rejects_models_without_three_classes():
    with pytest.raises(ValueError, match="do not cover"):
        canonical_order({0: "LABEL_0", 1: "LABEL_1"})


@pytest.mark.skipif(
    not os.environ.get("RUN_MODEL_TESTS"), reason="set RUN_MODEL_TESTS=1 to load the BERT model"
)
def test_local_bert_scores_obvious_examples():
    from sentiment.classifier.local_hf import LocalHFClassifier
    from sentiment.config import Settings

    settings = Settings(_env_file=None)
    clf = LocalHFClassifier(settings.scorer_model, revision=settings.scorer_revision)
    probs = clf.predict(
        [
            "Nuclear power is clean, safe, and exactly what we need.",
            "This nuclear plant is a dangerous disaster waiting to happen.",
        ]
    )
    assert all(abs(sum(p) - 1) < 1e-4 for p in probs)
    assert max(range(3), key=lambda i: probs[0][i]) == 2
    assert max(range(3), key=lambda i: probs[1][i]) == 0
