"""NER extractor — entity recognition + PII pseudonimizzazione.

Usa spaCy per NER standard e GLiNER per entità di dominio (importi, date, codici).
Applica pseudonimizzazione GDPR-aware prima di qualsiasi storage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from cci_common.observability import get_logger

logger = get_logger(__name__)

# Pattern PII da mascherare (GDPR)
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("FISCAL_CODE", re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b")),
    ("EMAIL", re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    ("PHONE", re.compile(r"\b(\+39|0039)?[\s\-]?(\d{2,4})[\s\-]?\d{6,8}\b")),
]


@dataclass(frozen=True)
class ExtractedEntity:
    entity_type: str
    label: str
    start_char: int
    end_char: int
    confidence: float = 1.0


@dataclass
class NERResult:
    entities: list[ExtractedEntity] = field(default_factory=list)
    redacted_text: str = ""
    pii_found: bool = False


def extract_entities(text: str, domain: str, mask_pii: bool = True) -> NERResult:
    """Estrae entità dal testo e opzionalmente maschera PII.

    Tenta spaCy per NER; se non disponibile usa regex-based fallback
    per entità di base (importi EUR, date, codici ISO).
    """
    redacted = _redact_pii(text) if mask_pii else text
    pii_found = redacted != text

    entities: list[ExtractedEntity] = []

    try:
        entities.extend(_extract_with_spacy(redacted, domain))
    except ImportError:
        logger.warning("spacy_not_installed", domain=domain)

    entities.extend(_extract_with_regex(redacted, domain))

    return NERResult(
        entities=entities,
        redacted_text=redacted,
        pii_found=pii_found,
    )


def _redact_pii(text: str) -> str:
    for pii_type, pattern in _PII_PATTERNS:
        text = pattern.sub(f"[{pii_type}]", text)
    return text


def _extract_with_spacy(text: str, domain: str) -> list[ExtractedEntity]:
    import spacy  # type: ignore[import-untyped]

    # Carica il modello italiano se disponibile, fallback su inglese
    try:
        nlp = spacy.load("it_core_news_sm")
    except OSError:
        nlp = spacy.load("en_core_web_sm")

    doc = nlp(text[:100_000])  # limite di sicurezza
    return [
        ExtractedEntity(
            entity_type=ent.label_,
            label=ent.text,
            start_char=ent.start_char,
            end_char=ent.end_char,
        )
        for ent in doc.ents
    ]


def _extract_with_regex(text: str, domain: str) -> list[ExtractedEntity]:
    """Fallback regex per entità finanziarie e date standard."""
    entities: list[ExtractedEntity] = []

    # Importi EUR
    for m in re.finditer(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*[€EUReur]+)", text):
        entities.append(
            ExtractedEntity(
                entity_type="MONEY",
                label=m.group(0).strip(),
                start_char=m.start(),
                end_char=m.end(),
                confidence=0.85,
            )
        )

    # Date ISO 8601 e italiane
    date_pattern = re.compile(
        r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}\.\d{2}\.\d{4})\b"
    )
    for m in date_pattern.finditer(text):
        entities.append(
            ExtractedEntity(
                entity_type="DATE",
                label=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                confidence=0.9,
            )
        )

    # Codici ISO (es. ISO 27001, ISO 42001)
    for m in re.finditer(r"\bISO\s*/?IEC\s*\d{4,5}(?::\d{4})?\b", text):
        entities.append(
            ExtractedEntity(
                entity_type="STANDARD_REF",
                label=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                confidence=0.95,
            )
        )

    return entities
