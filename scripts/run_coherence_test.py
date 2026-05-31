"""
/run-coherence-test — Scenario demo Hera Q1 2026 (in-process, no Docker).

Esegue il CoherenceEngine direttamente in Python senza richiedere
il docker stack. Valida le 4 regole R001-R004 sulle fixture reali.
"""
from __future__ import annotations

import pathlib
import sys
import time
import json

# Force UTF-8 on Windows consoles (default cp1252 can't encode arrow/box chars).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Aggiungi i src paths al PYTHONPATH (monorepo workspace)
_REPO = pathlib.Path(__file__).parent.parent
for _src in [
    "libs/cci-common/src",
    "services/coherence/src",
]:
    sys.path.insert(0, str(_REPO / _src))

from cci_coherence.entity_extractor import extract_hera_it
from cci_coherence.rule_evaluator import evaluate_rule

FIXTURES_BASE = _REPO / "tests" / "fixtures" / "hera_it"
ONTOLOGY_FILE = _REPO / "docs" / "ontologies" / "hera_it.yaml"
DEMO_OUTPUT = _REPO / "demo_output"


def load_fixtures_as_chunks() -> list[dict]:
    """Carica i file fixture come lista di chunk (simulazione retrieval)."""
    chunks = []
    for txt_file in sorted(FIXTURES_BASE.glob("*.txt")):
        text = txt_file.read_text(encoding="utf-8")
        chunks.append({
            "chunk_id": f"chunk_{txt_file.stem}",
            "text": text,
        })
        print(f"  Loaded fixture: {txt_file.name} ({len(text)} chars)")
    return chunks


def load_rules() -> list[dict]:
    """Carica le regole dall'ontologia hera_it.yaml."""
    import yaml
    with ONTOLOGY_FILE.open() as fh:
        data = yaml.safe_load(fh)
    rules = data.get("rules", [])
    return [
        {"rule_id": r["id"], "when": r["when"], "severity": r["severity"]}
        for r in rules
    ]


