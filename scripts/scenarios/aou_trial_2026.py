"""Scenario: AOU Policlinico di Modena — Sperimentazione clinica Q1 2026.

Incoerenze attese:
  C001: Trial AOU-MO-2026-003 ACTIVE ma approvazione etica AVEN scaduta 2025-12-31
        (il rinnovo è in attesa e non è ancora stato emesso)
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class AouTrial2026Scenario(BaseScenario):
    domain = "aou_clinical"
    scenario_name = "AOU Modena — Sperimentazione clinica senza approvazione etica valida 2026"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "aou_clinical"
        return [
            base / "trial_registro_aou_2026.txt",
            base / "comitato_etico_approvazione.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="C001",
                description=(
                    "Trial AOU-MO-2026-003 in stato ACTIVE dal 2026-01-15 "
                    "ma approvazione etica AVEN scaduta il 2025-12-31. "
                    "Rinnovo richiesto in data 2026-01-10 non ancora deliberato."
                ),
                severity="CRITICAL",
                entity_a="ClinicalTrial(AOU-MO-2026-003, status=ACTIVE)",
                entity_b="EthicsApproval(AVEN-CE-2025-089, valid_to=2025-12-31)",
            ),
        ]
