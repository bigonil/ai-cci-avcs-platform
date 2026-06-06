"""Citation enforcement for LLM outputs — R3 guardrail.

Every sentence in a grounded output that contains a factual claim (number,
date, entity name, amount) MUST carry at least one [source: chunk_id] citation.

Citation format: [source: chunk_id]
Example: "Il commitment Azure ammonta a 580.000 EUR [source: chunk_azure_ea_2026]."
"""
from __future__ import annotations

import re

import structlog

from cci_llm.models import CitationResult

log = structlog.get_logger(__name__)

# Matches [source: anything] — chunk_id can contain alphanumeric, - and _
_CITATION_RE = re.compile(r"\[source:\s*([A-Za-z0-9_\-]+)\]")

# Common Italian/international corporate abbreviations whose period should NOT
# trigger a sentence split (e.g. "S.p.A.", "s.r.l.", "Dr.", "Nr.").
_ABBREV_PLACEHOLDER = "\x00ABBREV\x00"
_ABBREV_RE = re.compile(
    r"\b(?:[A-Za-z]\.){2,}"   # multi-part abbreviations: S.p.A., s.r.l., U.S.A., etc.
    r"|\b(?:Dr|Mr|Mrs|Nr|Art|artt|cfr|ibid|op)\."  # single-word abbreviations
)

# Sentence splitter: split after . ? ! followed by whitespace, OR on bare newlines
_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+|\n+")

# Signals that a sentence contains a factual claim worth enforcing.
# The negative lookbehind (?<![A-Za-z_]) prevents matching digits inside
# identifiers like "R001", "chunk_123", "C001", etc.
_FACTUAL_SIGNAL_RE = re.compile(
    r"((?<![A-Za-z0-9_])\d[\d.,]*"  # numeric value NOT inside an identifier (e.g. not R001, chunk_123)
    r"|\d{4}-\d{2}-\d{2}"           # ISO date (e.g. 2026-03-31)
    r"|EUR|€"                        # currency
    r"|%)"                           # percentage
)


class GroundingError(ValueError):
    """Raised in strict mode when LLM output lacks required citations."""


def enforce_citations(
    text: str,
    strict: bool = True,
    min_sentence_length: int = 20,
) -> CitationResult:
    """Check and extract citations from LLM-generated text.

    In strict mode raises GroundingError if any factual sentence lacks citations.
    Outside of tests, strict must always be True (CLAUDE.md §6 anti-patterns).
    """
    # Temporarily replace abbreviation periods so they don't cause false splits
    protected = _ABBREV_RE.sub(lambda m: m.group().replace(".", _ABBREV_PLACEHOLDER), text.strip())
    raw_sentences = _SENTENCE_RE.split(protected)
    sentences = [s.replace(_ABBREV_PLACEHOLDER, ".") for s in raw_sentences]

    all_citations: list[str] = []
    sentences_without: list[str] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < min_sentence_length:
            continue

        # Extract any citations present in this sentence
        found = _CITATION_RE.findall(sentence)
        all_citations.extend(found)

        # Check if the sentence has factual content but no citation
        if _FACTUAL_SIGNAL_RE.search(sentence) and not found:
            sentences_without.append(sentence)

    is_grounded = len(sentences_without) == 0

    if not is_grounded and strict:
        log.warning(
            "grounding_violation",
            uncited_count=len(sentences_without),
            first_uncited=sentences_without[0][:120] if sentences_without else "",
        )
        raise GroundingError(
            f"R3 violation: {len(sentences_without)} sentence(s) with factual content "
            f"have no [source: chunk_id] citation.\n"
            f"First offender: {sentences_without[0][:200]}"
        )

    unique_citations = list(dict.fromkeys(all_citations))
    log.debug(
        "citation_check",
        total_citations=len(unique_citations),
        uncited_sentences=len(sentences_without),
        is_grounded=is_grounded,
    )
    return CitationResult(
        text=text,
        citations_found=unique_citations,
        sentences_without_citations=sentences_without,
        is_grounded=is_grounded,
    )


def extract_citations(text: str) -> list[str]:
    """Return all chunk_ids referenced in [source: X] patterns."""
    return list(dict.fromkeys(_CITATION_RE.findall(text)))
