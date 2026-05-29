"""Scenario: Ducati Corse — Stagione MotoGP 2026.

Incoerenze attese:
  DC001: Motore DC-ENG-2026-V4-REV3 IN_RACE ma omologazione FIM valida solo fino 2025-12-31
  DC002: Budget cap dichiarato 13.200.000 EUR > limite FIM 12.000.000 EUR (+10%)
  DC003: Development tokens usati (3) = allocazione totale (3), nessun margine rimanente
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class DucatiSeason2026Scenario(BaseScenario):
    domain = "ducati_corse"
    scenario_name = "Ducati Corse — MotoGP 2026: omologazione scaduta, budget cap e token esauriti"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "ducati_corse"
        return [
            base / "componente_motore_2026.txt",
            base / "omologazione_fim_2025.txt",
            base / "budget_cap_declaration_2026.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="DC001",
                description=(
                    "Motore DC-ENG-2026-V4-REV3 è IN_RACE nella stagione MotoGP 2026 "
                    "ma l'omologazione FIM-MOTO-2025-ENG-0044 è valida solo fino al "
                    "2025-12-31. Nessuna omologazione 2026 registrata."
                ),
                severity="CRITICAL",
                entity_a="RaceComponent(DC-ENG-2026-V4-REV3, season=2026)",
                entity_b="HomologationCertificate(FIM-MOTO-2025-ENG-0044, valid_to=2025-12-31)",
            ),
            ExpectedIncoherence(
                rule_id="DC002",
                description=(
                    "Dichiarazione budget cap 2026: 13.200.000 EUR > limite FIM "
                    "12.000.000 EUR. Sforamento di 1.200.000 EUR (+10%). "
                    "Soglia sanzione FIM: >5%."
                ),
                severity="HIGH",
                entity_a="BudgetCapDeclaration(2026, 13200000)",
                entity_b=None,
            ),
            ExpectedIncoherence(
                rule_id="DC003",
                description=(
                    "Development tokens 2026 completamente esauriti: 3 usati su 3 allocati. "
                    "Non è possibile sviluppare ulteriori revisioni motore nella stagione 2026."
                ),
                severity="HIGH",
                entity_a="DevelopmentTokenAllocation(2026, used=3, total=3)",
                entity_b=None,
            ),
        ]
