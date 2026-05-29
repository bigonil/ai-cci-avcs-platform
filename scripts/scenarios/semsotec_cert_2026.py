"""Scenario: SEMSOTEC — Prodotto ON_MARKET con certificazione CE scaduta Q1 2026.

Incoerenze attese:
  P001: SEM-VALVE-PRO-3000 stato ON_MARKET ma certificazione TÜV CE scaduta 2025-05-31
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class SemsotecCert2026Scenario(BaseScenario):
    domain = "semsotec_product"
    scenario_name = "SEMSOTEC — Valvola VP3000 in commercio senza certificazione CE valida 2026"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "semsotec_product"
        return [
            base / "catalogo_prodotti_2026.txt",
            base / "certificazioni_ce.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="P001",
                description=(
                    "Prodotto SEM-VALVE-PRO-3000 (VP3000-SS-DN80) è ON_MARKET "
                    "nell'UE nel 2026 ma la certificazione CE TÜV (TUV-CE-2023-00891) "
                    "è scaduta il 2025-05-31. Rinnovo non ancora completato."
                ),
                severity="HIGH",
                entity_a="Product(VP3000-SS-DN80, status=ON_MARKET)",
                entity_b="ProductCertification(TUV-CE-2023-00891, valid_to=2025-05-31)",
            ),
        ]
