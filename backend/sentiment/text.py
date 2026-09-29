"""Text cleanup, sentence splitting, language checks, and nuclear-energy relevance rules.

The sentiment model was trained on nuclear-energy discourse.
Keyword search for "nuclear" also returns idioms ("the nuclear option"), weapons, and geopolitics,
and scoring those would quietly corrupt the trend, so every segment is classified here first.
Excluded segments are still stored (with a reason) so the rules can be audited and tuned.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Cleanup


_BLOCK_TAGS = re.compile(r"<\s*(br|/p|/div|/li|/h[1-6])\s*/?>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t ]+")
_NEWLINES = re.compile(r"\s*\n\s*")


def strip_html(value: str) -> str:
    """Turn Mastodon/YouTube HTML into plain text, keeping line breaks between blocks."""
    text = _BLOCK_TAGS.sub("\n", value)
    text = _TAGS.sub("", text)
    return normalize(html.unescape(text))


def normalize(value: str) -> str:
    text = _WS.sub(" ", value.replace("\r", ""))
    text = _NEWLINES.sub("\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Sentences

# Abbreviations that end with a period but do not end a sentence.
_ABBREV = (
    "mr|mrs|ms|dr|prof|sr|jr|st|mt|vs|etc|inc|ltd|co|corp|gov|sen|rep|gen|col|lt|sgt|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|no|approx|u\\.s|u\\.k|e\\.g|i\\.e"
)
_SENTENCE_BREAK = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"')\]]))\s+(?=[\"'(\[]?[A-Z0-9])")


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph in normalize(text).split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # Split permissively, then re-join breaks that follow an abbreviation or an initial.
        parts = _SENTENCE_BREAK.split(paragraph)
        buffer = ""
        for part in parts:
            buffer = f"{buffer} {part}".strip() if buffer else part
            if not re.search(rf"\b(?:{_ABBREV})\.$", buffer, re.IGNORECASE) and not re.search(
                r"\b[A-Z]\.$", buffer
            ):
                sentences.append(buffer)
                buffer = ""
        if buffer:
            sentences.append(buffer)
    return sentences


# ---------------------------------------------------------------------------
# Language

_EN_STOPWORDS = frozenset(
    "the a an and or but of to in on for with is are was were be been it this that these "
    "those i you he she we they my your our their not no so if at by from as about just have "
    "has had do does did will would can could should what which who how why when there here "
    "more than".split()
)
# Common function words of the other languages that show up most in nuclear hashtags.
_FOREIGN_STOPWORDS = (
    frozenset(
        "der die das und ist nicht ein eine mit für auf auch sich uns wir ich zu den dem des von "
        "le la les et est une des du pour pas que qui dans sur au avec ce il elle nous el los las "
        "es y en por con para una del al lo se su muy pero como il lo gli di che è per non sono "
        "della o os um uma não com mais são het een van en niet dat zijn voor met ook".split()
    )
    - _EN_STOPWORDS
)
_WORD = re.compile(r"[A-Za-zÀ-ɏ']+")


def mostly_non_latin(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) < 0.6


def is_english(text: str, declared: str | None = None) -> bool:
    """Trust a declared language tag when there is one; otherwise use a function-word heuristic.

    Text that is mostly in a non-Latin script is never English, whatever its tag says
    (bots and cross-posters often tag everything "en").
    """
    if mostly_non_latin(text):
        return False
    letters = [c for c in text if c.isalpha()]
    if declared:
        return declared.lower().split("-")[0].split("_")[0] == "en"
    words = [w.lower() for w in _WORD.findall(text)]
    if not words:
        return False
    english = sum(w in _EN_STOPWORDS for w in words)
    foreign = sum(w in _FOREIGN_STOPWORDS for w in words)
    if foreign > english:
        return False
    if english / len(words) >= 0.12:
        return True
    # Few function words at all: accept short Latin-script text such as headlines and hashtags.
    return len(words) <= 12 and sum(c.isascii() for c in letters) / len(letters) > 0.97


# ---------------------------------------------------------------------------
# Relevance

# Terms that on their own anchor a text to nuclear energy.
_ANCHORS = re.compile(
    r"""
    \bnuclear\b
    | \#?\bnuclear(?:power|energy|plants?|fusion|fission|waste|reactors?|industry|renaissance|now)\b
    | \#(?:fission|fusionenergy|fusionpower|smrs?|uranium|atomkraft|kernenergie|nucleaire)\b
    | \bnuke\s+plants?\b
    | \b(?:fission|uranium|thorium|plutonium|tritium)\b
    | \breactors?\b
    | \bsmall\s+modular\s+reactors?\b
    | (?-i:\bSMRs?\b)
    | \b(?:nuclear\s+)?fusion\s+(?:energy|power|reactors?|plants?|research|start-?ups?)\b
    | \btokamaks?\b | \bstellarators?\b
    | \bspent\s+fuel\b | \bradioactive\s+waste\b | \byucca\s+mountain\b
    | \bchernobyl\b | \bthree\s+mile\s+island\b
    | \bfukushima\s+(?:daiichi|nuclear|disaster|plant|reactors?|meltdown|accident|radiation|
                       treated\s+water|wastewater)\b
    | \bzaporizhzhia\s+(?:nuclear|plant|npp|power|reactors?)\b
    | \bdiablo\s+canyon\b | \bvogtle\b
    | \b(?:palisades|indian\s+point)\s+(?:nuclear|plant|reactors?|power|restart)\b
    | \batomic\s+energy\b | \batomkraft\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Spans removed before re-checking for an anchor. If nothing is left, the segment is excluded.
