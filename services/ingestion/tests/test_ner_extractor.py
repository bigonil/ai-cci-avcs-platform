"""Test unitari per NER extractor e pseudonimizzazione PII."""
from __future__ import annotations

import pytest

from cci_ingestion.extractors.ner_extractor import NERResult, extract_entities


class TestPiiRedaction:
    def test_redacts_italian_fiscal_code(self) -> None:
        text = "Il codice fiscale è RSSMRA85M01H501Z e il CF del fornitore è BNCLCU80A41F205X."
        result = extract_entities(text, domain="hera_it", mask_pii=True)
        assert "RSSMRA85M01H501Z" not in result.redacted_text
        assert result.pii_found is True

    def test_redacts_email(self) -> None:
        text = "Contattare mario.rossi@hera.it per informazioni."
        result = extract_entities(text, domain="hera_it", mask_pii=True)
        assert "mario.rossi@hera.it" not in result.redacted_text
        assert result.pii_found is True

    def test_redacts_iban(self) -> None:
        text = "Bonifico su IT60X0542811101000000123456."
        result = extract_entities(text, domain="hera_it", mask_pii=True)
        assert "IT60X0542811101000000123456" not in result.redacted_text

    def test_no_pii_unchanged(self) -> None:
        text = "Il budget approvato per il 2026 è di 800.000 EUR."
        result = extract_entities(text, domain="hera_it", mask_pii=True)
        assert result.pii_found is False
        assert "800.000 EUR" in result.redacted_text

    def test_pii_disabled(self) -> None:
        text = "CF: RSSMRA85M01H501Z"
        result = extract_entities(text, domain="hera_it", mask_pii=False)
        assert "RSSMRA85M01H501Z" in result.redacted_text
        assert result.pii_found is False


class TestRegexEntities:
    def test_detects_money_eur(self) -> None:
        text = "Commitment totale: 920.000 € per Q1 2026."
        result = extract_entities(text, domain="hera_it", mask_pii=False)
        money_entities = [e for e in result.entities if e.entity_type == "MONEY"]
        assert len(money_entities) >= 1

    def test_detects_iso_date(self) -> None:
        text = "Scadenza certificazione: 2026-03-31."
        result = extract_entities(text, domain="hera_it", mask_pii=False)
        date_entities = [e for e in result.entities if e.entity_type == "DATE"]
        assert len(date_entities) >= 1
        assert any("2026-03-31" in e.label for e in date_entities)

    def test_detects_iso_standard(self) -> None:
        text = "La certificazione ISO/IEC 27001:2022 è scaduta."
        result = extract_entities(text, domain="hera_it", mask_pii=False)
        std_entities = [e for e in result.entities if e.entity_type == "STANDARD_REF"]
        assert len(std_entities) >= 1

    def test_returns_ner_result(self) -> None:
        result = extract_entities("testo", domain="hera_it")
        assert isinstance(result, NERResult)

    def test_empty_text(self) -> None:
        result = extract_entities("", domain="hera_it")
        assert result.entities == []
        assert result.pii_found is False


class TestDomainSpecific:
    def test_ducati_corse_domain(self) -> None:
        text = "Il componente è stato omologato FIM per la stagione 2026."
        result = extract_entities(text, domain="ducati_corse", mask_pii=True)
        assert isinstance(result, NERResult)

    def test_prada_domain(self) -> None:
        text = "Il Digital Product Passport DPP-2026-001 è stato emesso il 2026-01-15."
        result = extract_entities(text, domain="prada", mask_pii=True)
        date_entities = [e for e in result.entities if e.entity_type == "DATE"]
        assert len(date_entities) >= 1
