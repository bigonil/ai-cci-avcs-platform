"""
In-process multi-domain coherence test — tutti i 6 domini pilota CCI/AVCS.

Esegue il CoherenceEngine direttamente in Python senza richiedere
il docker stack. Valida le regole su fixture reali per:
  hera_it, aou_clinical, semsotec_product, ducati_corse, dallara, prada

Uso:
  uv run python scripts/run_all_coherence_test.py
  uv run python scripts/run_all_coherence_test.py --domain ducati_corse
  uv run python scripts/run_all_coherence_test.py --domain all
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = pathlib.Path(__file__).parent.parent
for _src in ["libs/cci-common/src", "services/coherence/src"]:
    sys.path.insert(0, str(_REPO / _src))

from cci_coherence.entity_extractor import extract_entities
from cci_coherence.rule_evaluator import evaluate_rule

FIXTURES_BASE = _REPO / "tests" / "fixtures"
ONTOLOGIES_DIR = _REPO / "docs" / "ontologies"
DEMO_OUTPUT = _REPO / "demo_output"

DOMAIN_CONFIG = {
    "hera_it": {
        "label": "Hera Group IT — Multi-Cloud Q1 2026",
        "expected": {
            "R001": ("Azure commitment 580k EUR > allocation CTO 500k EUR", "HIGH"),
            "R002": ("ISO 27001 scade 2026-03-31, commitment Azure copre 2026-12-31", "CRITICAL"),
            "R003": ("Totale multi-cloud 855k EUR > budget CdA 800k EUR", "HIGH"),
        },
        "expected_ok": [("R004", "Azure 67.8% < soglia 70% — nessuna violazione (corretto)")],
    },
    "aou_clinical": {
        "label": "AOU Modena — Sperimentazione clinica 2026",
        "expected": {
            "C001": ("Trial AOU-MO-2026-003 ACTIVE, approvazione AVEN scaduta 2025-12-31", "CRITICAL"),
        },
        "expected_ok": [],
    },
    "semsotec_product": {
        "label": "SEMSOTEC — Valvola VP3000 certificazione CE 2026",
        "expected": {
            "P001": ("VP3000-SS-DN80 ON_MARKET, cert TÜV-CE-2023-00891 scaduta 2025-05-31", "HIGH"),
        },
        "expected_ok": [],
    },
    "ducati_corse": {
        "label": "Ducati Corse — MotoGP 2026 compliance",
        "expected": {
            "DC001": ("Motore DC-ENG-2026-V4-REV3 IN_RACE, omologazione FIM valida fino 2025-12-31", "CRITICAL"),
            "DC002": ("Budget cap 13.2M EUR > limite FIM 12M EUR", "HIGH"),
            "DC003": ("Development tokens 2026: 3/3 usati — zero margine", "HIGH"),
        },
        "expected_ok": [],
    },
    "dallara": {
        "label": "Dallara — IR18 IndyCar 2026 crash test",
        "expected": {
            "DA001": ("DAL-IR18-2026-001 IN_COMPETITION, crash test FIA scaduto 2025-12-31", "CRITICAL"),
        },
        "expected_ok": [],
    },
    "prada": {
        "label": "Prada Group — DPP & Supply Chain FW2026",
        "expected": {
            "PR002": ("MBM Manifattura tier 1, audit etico PENDING", "HIGH"),
            "PR003": ("Conceria Walpier, cert LWG Gold scaduta 2025-10-31", "HIGH"),
        },
        "expected_ok": [],
    },
}


def load_fixture_chunks(domain: str) -> list[dict]:
    base = FIXTURES_BASE / domain
    chunks = []
    for f in sorted(base.glob("*.txt")):
        text = f.read_text(encoding="utf-8")
        chunks.append({"chunk_id": f"chunk_{f.stem}", "text": text})
        print(f"    Loaded: {f.name} ({len(text)} chars)")
    return chunks


def load_ontology_rules(domain: str) -> list[dict]:
    import yaml
    path = ONTOLOGIES_DIR / f"{domain}.yaml"
    with path.open() as fh:
        data = yaml.safe_load(fh)
    return [
        {"rule_id": r["id"], "when": r["when"], "severity": r["severity"]}
        for r in data.get("rules", [])
    ]


def run_domain(domain: str) -> dict:
    cfg = DOMAIN_CONFIG[domain]
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  {cfg['label']}")
    print(f"  Domain: {domain}")
    print(f"{sep}")

    t0 = time.time()

    print(f"\n  [1] Loading fixtures...")
    chunks = load_fixture_chunks(domain)
    print(f"  → {len(chunks)} fixture files")

    print(f"\n  [2] Loading ontology {domain}.yaml...")
    rules = load_ontology_rules(domain)
    print(f"  → {len(rules)} rules: {[r['rule_id'] for r in rules]}")

    print(f"\n  [3] Extracting entities (zero LLM — R4)...")
    ctx = extract_entities(chunks, domain)
    for etype, entities in ctx.entities_by_type.items():
        print(f"    {etype}: {len(entities)}")

    print(f"\n  [4] Evaluating rules (deterministic, R4)...")
    all_violations = []
    for rule in rules:
        violations = evaluate_rule(
            rule_id=rule["rule_id"],
            when_expr=rule["when"],
            severity=rule["severity"],
            domain=domain,
            ctx=ctx,
        )
        status = "VIOLAZIONE" if violations else "OK"
        print(f"    [{status:>10}] {rule['rule_id']} (severity={rule['severity']})")
        for v in violations:
            print(f"      → {v.description}")
            print(f"         evidence: {v.evidence_chunks}")
        all_violations.extend(violations)

    elapsed = time.time() - t0

    print(f"\n  [5] Verifica attese")
    print(f"  {'-'*58}")
    expected = cfg["expected"]
    detected_rules = {v.rule_id for v in all_violations}
    passed = 0
    failed = 0

    for rule_id, (desc, _sev) in expected.items():
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

    for rule_id, desc in cfg.get("expected_ok", []):
        rule_has_violation = any(v.rule_id == rule_id for v in all_violations)
        if not rule_has_violation:
            passed += 1
            print(f"  ✓ {rule_id}: {desc}")
        else:
            failed += 1
            print(f"  ✗ {rule_id}: violazione inattesa rilevata!")

    total_checks = len(expected) + len(cfg.get("expected_ok", []))
    print(f"  {'-'*58}")
    chunks_ok = all(len(v.evidence_chunks) > 0 for v in all_violations)
    print(f"  Regole valutate:    {len(rules)}")
    print(f"  Violazioni trovate: {len(all_violations)}")
    print(f"  Verifiche passate:  {passed}/{total_checks}")
    print(f"  Tempo:              {elapsed*1000:.1f}ms")
    print(f"  Evidence chunks:    {'✓' if chunks_ok else '✗'}")

    all_pass = failed == 0
    print(f"\n  {'✓ PASSED' if all_pass else '✗ FAILED'} — {domain}")
    print(f"{sep}")

    result = {
        "domain": domain,
        "scenario": cfg["label"],
        "rules_evaluated": len(rules),
        "incoherences_found": len(all_violations),
        "elapsed_ms": round(elapsed * 1000, 1),
        "passed": all_pass,
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
    out = DEMO_OUTPUT / f"{domain}_coherence_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Output: {out.relative_to(_REPO)}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="CCI/AVCS in-process multi-domain coherence test")
    parser.add_argument(
        "--domain",
        choices=[*DOMAIN_CONFIG.keys(), "all"],
        default="all",
        help="Dominio da testare (default: all)",
    )
    args = parser.parse_args()

    domains = list(DOMAIN_CONFIG.keys()) if args.domain == "all" else [args.domain]

    print("\nCCI/AVCS — In-Process Multi-Domain Coherence Test")
    print("(zero LLM, zero Docker — R4 compliant)")

    results = []
    for d in domains:
        results.append(run_domain(d))

    # Final summary
    sep = "=" * 62
    print(f"\n{sep}")
    print("RIEPILOGO FINALE")
    print(f"{sep}")
    total_violations = sum(r["incoherences_found"] for r in results)
    total_ms = sum(r["elapsed_ms"] for r in results)
    all_passed = all(r["passed"] for r in results)

    for r in results:
        icon = "✓" if r["passed"] else "✗"
        print(f"  {icon} {r['domain']:25s} — incoerenze: {r['incoherences_found']}")

    print(f"\n  Totale incoerenze rilevate: {total_violations}")
    print(f"  Tempo totale:               {total_ms:.1f}ms")
    print(f"\n  {'✓ ALL SCENARIOS PASSED' if all_passed else '✗ SOME SCENARIOS FAILED'}")
    print(f"{sep}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
