"""Scenario pilota: Hera Group IT — Multi-Cloud Q1 2026.

Provider: Azure (primario), AWS (secondario), GCP (terziario/analytics)

Incoerenze attese:
  R001: Azure commitment 580k EUR > allocation CTO approvata 500k EUR (+16%)
  R002: ISO 27001 scade 2026-03-31 ma commitment Azure copre tutto il 2026
  R003: Totale multi-cloud (Azure 580k + AWS 190k + GCP 85k = 855k) > budget CdA 800k (+6.9%)
  R004: Azure = 67.8% del totale — sotto soglia 70%, ma da monitorare (MEDIUM)
"""
from __future__ import annotations

import pathlib

from scripts.scenarios.base import BaseScenario, ExpectedIncoherence, FIXTURES_BASE


class HeraQ12026Scenario(BaseScenario):
    domain = "hera_it"
    scenario_name = "Hera Group IT — Multi-Cloud Commitment vs Budget vs ISO 27001 Q1 2026"

    @property
    def fixture_files(self) -> list[pathlib.Path]:
        base = FIXTURES_BASE / "hera_it"
        return [
            base / "bilancio_preventivo_2026.txt",
            base / "azure_commitment_report_q1_2026.txt",
            base / "aws_commitment_report_q1_2026.txt",
            base / "gcp_commitment_report_q1_2026.txt",
            base / "iso27001_cert_hera.txt",
            base / "policy_finanziaria_v3.txt",
        ]

    @property
    def expected_incoherences(self) -> list[ExpectedIncoherence]:
        return [
            ExpectedIncoherence(
                rule_id="R001",
                description=(
                    "Azure commitment 580.000 EUR > allocation CTO approvata 500.000 EUR "
                    "(sforamento +80.000 EUR, +16%). Notifica CTO in corso."
                ),
                severity="HIGH",
                entity_a="CloudCommitment(Azure, 580000)",
                entity_b="CloudBudgetAllocation(Azure, 2026, 500000)",
            ),
            ExpectedIncoherence(
                rule_id="R002",
                description=(
                    "ISO 27001 (Bureau Veritas, cert. IT-ISMS-2024-0892) scade 2026-03-31 "
                    "ma il commitment Azure copre il periodo 2026-01-01/2026-12-31. "
                    "Q2-Q4 2026 senza certificazione valida."
                ),
                severity="CRITICAL",
                entity_a="CloudCommitment(Azure, period_end=2026-12-31)",
                entity_b="ISO27001Certification(valid_to=2026-03-31)",
            ),
            ExpectedIncoherence(
                rule_id="R003",
                description=(
                    "Totale multi-cloud 2026: Azure 580k + AWS 190k + GCP 85k = 855.000 EUR "
                    "> budget CdA totale approvato 800.000 EUR "
                    "(sforamento +55.000 EUR, +6.9%). Richiesta approvazione CFO."
                ),
                severity="HIGH",
                entity_a="MultiCloudTotal(2026, 855000)",
                entity_b="BudgetApproval(2026, 800000)",
            ),
            ExpectedIncoherence(
                rule_id="R004",
                description=(
                    "Azure rappresenta 580k/855k = 67.8% del totale cloud 2026. "
                    "Sotto la soglia di alert del 70% ma in avvicinamento. "
                    "Monitoraggio concentrazione vendor lock-in raccomandato."
                ),
                severity="MEDIUM",
                entity_a="CloudCommitment(Azure, concentration_pct=67.8)",
                entity_b=None,
            ),
        ]
