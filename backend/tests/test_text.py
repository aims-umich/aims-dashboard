import pytest

from sentiment.text import (
    EXCLUDED,
    NON_ENGLISH,
    RELEVANT,
    Relevance,
    article_context,
    classify_article_sentences,
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
        "The Palisades plant restart is on schedule",
        "SMRs could change the grid",
        "Big day for #NuclearPower in Michigan",
        "Fusion energy startups raised $2B this year",
        "Nuclear weapons and nuclear power are different things.",
        "Chernobyl still shapes how people see reactors",
        "Iran restarts the Bushehr nuclear power plant after repairs",
        "China approves ten new reactors to cut coal use",
        "The Race for Nuclear Fusion Is Heating Up #China #CleanEnergy",
        "Treated water release from Fukushima Daiichi begins",
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
        ("Iran’s Araghchi Meets Qatari Mediators Amid US Nuclear Stance", "geopolitics"),
        ("Iran Pressed to Make Nuclear Concessions to Revive Peace Talks With U.S.", "geopolitics"),
        (
            "Trump suggests an endgame regarding Iran, stating 'Let them hit us with a nuclear weapon'",
            "weapons+geopolitics",
        ),
        ("A nuclear war would end civilization.", "weapons"),
        ("She works in nuclear medicine at the hospital.", "medicine"),
        ("Great weather today", "no_keyword"),
        ("jazz fusion night downtown", "no_keyword"),
        ("Fires spread through Pacific Palisades overnight", "no_keyword"),
        ("Umineko Shouten In-store, Fukushima, Japan #Japan", "no_keyword"),
        ("NATO condemned the nuclear rhetoric from Russia over Kaliningrad", "weapons+geopolitics"),
        ("China expands its nuclear stockpile, the Pentagon says", "geopolitics"),
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
    assert not is_english("福島の旅館・リゾート、10月3連休の予約 #fukushima #nuclear", declared="en")


def test_context_relevant_only_needs_english():
    assert classify_relevance("Great video, thanks!", context_relevant=True).status == RELEVANT
    assert classify_relevance("", context_relevant=True).status == EXCLUDED


@pytest.mark.parametrize(
    "text",
    [
        "<think> The post is about a startup wanting to build a nuclear-powered data center in Utah.",
        "Nuclear power is great </think> Here is a reply you could post.",
        "<|im_start|>assistant Nuclear energy is safe.",
    ],
)
def test_machine_output_is_never_scored(text):
    assert classify_relevance(text, lang="en") == Relevance(EXCLUDED, "machine_output")
    assert classify_relevance(text, context_relevant=True) == Relevance(EXCLUDED, "machine_output")


def test_thinking_about_nuclear_is_still_a_person():
    assert classify_relevance("I think nuclear power is underrated.", lang="en").status == RELEVANT


# Sentences from real Guardian articles that leaked into the scores in September 2026.
OFF_TOPIC_ARTICLES = [
    (
        "Alexander Zverev clinches Laver Cup for Team Europe with victory over Learner Tien",
        "At 10-11, he responded with a successful drop shot and lob combination, a nuclear forehand and "
        "then another winning drop shot to clinch the final three points of the match.",
    ),
    (
        "Heavy metal is about uplifting the downtrodden. So why is alleged abuse by Marilyn Manson so easily "
        "forgotten?",
        "In November, Nuclear Blast Records, the same label to which Manson signed in 2024, will release "
        "a new album by Anselmo's other group, Down.",
    ),
    (
        "Digger review - Tom Cruise's loudmouth oil tycoon goes hard in Alejandro G Iñárritu's eco-satire",
        "He also angrily says that moving over to renewables, or nuclear, is simply not viable.",
    ),
]


@pytest.mark.parametrize(("title", "sentence"), OFF_TOPIC_ARTICLES)
def test_article_sentences_need_an_article_about_energy(title, sentence):
    assert classify_relevance(sentence, lang="en").status == RELEVANT  # alone, the sentence looks fine
    [result] = classify_article_sentences([sentence], title=title, standfirst=None)
    assert result == Relevance(EXCLUDED, "off_topic_article")


def test_geopolitical_articles_keep_only_energy_sentences():
    sentences = [
        "The initial steps would take four to five days, and talks on the nuclear programme would start "
        "on the seventh day, he said.",
        "Iran's Bushehr nuclear power plant was not affected, the agency said.",
    ]
    results = classify_article_sentences(
        sentences,
        title="Trump rejects Iran's seven-day peace deal to reopen strait of Hormuz",
        standfirst="US president is said to expect renewed strikes after the midterms",
    )
    assert results == [Relevance(EXCLUDED, "geopolitics"), Relevance(RELEVANT)]


@pytest.mark.parametrize(
    ("title", "sentences"),
    [
        (
            "New UK gas and oil projects are a 'no-brainer', says EDF boss",
            [
                "EDF Energy has about 8 gigawatts of low-carbon capacity in the UK, including eight "
                "nuclear power plants.",
                "It is building the much-delayed Hinkley Point C nuclear power station in Somerset.",
            ],
        ),
        (
            "Burnham's electricity grid idea is interesting - but it's not 'public control'",
            ["A chunk has already been raided to back small modular nuclear reactors."],
        ),
        (
            "Poland signs its first nuclear power plant contract",
            ["Nuclear is the only way to quit coal, he said."],
        ),
    ],
)
def test_energy_articles_keep_their_nuclear_sentences(title, sentences):
    results = classify_article_sentences(sentences, title=title, standfirst=None)
    assert all(r.status == RELEVANT for r in results)


def test_article_context_reads_the_headline_and_every_sentence():
    assert article_context("Reactor restarts in Michigan", None, []).about_energy
    assert article_context("Budget news", "A standfirst", ["A new nuclear plant opens."]).about_energy
    assert not article_context("Budget news", None, ["A nuclear forehand won it."]).about_energy
    assert article_context("Iran talks stall", None, []).geopolitical
    assert not article_context("Iran restarts its Bushehr nuclear power plant", None, []).geopolitical


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
