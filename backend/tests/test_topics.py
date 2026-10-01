import pytest

from sentiment.topics import TOPICS, topics_for


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A startup wants to power AI data centers with nuclear", ["data-centers"]),
        ("NuScale's SMR design got its NRC approval", ["advanced-reactors", "policy"]),
        ("Spent fuel storage at the plant still worries residents", ["waste", "fuel"]),
        ("Fusion ignition at NIF is a milestone", ["fusion"]),
        ("Vogtle ran billions over budget and ratepayers paid", ["cost"]),
        ("Nuclear is carbon-free and cuts emissions", ["climate"]),
        ("Chernobyl still shapes how people see radiation", ["safety"]),
        ("Uranium enrichment in the US is ramping up", ["fuel"]),
    ],
)
def test_rules_tag_each_topic(text, expected):
    assert topics_for(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "The fossil fuel industry is lobbying hard",  # not nuclear fuel
        "That reactor is mine",  # "mine" the pronoun
        "Said he'd aim for the stars",  # "aim" is not "AI"
        "A metaphor about a mainframe computer",  # "computer" is not "compute"
        "Nuclear power is great",
    ],
)
def test_rules_do_not_fire_on_near_misses(text):
    assert "fuel" not in topics_for(text)
    assert "data-centers" not in topics_for(text)


def test_topic_ids_are_unique_and_every_topic_lists_keywords():
    assert len({t.id for t in TOPICS}) == len(TOPICS)
    assert all(t.keywords for t in TOPICS)
