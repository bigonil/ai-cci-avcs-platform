"""Semantic chunker — divide il testo in chunk logici (NON sliding window).

Strategia: paragrafi logici delimitati da doppio newline, con merge dei
paragrafi troppo brevi e split di quelli troppo lunghi (> max_tokens).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from cci_common.observability import get_logger

logger = get_logger(__name__)

_AVG_CHARS_PER_TOKEN = 4  # stima conservativa per italiano/inglese


@dataclass(frozen=True)
class TextChunk:
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    token_estimate: int


def chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[TextChunk]:
    """Divide il testo in chunk semantici basati su paragrafi logici.

    1. Separa per doppio newline (paragrafi naturali)
    2. Unisce paragrafi troppo corti (< 50 token) con il successivo
    3. Spezza paragrafi troppo lunghi (> max_tokens) su confini di frase
    4. Aggiunge overlap token tra chunk consecutivi per continuità RAG
    """
    paragraphs = _split_paragraphs(text)
    merged = _merge_short_paragraphs(paragraphs, min_tokens=50)
    raw_chunks = _split_long_paragraphs(merged, max_tokens)
    chunks = _apply_overlap(raw_chunks, overlap_tokens)

    logger.info(
        "chunking_complete",
        total_chunks=len(chunks),
        avg_tokens=sum(c.token_estimate for c in chunks) // max(len(chunks), 1),
    )
    return chunks


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n{2,}", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _merge_short_paragraphs(paragraphs: list[str], min_tokens: int) -> list[str]:
    merged: list[str] = []
    buffer = ""
    for para in paragraphs:
        if buffer:
            candidate = f"{buffer}\n\n{para}"
            if _token_estimate(buffer) < min_tokens:
                buffer = candidate
                continue
            else:
                merged.append(buffer)
                buffer = para
        else:
            buffer = para
    if buffer:
        merged.append(buffer)
    return merged


def _split_long_paragraphs(paragraphs: list[str], max_tokens: int) -> list[str]:
    result: list[str] = []
    for para in paragraphs:
        if _token_estimate(para) <= max_tokens:
            result.append(para)
        else:
            # Spezza su confini di frase (. ! ?)
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current = ""
            for sent in sentences:
                candidate = f"{current} {sent}".strip() if current else sent
                if _token_estimate(candidate) <= max_tokens:
                    current = candidate
                else:
                    if current:
                        result.append(current)
                    current = sent
            if current:
                result.append(current)
    return result


def _apply_overlap(chunks: list[str], overlap_tokens: int) -> list[TextChunk]:
    result: list[TextChunk] = []
    overlap_chars = overlap_tokens * _AVG_CHARS_PER_TOKEN
    char_pos = 0

    for i, chunk_text_str in enumerate(chunks):
        # Aggiunge il tail del chunk precedente come contesto di overlap
        if i > 0 and overlap_chars > 0:
            prev = chunks[i - 1]
            tail = prev[-overlap_chars:] if len(prev) > overlap_chars else prev
            chunk_with_overlap = f"{tail}\n{chunk_text_str}"
        else:
            chunk_with_overlap = chunk_text_str

        end_pos = char_pos + len(chunk_text_str)
        result.append(
            TextChunk(
                text=chunk_with_overlap,
                chunk_index=i,
                char_start=char_pos,
                char_end=end_pos,
                token_estimate=_token_estimate(chunk_with_overlap),
            )
        )
        char_pos = end_pos

    return result


def _token_estimate(text: str) -> int:
    return max(1, len(text) // _AVG_CHARS_PER_TOKEN)
