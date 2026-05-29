"""Dispatcher demo scenario CCI/AVCS.

Uso:
  python scripts/run_demo_scenario.py --domain hera_it
  python scripts/run_demo_scenario.py --domain all
  python scripts/run_demo_scenario.py --domain ducati_corse --dry-run

Domini disponibili:
  hera_it, aou_clinical, semsotec_product, ducati_corse, dallara, prada, all

Il flag --dry-run mostra il piano senza chiamare i servizi (utile in CI).
Senza --dry-run richiede docker-compose up attivo (make up).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Aggiunge la root del progetto al path per import scripts.scenarios
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.scenarios.base import BaseScenario, ScenarioResult
from scripts.scenarios.hera_q1_2026 import HeraQ12026Scenario
from scripts.scenarios.aou_trial_2026 import AouTrial2026Scenario
from scripts.scenarios.semsotec_cert_2026 import SemsotecCert2026Scenario
from scripts.scenarios.ducati_season_2026 import DucatiSeason2026Scenario
from scripts.scenarios.dallara_oem_2026 import DallaraOem2026Scenario
from scripts.scenarios.prada_dpp_2026 import PradaDpp2026Scenario

SCENARIOS: dict[str, type[BaseScenario]] = {
    "hera_it": HeraQ12026Scenario,
    "aou_clinical": AouTrial2026Scenario,
    "semsotec_product": SemsotecCert2026Scenario,
    "ducati_corse": DucatiSeason2026Scenario,
    "dallara": DallaraOem2026Scenario,
    "prada": PradaDpp2026Scenario,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CCI/AVCS Demo Scenario Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--domain",
        choices=[*SCENARIOS.keys(), "all"],
        default="all",
        help="Dominio verticale da eseguire (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra piano senza chiamare i servizi",
    )
    return parser.parse_args()


def run_scenario(domain: str, dry_run: bool) -> ScenarioResult:
    scenario_cls = SCENARIOS[domain]
    scenario = scenario_cls()
    return scenario.run(dry_run=dry_run)


def main() -> None:
    args = parse_args()

    print("\nCCI/AVCS — Demo Scenario Runner")
    print("=" * 60)

    if not args.dry_run:
        print("Prerequisiti: assicurarsi che 'make up' sia stato eseguito.")
        print(f"Ingestion URL:   {__import__('os').getenv('CCI_INGESTION_URL', 'http://localhost:8000')}")
        print(f"Agents URL:      {__import__('os').getenv('CCI_AGENTS_URL', 'http://localhost:8004')}")
        print(f"Governance URL:  {__import__('os').getenv('CCI_GOVERNANCE_URL', 'http://localhost:8005')}")

    domains = list(SCENARIOS.keys()) if args.domain == "all" else [args.domain]

    results: list[ScenarioResult] = []
    for domain in domains:
        result = run_scenario(domain, dry_run=args.dry_run)
        results.append(result)

    # Riepilogo finale
    print(f"\n{'='*60}")
    print("RIEPILOGO FINALE")
    print(f"{'='*60}")
    total_docs = sum(len(r.ingested_docs) for r in results)
    total_expected = sum(len(r.expected_incoherences) for r in results)
    total_errors = sum(len(r.errors) for r in results)

    for r in results:
        status = "OK" if r.ingestion_ok or args.dry_run else "!!"
        print(f"  [{status}] {r.domain:25s} - docs:{len(r.ingested_docs):2d}  incoerenze attese:{len(r.expected_incoherences):2d}")

    print(f"\n  Totale documenti ingeriti: {total_docs}")
    print(f"  Totale incoerenze attese:  {total_expected}")
    if total_errors:
        print(f"  ERRORI: {total_errors}")
        sys.exit(1)

    print("\nPer la verifica completa di coerenza: disponibile da Step 7 (coherence-service).")
    print("Per i report generati:                disponibile da Step 8 (agents).")
    print("Per la verifica audit chain:          disponibile da Step 9 (governance-service).")


if __name__ == "__main__":
    main()
