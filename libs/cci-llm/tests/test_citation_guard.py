"""Tests for the citation enforcement guard — R3 guardrail."""
from __future__ import annotations

import pytest

from cci_llm.citation_guard import GroundingError, enforce_citations, extract_citations


class TestExtractCitations:
    def test_single_citation(self):
        text = "Il valore è 580.000 EUR [source: chunk_azure_001]."
        assert extract_citations(text) == ["chunk_azure_001"]

    def test_multiple_citations(self):
        text = (
            "Azure spende 580k [source: chunk_a]. "
            "AWS spende 190k [source: chunk_b]."
        )
        result = extract_citations(text)
        assert "chunk_a" in result
        assert "chunk_b" in result

    def test_no_citations(self):
        assert extract_citations("No citations here.") == []

    def test_deduplication(self):
        text = "Dato A [source: chunk_x]. Dato B [source: chunk_x]."
        assert extract_citations(text) == ["chunk_x"]

    def test_hyphen_in_chunk_id(self):
        text = "Valore [source: chunk-abc-123]."
        assert extract_citations(text) == ["chunk-abc-123"]


class TestEnforceCitations:
    def test_grounded_text_passes(self):
        text = (
            "Il commitment Azure è 580.000 EUR [source: chunk_azure_001]. "
            "La certificazione scade il 2026-03-31 [source: chunk_cert_002]."
        )
        result = enforce_citations(text, strict=True)
        assert result.is_grounded
        assert len(result.citations_found) == 2

    def test_uncited_factual_sentence_raises_in_strict(self):
        text = (
            "Il commitment è 580.000 EUR senza citazione. "
            "Altra frase normale senza numeri."
        )
        with pytest.raises(GroundingError):
            enforce_citations(text, strict=True)

    def test_uncited_returns_result_in_non_strict(self):
        text = "Il valore è 100 EUR senza citazione."
        result = enforce_citations(text, strict=False)
        assert not result.is_grounded
        assert len(result.sentences_without_citations) == 1

    def test_short_sentence_not_enforced(self):
        # Sentences shorter than min_sentence_length are skipped
        result = enforce_citations("OK.", strict=True, min_sentence_length=5)
        assert result.is_grounded

    def test_no_factual_content_passes(self):
        text = (
            "Il sistema verifica la coerenza finanziaria. "
            "L'analisi è stata completata con successo."
        )
        result = enforce_citations(text, strict=True)
        assert result.is_grounded

    def test_percentage_requires_citation(self):
        text = "Azure rappresenta il 67% del budget senza citazione."
        with pytest.raises(GroundingError):
            enforce_citations(text, strict=True)

    def test_citation_before_period_valid(self):
        text = "Il totale è 855.000 EUR [source: chunk_totale]. Fine."
        result = enforce_citations(text, strict=True)
        assert result.is_grounded

    def test_error_message_shows_offender(self):
        text = "Valore 500 EUR non citato qui."
        with pytest.raises(GroundingError, match="R3 violation"):
            enforce_citations(text, strict=True)
