import pytest

from sentiment.text import (
    EXCLUDED,
    NON_ENGLISH,
    RELEVANT,
    classify_relevance,
    is_english,
    nuclear_sentences,
    split_sentences,
    strip_html,
)


@pytest.mark.parametrize(
    "text",
    [
        "Nuclear power is the cleanest energy we have.",
        "Vogtle unit 4 is finally online",
        "SMRs could change the grid",
        "Big day for #NuclearPower in Michigan",
        "Fusion energy startups raised $2B this year",
        "Nuclear weapons and nuclear power are different things.",
        "Chernobyl still shapes how people see reactors",
    ],
)
def test_energy_texts_are_relevant(text):
    assert classify_relevance(text, lang="en").status == RELEVANT


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("The Senate may use the nuclear option on the filibuster.", "idiom"),
        ("He went nuclear on his coworkers.", "idiom"),
        ("My nuclear family went to the beach.", "idiom"),
        ("Iran's nuclear program is advancing, officials said.", "weapons"),
        ("A nuclear war would end civilization.", "weapons"),
        ("She works in nuclear medicine at the hospital.", "medicine"),
        ("Great weather today", "no_keyword"),
        ("jazz fusion night downtown", "no_keyword"),
        ("smr lol", "no_keyword"),
    ],
)
def test_off_topic_texts_are_excluded_with_a_reason(text, reason):
    result = classify_relevance(text, lang="en")
    assert result.status == EXCLUDED
    assert result.reason == reason


def test_declared_language_wins_and_heuristic_catches_undeclared():
    assert classify_relevance("Kernkraft ist gut", lang="de").status == NON_ENGLISH
    assert classify_relevance("La energía nuclear es muy segura para el clima").status == NON_ENGLISH
    assert is_english("Nuclear power plant closed today in Michigan after a long fight")
    assert is_english("#nuclear #smr")
    assert not is_english("原子力発電所")


def test_context_relevant_only_needs_english():
    assert classify_relevance("Great video, thanks!", context_relevant=True).status == RELEVANT
    assert classify_relevance("", context_relevant=True).status == EXCLUDED


def test_strip_html_keeps_block_breaks_and_unescapes():
    html = '<p>Nuclear &amp; wind</p><p>line two<br>line three <a href="x">#nuclear</a></p>'
    assert strip_html(html) == "Nuclear & wind\nline two\nline three #nuclear"


def test_split_sentences_respects_abbreviations():
    text = 'Dr. Smith said the U.S. plant is safe. It opened in Jan. 2020! Is it? "Yes." The NRC agreed.'
    assert split_sentences(text) == [
        "Dr. Smith said the U.S. plant is safe.",
        "It opened in Jan. 2020!",
        "Is it?",
        '"Yes."',
        "The NRC agreed.",
    ]


def test_nuclear_sentences_picks_only_mentions():
    body = "The council met on Tuesday. It debated a new nuclear plant. Parking was also discussed."
    assert nuclear_sentences(body) == ["It debated a new nuclear plant."]
