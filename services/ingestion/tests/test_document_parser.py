"""Test unitari per il document parser."""
from __future__ import annotations

import pytest

from cci_ingestion.parsers.document_parser import ParsedDocument, parse_document


class TestParseDocument:
    def test_parse_plain_text(self) -> None:
        content = b"Questo e' un testo di prova.\n\nSecondo paragrafo."
        result = parse_document(content, "test.txt")
        assert isinstance(result, ParsedDocument)
        assert "testo di prova" in result.text
        assert result.source_type == "txt"

    def test_parse_markdown(self) -> None:
        content = b"# Titolo\n\nContenuto del documento."
        result = parse_document(content, "test.md")
        assert result.source_type == "md"
        assert len(result.text) > 0

    def test_unknown_extension_without_unstructured(self) -> None:
        content = b"binary content"
        with pytest.raises(ValueError, match="Impossibile parsare|Unstructured"):
            parse_document(content, "test.bin")

    def test_source_type_detection(self) -> None:
        cases = [
            ("file.pdf", "pdf"),
            ("doc.docx", "docx"),
            ("sheet.xlsx", "xlsx"),
            ("page.html", "html"),
            ("email.eml", "eml"),
            ("notes.txt", "txt"),
            ("readme.md", "md"),
        ]
        for filename, expected_type in cases:
            from cci_ingestion.parsers.document_parser import _detect_source_type
            from pathlib import Path
            suffix = Path(filename).suffix.lower()
            assert _detect_source_type(suffix) == expected_type

    def test_metadata_contains_filename(self) -> None:
        content = b"Test content"
        result = parse_document(content, "budget_2026.txt")
        assert result.metadata.get("filename") == "budget_2026.txt"

    def test_page_count_minimum_one(self) -> None:
        content = b"Testo senza informazioni di pagina."
        result = parse_document(content, "doc.txt")
        assert result.page_count >= 1
