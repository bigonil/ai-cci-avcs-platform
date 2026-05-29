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

# Sentence splitter: split after . ? ! followed by whitespace or end-of-string
_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")

# Signals that a sentence contains a factual claim worth enforcing
_FACTUAL_SIGNAL_RE = re.compile(
    r"(\d[\d.,]*"            # numeric value
    r"|\d{4}-\d{2}-\d{2}"   # ISO date
    r"|EUR|€"                # currency
    r"|%)"                   # percentage
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
    sentences = _SENTENCE_RE.split(text.strip())
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
