"""Citation enforcer — R3 grounding guardrail.

CLAUDE.md R3: every sentence in LLM output destined for the user MUST contain
at least one citation reference [source: chunk_id] or [chunk_id].

The enforcer:
  1. Splits text into sentences (regex-based, no NLTK dependency).
  2. Skips sentences shorter than `min_sentence_length` (headers, bullets, etc.).
  3. Checks each qualifying sentence for the configured citation pattern.
  4. Returns `CitationResult` with `valid` flag and list of uncited sentences.

The upstream caller (Generator agent) MUST re-invoke with a reinforced prompt
when `valid=False`. Calling `enforce_grounding(..., strict=True)` raises if invalid.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class CitationResult:
    valid: bool
    uncited_sentences: list[str] = field(default_factory=list)
    total_checked: int = 0
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def coverage(self) -> float:
        if self.total_checked == 0:
            return 1.0
        cited = self.total_checked - len(self.uncited_sentences)
        return cited / self.total_checked


# Sentence splitter: split on . ? ! followed by whitespace or end-of-string
_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def check_citations(
    text: str,
    citation_pattern: str = r"\[(?:source:\s*)?[a-zA-Z0-9_\-]{8,}\]",
    min_sentence_length: int = 40,
) -> CitationResult:
    """Check every qualifying sentence for at least one citation reference.

    Args:
        text: LLM-generated output string.
        citation_pattern: Regex that matches a valid citation token.
        min_sentence_length: Sentences shorter than this are skipped (e.g., headers).

    Returns:
        CitationResult with valid=True only if all qualifying sentences are cited.
    """
    compiled = re.compile(citation_pattern)
    sentences = _split_sentences(text)
    qualifying = [s for s in sentences if len(s) >= min_sentence_length]
    uncited = [s for s in qualifying if not compiled.search(s)]
    return CitationResult(
        valid=len(uncited) == 0,
        uncited_sentences=uncited,
        total_checked=len(qualifying),
    )


def enforce_grounding(
    text: str,
    citation_pattern: str = r"\[(?:source:\s*)?[a-zA-Z0-9_\-]{8,}\]",
    min_sentence_length: int = 40,
    strict: bool = True,
) -> CitationResult:
    """Enforce grounding. Raises `GroundingError` when strict=True and output is invalid.

    NOTE: `strict=False` is only allowed in test code (CLAUDE.md anti-pattern list).
    """
    result = check_citations(text, citation_pattern, min_sentence_length)
    if not result.valid and strict:
        raise GroundingError(
            f"Grounding violation: {len(result.uncited_sentences)} uncited sentence(s). "
            f"Coverage: {result.coverage:.0%}. "
            f"First violation: '{result.uncited_sentences[0][:120]}'"
        )
    return result


class GroundingError(ValueError):
    """Raised when LLM output fails citation enforcement in strict mode."""
