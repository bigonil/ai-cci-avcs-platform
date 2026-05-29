"""Unit tests for the citation enforcer — R3 grounding guardrail."""
from __future__ import annotations

import pytest

from cci_retrieval.citation_enforcer import (
    CitationResult,
    GroundingError,
    check_citations,
    enforce_grounding,
)

_PATTERN = r"\[(?:source:\s*)?[a-zA-Z0-9_\-]{8,}\]"


class TestCheckCitations:
    def test_fully_cited_text(self) -> None:
        # Citations must appear BEFORE the period so the sentence splitter
        # keeps them in the same sentence as the claim they support.
        text = (
            "Azure commitment di 580.000 EUR supera il budget approvato di 500.000 EUR [source: chunk-001abc]. "
            "La certificazione ISO 27001 scade il 2026-03-31 ma il commitment copre l'intero anno [chunk-002xyz]."
        )
        result = check_citations(text, _PATTERN)
        assert result.valid is True
        assert result.uncited_sentences == []

    def test_uncited_sentence_detected(self) -> None:
        text = (
            "Azure commitment di 580.000 EUR supera il budget approvato di 500.000 EUR per il 2026. "
            "Questa frase non ha nessuna citazione e dovrebbe fallire la verifica di grounding."
        )
        result = check_citations(text, _PATTERN)
        assert result.valid is False
        assert len(result.uncited_sentences) >= 1

    def test_short_sentences_skipped(self) -> None:
        # "OK." is 3 chars — below min_sentence_length of 40, should be skipped
        text = "OK. Azure overspend detected. [source: chunk-abc123de]"
        result = check_citations(text, _PATTERN, min_sentence_length=40)
        # Only sentence >= 40 chars is checked; "Azure overspend detected." is 25 chars → skipped
        # So no qualifying sentences → valid=True (vacuously)
        assert result.total_checked == 0
        assert result.valid is True

    def test_empty_text(self) -> None:
        result = check_citations("", _PATTERN)
        assert result.valid is True
        assert result.total_checked == 0

    def test_coverage_calculation(self) -> None:
        text = (
            "Prima frase con citation e contenuto sufficiente per superare la soglia. [source: chunk-abc123de] "
            "Seconda frase senza nessuna citation che dovrebbe far fallire la verifica di grounding totale."
        )
        result = check_citations(text, _PATTERN, min_sentence_length=20)
        assert result.total_checked == 2
        assert result.coverage == 0.5

    def test_multiple_citation_formats(self) -> None:
        text1 = "Azure overspend rilevato come da policy finanziaria per il cloud 2026 [source: chunk-abc12345]."
        text2 = "Azure overspend rilevato come da policy finanziaria per il cloud 2026 [chunk-abc12345]."
        assert check_citations(text1, _PATTERN).valid is True
        assert check_citations(text2, _PATTERN).valid is True

    def test_citation_too_short_rejected(self) -> None:
        # chunk IDs must be >= 8 chars in the pattern
        text = (
            "Azure overspend rilevato come da policy finanziaria per il cloud 2026. [c1]"
        )
        result = check_citations(text, _PATTERN, min_sentence_length=20)
        assert result.valid is False


class TestEnforceGrounding:
    def test_strict_raises_on_violation(self) -> None:
        bad_text = (
            "Questa affermazione non ha nessuna citazione e il testo è sufficientemente lungo da essere verificato. "
            "Anche questa seconda frase è priva di qualsiasi riferimento a chunk del corpus."
        )
        with pytest.raises(GroundingError):
            enforce_grounding(bad_text, strict=True)

    def test_strict_false_returns_result(self) -> None:
        bad_text = (
            "Testo senza citation che supera la soglia minima per la verifica del grounding imposto da R3."
        )
        # strict=False — only allowed in tests (CLAUDE.md anti-pattern when used in prod)
        result = enforce_grounding(bad_text, strict=False)
        assert result.valid is False

    def test_valid_text_does_not_raise(self) -> None:
        text = (
            "Il commitment Azure di 580.000 EUR supera l'allocation CTO approvata di 500.000 EUR [source: chunk-abc12345]."
        )
        result = enforce_grounding(text, strict=True)
        assert result.valid is True