def run_scenario() -> dict:
    """Esegue lo scenario completo, restituisce il report."""
    sep = "=" * 60
    print(f"\n{sep}")
    print("CCI/AVCS — Scenario Demo: Hera Group IT Multi-Cloud Q1 2026")
    print(f"{sep}\n")

    t0 = time.time()

    # 1. Carica fixture
    print("► Step 1: Caricamento fixture Hera Q1 2026")
    chunks = load_fixtures_as_chunks()
    print(f"  {len(chunks)} fixture file caricati\n")

    # 2. Carica regole
    print("► Step 2: Caricamento ontologia hera_it.yaml")
    rules = load_rules()
    print(f"  {len(rules)} regole caricate: {[r['rule_id'] for r in rules]}\n")

    # 3. Estrazione entità
    print("► Step 3: Estrazione entità (regex, zero LLM — R4)")
    ctx = extract_hera_it(chunks)
    print(f"  CloudCommitment:       {len(ctx.get('CloudCommitment'))}")
    print(f"  CloudBudgetAllocation: {len(ctx.get('CloudBudgetAllocation'))}")
    print(f"  BudgetApproval:        {len(ctx.get('BudgetApproval'))}")
    print(f"  ISO27001Certification: {len(ctx.get('ISO27001Certification'))}")

    for e in ctx.get("CloudCommitment"):
        print(f"    → Commitment: {e.get_str('provider')} "
              f"{e.get_float('amount_eur'):,.0f} EUR "
              f"(period_end={e.get_date_str('period_end')})")
    for e in ctx.get("CloudBudgetAllocation"):
        print(f"    → Allocation: {e.get_str('provider')} "
              f"{e.get_float('allocated_eur'):,.0f} EUR")
    for e in ctx.get("BudgetApproval"):
        print(f"    → BudgetApproval: {e.get_float('amount_eur'):,.0f} EUR")
    for e in ctx.get("ISO27001Certification"):
        print(f"    → ISO27001: valid_to={e.get_date_str('valid_to')}")
    print()

    # 4. Valutazione regole
    print("► Step 4: Valutazione regole (deterministica, R4: zero LLM)")
    all_violations = []
    for rule in rules:
        violations = evaluate_rule(
            rule_id=rule["rule_id"],
            when_expr=rule["when"],
            severity=rule["severity"],
            domain="hera_it",
            ctx=ctx,
        )
        status = "VIOLAZIONE" if violations else "OK"
        print(f"  [{status:>10}] {rule['rule_id']} (severity={rule['severity']})")
        for v in violations:
            print(f"    → {v.description}")
            print(f"       evidence_chunks: {v.evidence_chunks}")
        all_violations.extend(violations)
    print()

    elapsed = time.time() - t0

    # 5. Report finale
    print(f"► Step 5: Report")
    print(f"{'-'*60}")

    expected = {
        "R001": ("Azure commitment 580k EUR > allocation CTO 500k EUR", "HIGH"),
        "R002": ("ISO 27001 scade 2026-03-31, commitment Azure copre 2026-12-31", "CRITICAL"),
        "R003": ("Totale multi-cloud 855k EUR > budget CdA 800k EUR", "HIGH"),
    }

    detected_rules = {v.rule_id for v in all_violations}
    passed = 0
    failed = 0

    for rule_id, (desc, sev) in expected.items():
        found = rule_id in detected_rules
        icon = "✓" if found else "✗"
        if found:
            passed += 1
        else:
            failed += 1
        print(f"  {icon} {rule_id}: {desc}")
        if found:
            v = next(x for x in all_violations if x.rule_id == rule_id)
            print(f"    severity={v.severity} | evidence={v.evidence_chunks}")
            if v.computed_values:
                print(f"    values={v.computed_values}")

    # R004 — atteso: NON violazione (67.8% < 70%)
    r004_violations = [v for v in all_violations if v.rule_id == "R004"]
    if not r004_violations:
        print(f"  ✓ R004: Azure 67.8% < soglia 70% — nessuna violazione (corretto)")
        passed += 1
    else:
        print(f"  ✗ R004: Violazione inattesa rilevata!")
        failed += 1

    print(f"{'-'*60}")
    print(f"  Regole valutate:    {len(rules)}")
    print(f"  Violazioni trovate: {len(all_violations)}")
    print(f"  Verifiche passate:  {passed}/4")
    print(f"  Tempo di esecuzione: {elapsed*1000:.1f}ms")

    # Evidence chunks non vuoti
    chunks_ok = all(len(v.evidence_chunks) > 0 for v in all_violations)
    print(f"  Evidence chunks populated: {'✓' if chunks_ok else '✗'}")

    all_pass = (failed == 0)
    print(f"\n  {'✓ DEMO SCENARIO PASSED' if all_pass else '✗ DEMO SCENARIO FAILED'}")
    print(f"{sep}\n")

    # 6. Salva output
    result = {
        "scenario": "Hera Group IT Multi-Cloud Q1 2026",
        "domain": "hera_it",
        "as_of_date": "2026-03-31",
        "evaluation_source": "chunks",
        "rules_evaluated": len(rules),
        "incoherences_found": len(all_violations),
        "elapsed_ms": round(elapsed * 1000, 1),
        "violations": [
            {
                "rule_violated": v.rule_id,
                "severity": v.severity,
                "description": v.description,
                "evidence_chunks": v.evidence_chunks,
                "computed_values": v.computed_values,
            }
            for v in all_violations
        ],
    }
    DEMO_OUTPUT.mkdir(parents=True, exist_ok=True)
    out = DEMO_OUTPUT / "hera_q1_2026_coherence_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Output salvato: {out.relative_to(_REPO)}")

    return result


if __name__ == "__main__":
    run_scenario()
