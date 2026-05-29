"""Test unitari per il semantic chunker."""
from __future__ import annotations

import pytest

from cci_ingestion.extractors.chunker import TextChunk, chunk_text


class TestChunkText:
    def test_single_short_paragraph(self) -> None:
        text = "Questo è un testo breve."
        chunks = chunk_text(text, max_tokens=512)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_multiple_paragraphs(self) -> None:
        text = "Primo paragrafo.\n\nSecondo paragrafo.\n\nTerzo paragrafo."
        chunks = chunk_text(text, max_tokens=512)
        assert len(chunks) >= 1

    def test_long_text_is_split(self) -> None:
        # ~600 token (2400 chars)
        long_para = ("word " * 480).strip()
        chunks = chunk_text(long_para, max_tokens=512)
        assert len(chunks) > 1, "Il testo lungo dovrebbe essere spezzato"

    def test_chunk_indices_are_sequential(self) -> None:
        text = "\n\n".join([f"Paragrafo {i}." for i in range(10)])
        chunks = chunk_text(text, max_tokens=512)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_overlap_adds_context(self) -> None:
        text = "Prima parte.\n\nSeconda parte con contenuto aggiuntivo."
        chunks = chunk_text(text, max_tokens=512, overlap_tokens=10)
        if len(chunks) > 1:
            # Il secondo chunk deve contenere parte del primo
            assert len(chunks[1].text) > len("Seconda parte con contenuto aggiuntivo.")

    def test_empty_text(self) -> None:
        chunks = chunk_text("", max_tokens=512)
        assert chunks == []

    def test_token_estimate_positive(self) -> None:
        text = "Testo di esempio con alcune parole."
        chunks = chunk_text(text)
        for chunk in chunks:
            assert chunk.token_estimate > 0

    def test_returns_text_chunks(self) -> None:
        text = "Un paragrafo.\n\nUn altro."
        chunks = chunk_text(text)
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_max_tokens_respected(self) -> None:
        # Crea un testo con molte frasi brevi separate da punti
        sentences = ". ".join([f"Frase numero {i} di test" for i in range(100)])
        chunks = chunk_text(sentences, max_tokens=100)
        for chunk in chunks:
            assert chunk.token_estimate <= 200  # tolleranza overlap
