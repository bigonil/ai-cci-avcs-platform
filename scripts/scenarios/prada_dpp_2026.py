"""Scenario: Prada Group — Digital Product Passport e Supply Chain 2026.

Incoerenze attese:
  PR002: Fornitore tier 1 MBM Manifattura con audit etico PENDING (nessuna cert. materiale)
  PR003: Fornitore Conceria Walpier con certificazione LWG scaduta 2025-10-31
         (produzione collezione FW2026 avviene nel 2026)
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class PradaDpp2026Scenario(BaseScenario):
    domain = "prada"
    scenario_name = "Prada Group — DPP e Supply Chain FW2026: fornitori non certificati"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "prada"
        return [
            base / "collezione_fw2026.txt",
            base / "fornitori_certificazioni.txt",
            base / "esg_report_2025.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="PR002",
                description=(
                    "Fornitore tier 1 MBM Manifattura S.r.l. ha stato audit etico PENDING "
                    "e nessuna certificazione materiale attiva. "
                    "Politica Prada richiede audit etico completato per tutti i tier 1."
                ),
                severity="HIGH",
                entity_a="Supplier(MBM Manifattura, tier=1, audit=PENDING)",
                entity_b=None,
            ),
            ExpectedIncoherence(
                rule_id="PR003",
                description=(
                    "Fornitore Conceria Walpier (pelle Saffiano per PR-BAG-FW26-001) "
                    "ha certificazione LWG Gold scaduta il 2025-10-31. "
                    "La produzione della collezione FW2026 avviene nel 2026 "
                    "senza certificazione materiale valida."
                ),
                severity="HIGH",
                entity_a="Supplier(Conceria Walpier, tier=1)",
                entity_b="MaterialCertification(LWG-IT-2023-4412, valid_to=2025-10-31)",
            ),
        ]
