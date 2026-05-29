"""Document parser — estrae testo grezzo da PDF, DOCX, XLSX, HTML, EML.

Usa Unstructured.io come backend primario con fallback Tesseract OCR.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from cci_common.observability import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    metadata: dict[str, object]
    source_type: str
    page_count: int


def parse_document(content: bytes, filename: str) -> ParsedDocument:
    """Estrae il testo da un documento binario.

    Tenta Unstructured.io; se non disponibile o fallisce, ritorna testo grezzo
    per file di testo puro (.txt, .md) o solleva ValueError.
    """
    suffix = Path(filename).suffix.lower()
    source_type = _detect_source_type(suffix)

    try:
        return _parse_with_unstructured(content, filename, source_type)
    except ImportError:
        logger.warning("unstructured_not_installed", filename=filename)
        return _parse_fallback(content, filename, source_type)
    except Exception as exc:
        logger.error("parse_failed", filename=filename, error=str(exc))
        raise ValueError(f"Impossibile parsare {filename}: {exc}") from exc


def _parse_with_unstructured(
    content: bytes, filename: str, source_type: str
) -> ParsedDocument:
    from unstructured.partition.auto import partition  # type: ignore[import-untyped]

    elements = partition(file=io.BytesIO(content), metadata_filename=filename)
    text_parts = [el.text for el in elements if hasattr(el, "text") and el.text]
    full_text = "\n\n".join(text_parts)

    page_numbers: list[int] = []
    for el in elements:
        pn = getattr(getattr(el, "metadata", None), "page_number", None)
        if pn is not None:
            page_numbers.append(pn)

    page_count = max(page_numbers) if page_numbers else 1

    return ParsedDocument(
        text=full_text,
        metadata={
            "filename": filename,
            "element_count": len(elements),
        },
        source_type=source_type,
        page_count=page_count,
    )


def _parse_fallback(
    content: bytes, filename: str, source_type: str
) -> ParsedDocument:
    if source_type in ("txt", "md"):
        text = content.decode("utf-8", errors="replace")
        return ParsedDocument(
            text=text,
            metadata={"filename": filename, "fallback": True},
            source_type=source_type,
            page_count=1,
        )
    raise ValueError(
        f"Unstructured non disponibile e nessun fallback per tipo {source_type}"
    )


def _detect_source_type(suffix: str) -> str:
    mapping = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "doc",
        ".xlsx": "xlsx",
        ".xls": "xls",
        ".html": "html",
        ".htm": "html",
        ".eml": "eml",
        ".txt": "txt",
        ".md": "md",
    }
    return mapping.get(suffix, "unknown")
