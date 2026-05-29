"""Scenario: Dallara — Fornitura OEM IndyCar 2026.

Incoerenze attese:
  DA001: IR18 IN_COMPETITION stagione 2026 ma certificazione crash test FIA
         scaduta 2025-12-31. Le specifiche aerodinamiche 2026 richiedono ri-certificazione.
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class DallaraOem2026Scenario(BaseScenario):
    domain = "dallara"
    scenario_name = "Dallara — IR18 IndyCar 2026: certificazione crash test FIA scaduta"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "dallara"
        return [
            base / "veicolo_sf23_indycar.txt",
            base / "crash_test_fia_2024.txt",
            base / "contratto_oem_indycar.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="DA001",
                description=(
                    "Veicolo Dallara IR18 è IN_COMPETITION nel campionato IndyCar 2026 "
                    "ma la certificazione crash test FIA (FIA-CTC-2024-DAL-IR18-003) "
                    "è scaduta il 2025-12-31. Il kit aerodinamico 2026 richiede "
                    "ri-certificazione strutturale non ancora completata."
                ),
                severity="CRITICAL",
                entity_a="Vehicle(DAL-IR18-2026-001, status=IN_COMPETITION)",
                entity_b="CrashTestCertification(FIA-CTC-2024-DAL-IR18-003, valid_to=2025-12-31)",
            ),
        ]
