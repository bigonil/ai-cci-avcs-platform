---
description: Verifica l'integrità della hash chain SHA-256 dell'audit log MongoDB (R5)
---

# /audit-chain-verify

Verifica che la catena di hash dei documenti `audit_log` su MongoDB sia integra end-to-end.

## Cosa fa

1. Esegui lo script di verifica:
   ```bash
   uv run python scripts/verify_audit_chain.py
   ```

   Lo script:
   - Si connette a MongoDB (`MONGODB_URI` da env)
   - Legge tutti i documenti della collection `cci_governance.audit_log` ordinati per `seq` ASC
   - Per ogni documento, ricalcola `record_hash` da `(prev_hash, event_id, ts, actor, event_type, payload)` usando lo stesso algoritmo di `audit_log.py`
   - Verifica che `prev_hash` di ogni documento sia uguale al `record_hash` del precedente
   - Verifica che il primo documento abbia `prev_hash == GENESIS_HASH` (32 zero bytes)
   - Verifica che il singleton `audit_log_tail` sia consistente con la fine della catena

2. Output atteso (catena integra):
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     CCI/AVCS · audit chain integrity check (MongoDB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     MongoDB:          mongodb://mongo:27017/cci_governance
     Collection:       audit_log
     Records examined: 4_823
     First seq:        1
     Last seq:         4823
     Genesis verified: ✓
     Chain integrity:  ✓ ALL RECORDS VALID
     Tail consistent:  ✓ (last_seq=4823, last_hash matches)
     Broken links:     0
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. Se la catena è rotta:
   ```
     Chain integrity:  ❌ BROKEN AT seq=2341
     Broken links:     1
     Reason:           record_hash recomputation mismatch
   ```
   **Non tentare di "riparare" la catena**. Una catena rotta è prova di tampering o di bug critico nel pattern di append (race condition sul `audit_log_tail`, validator schema bypassato, ruolo DB compromesso). Procedere così:
   - Crea un incident ticket immediatamente
   - Esporta i documenti da `seq=1` a `seq=(seq_broken - 1)` come signed export per backup legale
   - Analizza con `git log` se ci sono stati change a `audit_log.py`, alle migration MongoDB o ai ruoli DB
   - Verifica che il singleton `audit_log_tail` non sia stato manipolato (deve avere `_id: "singleton"` e essere l'unico documento della sua collection)
   - Non procedere con nuovi deploy fino a root cause identificata

## Verifica del ruolo DB write-only

Controlla che il ruolo `audit_log_writer` sia configurato correttamente:
```bash
docker compose exec mongo mongosh \
  --quiet \
  --username admin \
  --eval 'use cci_governance; db.getRole("audit_log_writer", {showPrivileges: true})'
```

Output atteso: privilegi `insert` e `find` su `audit_log`; **nessun** `update`, `remove`, `dropCollection`. Se vedi privilegi aggiuntivi, la collection NON è più write-only e va riallineata immediatamente.

## Export firmato (su richiesta auditor)

```bash
uv run python scripts/export_audit_signed.py \
  --start-seq 1 \
  --end-seq 4823 \
  --output exports/audit-2026-q1.json
```

Il file include `hmac_sha256` calcolato con la chiave da Vault. L'auditor riceverà file + chiave separatamente.

## Verifica nightly

Aggiungi al crontab del governance-host:
```cron
0 2 * * * cd /opt/cci-avcs && uv run python scripts/verify_audit_chain.py >> /var/log/cci/audit-verify.log 2>&1
```

Se il check nightly fallisce, alert immediato a SOC + DPO.

## Quando usarlo

- Pre-export per audit esterno
- Dopo deploy che ha toccato `services/governance/`
- Dopo migration MongoDB o cambio di ruoli DB
- Quando un report mostra `correlation_id` con sequenze mancanti
- Periodicamente come parte di compliance review

## Riferimenti
- Skill: `cci-audit-chain`
- Regola: CLAUDE.md §3, R5
- AI Act art. 12 (Record keeping)
- MongoDB schema validation: https://www.mongodb.com/docs/manual/core/schema-validation/