_EXCLUSIONS: list[tuple[str, re.Pattern[str]]] = [
    (
        "idiom",
        re.compile(
            r"\b(?:the\s+)?nuclear\s+options?\b"
            r"|\b(?:go(?:es|ing)?|went|gone)\s+(?:full\s+)?nuclear\b"
            r"|\bnuclear\s+famil(?:y|ies)\b"
            r"|\bnuclear\s+(?:winter|football|codes?|holocaust|meltdown\s+of\s+the)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "weapons",
        re.compile(
            r"\b(?:non-?)?nuclear[-\s]+(?:weapons?|bombs?|war(?:fare|s)?|warheads?|missiles?|arsenals?|"
            r"strikes?|attacks?|submarines?|deterren(?:ce|t)s?|tests?|testing|threats?|"
            r"(?:non-?)?proliferation|disarmament|armed|capable|blackmail|escalation|"
            r"annihilation|apocalypse|armageddon|triad|umbrella|posture|doctrine|rhetoric|saber-?rattling|"
            r"sabre-?rattling|forces|powers|states?|club)\b"
            r"|\bnukes?\b(?!\s+plants?)"
            r"|\bnuclear\s+(?:program(?:me)?s?|deal|talks|negotiations|ambitions|sites?|facilities|"
            r"enrichment)\b(?=[^.]*\b(?:iran|tehran|north\s+korea|pyongyang|kim\s+jong)\b)"
            r"|\b(?:iran|tehran|north\s+korea|pyongyang)(?:'s)?\s+nuclear\s+\w+",
            re.IGNORECASE,
        ),
    ),
    (
        "medicine",
        re.compile(
            r"\bnuclear\s+(?:medicine|magnetic\s+resonance|imaging|scans?|stress\s+tests?|cardiology)\b"
            r"|\bnuclear\s+(?:membranes?|envelope|receptors?|pores?|dna|genome)\b",
            re.IGNORECASE,
        ),
    ),
]

# In texts about these actors, a bare "nuclear" almost always means weapons or diplomacy;
# only energy-specific terms keep such a text relevant.
_GEOPOLITICS = re.compile(
    r"\b(?:iran|iranian|tehran|north\s+korea|north\s+korean|pyongyang|kim\s+jong|hezbollah|hormuz|"
    r"russia|russian|kremlin|putin|moscow|nato|pentagon|israel|israeli|china|chinese|pakistan|india)\b",
    re.IGNORECASE,
)
# Energy-specific terms that keep a geopolitical text relevant (such as Zaporizhzhia or Bushehr coverage).
_ENERGY_ANCHORS = re.compile(
    r"\bnuclear[-\s]+(?:power|energy|electricity|plants?|reactors?|stations?|industry|generation|fuel)\b"
    r"|\bpower\s+(?:plants?|stations?)\b|\breactors?\b|\bnuclear(?:power|energy|fusion)\b"
    r"|\b(?:nuclear\s+)?fusion\s+(?:energy|power|reactors?|plants?|research)\b|\bnuclear\s+fusion\b"
    r"|\bfission\b|\bsmall\s+modular\b|(?-i:\bSMRs?\b)",
    re.IGNORECASE,
)

RELEVANT = "relevant"
EXCLUDED = "excluded"
NON_ENGLISH = "non_english"


@dataclass(frozen=True, slots=True)
class Relevance:
    status: str
    reason: str | None = None


def has_anchor(text: str) -> bool:
    return bool(_ANCHORS.search(text))


def classify_relevance(text: str, *, lang: str | None = None, context_relevant: bool = False) -> Relevance:
    """Decide whether a segment should be scored.

    `context_relevant` is for texts whose topic comes from their parent, such as a YouTube
    comment on a nuclear-energy video: they only need to be English.
    """
    if not text.strip():
        return Relevance(EXCLUDED, "empty")
    if not is_english(text, lang):
        return Relevance(NON_ENGLISH, "script" if mostly_non_latin(text) else lang or "heuristic")
    if context_relevant:
        return Relevance(RELEVANT)
    text = text.replace("\u2019", "'")
    if not has_anchor(text):
        return Relevance(EXCLUDED, "no_keyword")
    remaining = text
    reasons: list[str] = []
    for reason, pattern in _EXCLUSIONS:
        remaining, count = pattern.subn(" ", remaining)
        if count:
            reasons.append(reason)
    if _GEOPOLITICS.search(remaining) and not _ENERGY_ANCHORS.search(remaining):
        return Relevance(EXCLUDED, "+".join([*reasons, "geopolitics"]))
    if has_anchor(remaining):
        return Relevance(RELEVANT)
    return Relevance(EXCLUDED, "+".join(reasons) or "no_keyword")


def nuclear_sentences(body: str) -> list[str]:
    """Sentences of an article that mention a nuclear anchor term (relevant or not)."""
    return [s for s in split_sentences(body) if has_anchor(s)]
