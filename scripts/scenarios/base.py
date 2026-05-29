"""Base class per tutti i demo scenario runner CCI/AVCS.

Ogni scenario implementa `expected_incoherences` e `fixture_files`.
Il runner esegue gli step disponibili in base allo stato della piattaforma:
  - Step A: Ingestion (disponibile da Step 4)
  - Step B: Coherence check (disponibile da Step 7)
  - Step C: Report generato (disponibile da Step 8)
  - Step D: Audit chain verify (disponibile da Step 9)
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

FIXTURES_BASE = pathlib.Path(__file__).parent.parent.parent / "tests" / "fixtures"
DEMO_OUTPUT = pathlib.Path(__file__).parent.parent.parent / "demo_output"

INGESTION_URL = os.getenv("CCI_INGESTION_URL", "http://localhost:8000")
AGENTS_URL = os.getenv("CCI_AGENTS_URL", "http://localhost:8004")
GOVERNANCE_URL = os.getenv("CCI_GOVERNANCE_URL", "http://localhost:8005")


@dataclass
class ExpectedIncoherence:
    rule_id: str
    description: str
    severity: str
    entity_a: str
    entity_b: str | None = None


@dataclass
class ScenarioResult:
    domain: str
    scenario_name: str
    ingested_docs: list[str] = field(default_factory=list)
    detected_incoherences: list[dict[str, Any]] = field(default_factory=list)
    expected_incoherences: list[ExpectedIncoherence] = field(default_factory=list)
    report_path: str | None = None
    audit_verified: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def ingestion_ok(self) -> bool:
        return len(self.ingested_docs) > 0 and not self.errors

    @property
    def coherence_precision(self) -> float:
        if not self.expected_incoherences:
            return 1.0
        detected_rules = {d.get("rule_violated") for d in self.detected_incoherences}
        expected_rules = {e.rule_id for e in self.expected_incoherences}
        tp = len(detected_rules & expected_rules)
        return tp / len(detected_rules) if detected_rules else 0.0

    def print_summary(self) -> None:
        print(f"\n{'='*60}")
        print(f"SCENARIO: {self.scenario_name} [{self.domain}]")
        print(f"{'='*60}")
        print(f"  Documenti ingeriti:    {len(self.ingested_docs)}")
        print(f"  Incoerenze attese:     {len(self.expected_incoherences)}")
        print(f"  Incoerenze rilevate:   {len(self.detected_incoherences)}")
        print(f"  Audit chain verified:  {self.audit_verified}")
        if self.errors:
            print(f"  ERRORI: {self.errors}")
        print()
        if self.expected_incoherences:
            print("  Incoerenze attese:")
            for inc in self.expected_incoherences:
                status = "OK" if any(
                    d.get("rule_violated") == inc.rule_id
                    for d in self.detected_incoherences
                ) else ".."
                print(f"    [{status}] {inc.rule_id}: {inc.description}")


class BaseScenario(ABC):
    """Scenario base — implementa i metodi astratti nelle sottoclassi."""

    domain: str
    scenario_name: str

    @property
    @abstractmethod
    def fixture_files(self) -> list[pathlib.Path]:
        """Lista dei file fixture da ingerire."""
        ...

    @property
    @abstractmethod
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        """Incoerenze attese dopo la verifica di coerenza."""
        ...

    def run(self, dry_run: bool = False) -> ScenarioResult:
        """Esegue lo scenario completo.

        dry_run=True: mostra il piano senza chiamare i servizi.
        """
        result = ScenarioResult(
            domain=self.domain,
            scenario_name=self.scenario_name,
            expected_incoherences=self.expected_incoherences,
        )

        print(f"\n>> Scenario: {self.scenario_name} (domain: {self.domain})")

        if dry_run:
            print("  [DRY RUN — servizi non chiamati]")
            print(f"  Fixture files: {[f.name for f in self.fixture_files]}")
            print(f"  Incoerenze attese: {len(self.expected_incoherences)}")
            return result

        # Step A: Ingestion
        print("  Step A: Ingestion documenti...")
        result.ingested_docs = self._ingest_documents(result)

        # Step B: Coherence check (disponibile da Step 7)
        print("  Step B: Coherence check... [disponibile da Step 7]")

        # Step C: Report (disponibile da Step 8)
        print("  Step C: Generazione report... [disponibile da Step 8]")

        # Step D: Audit verify (disponibile da Step 9)
        print("  Step D: Audit chain verify... [disponibile da Step 9]")

        result.print_summary()
        self._save_result(result)
        return result

    def _ingest_documents(self, result: ScenarioResult) -> list[str]:
        """Chiama POST /documents per ogni fixture file."""
        try:
            import urllib.request
            import urllib.error
        except ImportError:
            result.errors.append("urllib non disponibile")
            return []

        ingested: list[str] = []
        for fixture_path in self.fixture_files:
            if not fixture_path.exists():
                result.errors.append(f"Fixture non trovata: {fixture_path}")
                continue

            content = fixture_path.read_bytes()
            boundary = b"----CCI_BOUNDARY_12345"
            body = (
                b"--" + boundary + b"\r\n"
                + b'Content-Disposition: form-data; name="file"; filename="'
                + fixture_path.name.encode() + b'"\r\n'
                + b"Content-Type: text/plain\r\n\r\n"
                + content + b"\r\n"
                + b"--" + boundary + b"\r\n"
                + b'Content-Disposition: form-data; name="domain"\r\n\r\n'
                + self.domain.encode() + b"\r\n"
                + b"--" + boundary + b"--\r\n"
            )
            req = urllib.request.Request(
                f"{INGESTION_URL}/documents",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                    doc_id = data.get("document_id", "unknown")
                    ingested.append(doc_id)
                    print(f"    ✓ {fixture_path.name} → {doc_id} ({data.get('chunk_count', 0)} chunks)")
            except urllib.error.URLError as e:
                result.errors.append(f"Ingestion failed {fixture_path.name}: {e}")
                print(f"    ✗ {fixture_path.name} — {e}")

        return ingested

    def _save_result(self, result: ScenarioResult) -> None:
        DEMO_OUTPUT.mkdir(parents=True, exist_ok=True)
        out_path = DEMO_OUTPUT / f"{self.domain}_demo_result.json"
        out_path.write_text(
            json.dumps(
                {
                    "domain": result.domain,
                    "scenario": result.scenario_name,
                    "ingested_docs": result.ingested_docs,
                    "expected_incoherences": [
                        {"rule_id": e.rule_id, "description": e.description}
                        for e in result.expected_incoherences
                    ],
                    "detected_incoherences": result.detected_incoherences,
                    "errors": result.errors,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"  Output salvato: {out_path}")
