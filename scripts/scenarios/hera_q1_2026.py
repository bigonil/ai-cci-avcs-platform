"""Scenario pilota: Hera Group IT — Q1 2026.

Incoerenze attese:
  R001: AWS commitment 920k EUR > budget approvato CdA 800k EUR (overrun 15%)
  R002: ISO 27001 scade 2026-03-31 ma commitment copre tutto il 2026
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class HeraQ12026Scenario(BaseScenario):
    domain = "hera_it"
    scenario_name = "Hera Group IT — Cloud Commitment vs Budget vs ISO 27001 Q1 2026"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "hera_it"
        return [
            base / "bilancio_preventivo_2026.txt",
            base / "aws_commitment_report_q1_2026.txt",
            base / "iso27001_cert_hera.txt",
            base / "policy_finanziaria_v3.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="R001",
                description="AWS commitment 920.000 EUR > budget CdA approvato 800.000 EUR (overrun +15%)",
                severity="HIGH",
                entity_a="CloudCommitment(AWS, 920000)",
                entity_b="BudgetApproval(2026, 800000)",
            ),
            ExpectedIncoherence(
                rule_id="R002",
                description="ISO 27001 scade 2026-03-31 ma il commitment AWS copre tutto il 2026 (Q2-Q4 senza certificazione valida)",
                severity="CRITICAL",
                entity_a="CloudCommitment(period_end=2026-12-31)",
                entity_b="ISO27001Certification(valid_to=2026-03-31)",
            ),
        ]
