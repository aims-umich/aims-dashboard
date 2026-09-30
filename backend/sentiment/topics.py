"""Topic tags for scored text: plain keyword rules, so anyone can check why a text landed in a topic.

A text can carry several topics or none. Rules run after relevance filtering, so weapons, medicine,
and idioms never reach them. Tags are stored on each segment (`segments.topics`) at ingest time;
after changing a rule, run `sentiment topics` to re-apply the rules to stored segments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Topic:
    id: str
    name: str
    # The terms shown on the site, in the same order as the pattern.
    keywords: tuple[str, ...]
    pattern: re.Pattern[str]


def _rule(*case_insensitive: str, exact: tuple[str, ...] = ()) -> re.Pattern[str]:
    """Match any term; `exact` terms are case-sensitive acronyms such as "AI" or "NRC"."""
    parts = [rf"\b(?:{term})" for term in case_insensitive]
    parts += [rf"(?-i:\b{term}\b)" for term in exact]
    return re.compile("|".join(parts), re.IGNORECASE)


TOPICS: tuple[Topic, ...] = (
    Topic(
        "data-centers",
        "Data centers and AI power",
        ("data center", "AI", "hyperscaler", "Microsoft", "Google", "Amazon", "Meta", "compute"),
        _rule(
            r"data\s*cent(?:er|re)s?\b",
            r"datacent(?:er|re)s?\b",
            r"artificial intelligence\b",
            r"hyperscalers?\b",
            r"microsoft\b",
            r"google\b",
            r"amazon\b",
            r"compute\b",
            exact=("AI", "Meta"),
        ),
    ),
    Topic(
        "advanced-reactors",
        "Advanced reactors and SMRs",
        (
            "SMR",
            "small modular",
            "microreactor",
            "advanced reactor",
            "NuScale",
            "TerraPower",
            "X-energy",
            "Kairos",
        ),
        _rule(
            r"small\s+modular\b",
            r"micro-?reactors?\b",
            r"advanced\s+(?:nuclear\s+)?reactors?\b",
            r"nuscale\b",
            r"terrapower\b",
            r"x-energy\b",
            r"kairos\b",
            r"natrium\b",
            r"oklo\b",
            r"valar\b",
            r"#smrs?\b",
            exact=("SMRs?",),
        ),
    ),
    Topic(
        "policy",
        "Policy and politics",
        ("Congress", "executive order", "NRC", "regulator", "subsidy", "DOE", "license", "administration"),
        _rule(
            r"congress\b",
            r"senat(?:e|or)s?\b",
            r"executive\s+orders?\b",
            r"regulat(?:or|ors|ory|ion|ions|ed)\b",
            r"subsid(?:y|ies|ize|ise)\b",
            r"licen[cs](?:e|es|ed|ing)\b",
            r"legislat(?:ion|ure|ors?)\b",
            r"parliament\b",
            r"ministers?\b",
            r"administration\b",
            r"governments?\b",
            r"trump\b",
            r"biden\b",
            exact=("NRC", "DOE", "IRA"),
        ),
    ),
    Topic(
        "safety",
        "Safety and accidents",
        (
            "Chernobyl",
            "Fukushima",
            "Three Mile Island",
            "Zaporizhzhia",
            "meltdown",
            "leak",
            "accident",
            "radiation",
        ),
        _rule(
            r"chernobyl\b",
            r"fukushima\b",
            r"three\s+mile\s+island\b",
            r"zaporizhzhia\b",
            r"meltdowns?\b",
            r"leak(?:s|ed|ing)?\b",
            r"accidents?\b",
            r"disasters?\b",
            r"evacuat(?:e|ed|ion)\b",
            r"radiation\b",
            r"safety\b",
            r"safe\b",
        ),
    ),
    Topic(
        "waste",
        "Waste and storage",
        ("nuclear waste", "spent fuel", "repository", "Yucca", "Onkalo", "cask", "disposal"),
        _rule(
            r"waste\b",
            r"spent\s+fuel\b",
            r"repositor(?:y|ies)\b",
            r"yucca\b",
            r"onkalo\b",
            r"(?:dry\s+)?casks?\b",
            r"disposal\b",
        ),
    ),
    Topic(
        "fusion",
        "Fusion",
        ("fusion", "tokamak", "stellarator", "ITER", "NIF", "ignition", "Helion", "Commonwealth Fusion"),
        _rule(
            r"fusion\b", r"tokamaks?\b", r"stellarators?\b", r"ignition\b", r"helion\b", exact=("ITER", "NIF")
        ),
    ),
    Topic(
        "cost",
        "Cost and finance",
        ("cost", "overrun", "billion", "investors", "financing", "ratepayers", "taxpayers", "price"),
        _rule(
            r"costs?\b",
            r"costly\b",
            r"overruns?\b",
            r"billions?\b",
            r"investors?\b",
            r"investments?\b",
            r"financ(?:e|ing|ial)\b",
            r"ratepayers?\b",
            r"taxpayers?\b",
            r"loans?\b",
            r"expensive\b",
            r"prices?\b",
            r"afford(?:able|ability)\b",
            r"money\b",
        ),
    ),
    Topic(
        "fuel",
        "Uranium and fuel",
        ("uranium", "enrichment", "HALEU", "fuel", "mining", "thorium"),
        _rule(
            r"uranium\b",
            r"enrich(?:ment|ed)\b",
            r"(?<!fossil\s)fuels?\b",
            r"mining\b",
            r"yellowcake\b",
            r"centrus\b",
            r"cameco\b",
            r"thorium\b",
            exact=("HALEU",),
        ),
    ),
    Topic(
        "climate",
        "Climate and emissions",
        ("climate", "emissions", "net zero", "carbon-free", "decarbonize", "clean energy", "fossil fuels"),
        _rule(
            r"climate\b",
            r"emissions?\b",
            r"net[-\s]zero\b",
            r"carbon\b",
            r"decarboni[sz](?:e|ed|ing|ation)\b",
            r"clean\s+(?:energy|power|electricity)\b",
            r"low-carbon\b",
            r"fossil\b",
            r"coal\b",
            r"renewables?\b",
        ),
    ),
)

TOPICS_BY_ID: dict[str, Topic] = {topic.id: topic for topic in TOPICS}


def topics_for(text: str) -> list[str]:
    """Ids of every topic whose rule matches the text, in the fixed topic order."""
    text = text.replace("\u2019", "'")
    return [topic.id for topic in TOPICS if topic.pattern.search(text)]
