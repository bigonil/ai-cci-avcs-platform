---
name: cci-audit-chain
description: Use this skill whenever you write, modify, or debug code that logs decisions, agent transitions, LLM calls, HITL approvals, or any auditable event in CCI/AVCS. Trigger on files under services/governance/, on file names like audit_log.py, audit_agent.py, verify_audit_chain.py, on MongoDB operations involving the audit_log collection, on imports of hashlib, motor, or pymongo for governance, on mentions of "audit trail", "hash chain", "append-only", "immutable log", "tamper-evident", "ISO 42001 record keeping", "art. 12 AI Act". This skill enforces that NO document in the audit_log collection is mutable and that the SHA-256 hash chain is unbreakable end-to-end on MongoDB.
license: Internal — CCI/AVCS Project
---

# CCI/AVCS Audit Chain (MongoDB)

L'audit log non è "un sistema di logging". È **prova legale**. Una volta scritto, un documento non si modifica, non si cancella, non si "corregge". Si appende un nuovo documento che annulla o supersedes il precedente, e la catena di hash deve sempre verificare.

## Garanzie del sistema

1. **Append-only**: solo `insertOne` / `insertMany`, mai `updateOne`, mai `deleteOne`, mai `replaceOne`, mai `findOneAndUpdate`, mai `drop`
2. **Tamper-evident**: ogni documento contiene l'hash del precedente; modifica → catena rotta → integrità verifica fallisce
3. **Order-preserving**: monotonic `seq` field, timestamp UTC, indice unique
4. **Self-verifiable**: lo script `verify_audit_chain.py` ricalcola tutti gli hash e conferma integrità

## Database setup (init script)

Lo script `infra/docker/mongo-init/02-audit-log.js` viene eseguito al boot di MongoDB e configura la collection audit log con tutte le garanzie strutturali.

```javascript
// infra/docker/mongo-init/02-audit-log.js
// Init script: runs once on a fresh MongoDB replica set primary.
// Requires the replica set to be already initialized (see 01-init-rs.js).

const governanceDb = db.getSiblingDB("cci_governance");

// 1. Create the audit_log collection with a validator schema
governanceDb.createCollection("audit_log", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["seq", "event_id", "ts", "actor", "event_type", "payload", "prev_hash", "record_hash"],
      properties: {
        seq:           { bsonType: "long" },
        event_id:      { bsonType: "binData" },          // UUID v4 (BSON subtype 4)
        correlation_id:{ bsonType: ["binData", "null"] },
        ts:            { bsonType: "date" },              // UTC
        actor:         { bsonType: "string" },
        event_type:    { bsonType: "string" },
        payload:       { bsonType: "object" },
        prev_hash:     { bsonType: "binData" },          // 32 bytes SHA-256
        record_hash:   { bsonType: "binData" },          // 32 bytes SHA-256
        schema_version:{ bsonType: "string" }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// 2. Indexes
governanceDb.audit_log.createIndex({ seq: 1 }, { unique: true, name: "seq_unique" });
governanceDb.audit_log.createIndex({ event_id: 1 }, { unique: true, name: "event_id_unique" });
governanceDb.audit_log.createIndex({ record_hash: 1 }, { unique: true, name: "record_hash_unique" });
governanceDb.audit_log.createIndex({ correlation_id: 1 }, { name: "correlation_idx" });
governanceDb.audit_log.createIndex({ ts: 1 }, { name: "ts_idx" });
governanceDb.audit_log.createIndex({ event_type: 1 }, { name: "event_type_idx" });

// 3. Tail document for hash-chain anchoring (atomic findOneAndUpdate target)
governanceDb.createCollection("audit_log_tail");
governanceDb.audit_log_tail.insertOne({
  _id: "singleton",
  last_seq: NumberLong(0),
  last_hash: BinData(0, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")  // 32 zero bytes = GENESIS_HASH
});

// 4. Create a write-only DB user for the governance service
// (this user can insertOne / insertMany only; not update, not delete, not drop)
governanceDb.runCommand({
  createRole: "audit_log_writer",
  privileges: [{
    resource: { db: "cci_governance", collection: "audit_log" },
    actions:  [ "insert", "find" ]  // 'find' is required for the chain verification script
  }, {
    resource: { db: "cci_governance", collection: "audit_log_tail" },
    actions:  [ "find", "update" ]  // need update only on the tail singleton
  }],
  roles: []
});

governanceDb.runCommand({
  createUser: "cci_audit_writer",
  pwd: passwordPrompt(),    // or via Vault-injected env var in production
  roles: [{ role: "audit_log_writer", db: "cci_governance" }]
});

print("✓ audit_log collection configured (write-only, validated, indexed)");
```

**Punti critici dello schema**:
- Validator strict → MongoDB rifiuta documenti non conformi a livello server
- Indici unique su `seq`, `event_id`, `record_hash` → tre garanzie indipendenti di unicità
- Ruolo `audit_log_writer` con solo `insert` + `find` → l'applicazione non può fisicamente cancellare o modificare nulla
- Collection `audit_log_tail` con singleton doc → punto di sincronizzazione atomica per la catena hash

## Algoritmo di hash chain

```python
# services/governance/src/cci_governance/audit_log.py
from __future__ import annotations
import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

GENESIS_HASH = b"\x00" * 32
TAIL_DOC_ID = "singleton"


def canonical_json(payload: dict[str, Any]) -> bytes:
    """Stable JSON: sorted keys, no whitespace, UTF-8. Required for hash determinism."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_record_hash(*, prev_hash: bytes, event_id: uuid.UUID, ts: datetime,
                        actor: str, event_type: str, payload: dict) -> bytes:
    h = hashlib.sha256()
    h.update(prev_hash)
    h.update(event_id.bytes)
    h.update(ts.astimezone(timezone.utc).isoformat().encode("ascii"))
    h.update(actor.encode("utf-8"))
    h.update(event_type.encode("utf-8"))
    h.update(canonical_json(payload))
    return h.digest()


class AuditLog:
    """Append-only audit log on MongoDB with SHA-256 hash chain."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db
        self._collection = db.audit_log
        self._tail = db.audit_log_tail
        self._lock = asyncio.Lock()  # intra-process serialization

    async def append(
        self,
        *,
        actor: str,
        event_type: str,
        payload: dict,
        correlation_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        """
        Atomically appends an event to the chain.

        Concurrency strategy:
        - intra-process: asyncio.Lock guards against multi-task races
        - inter-process: findOneAndUpdate on the tail singleton is atomic at the
          MongoDB server level, returning the previous hash AND incrementing seq
          in a single round-trip. No transaction needed for the tail update.
        - The insert into audit_log uses the seq from the tail update; if a
          concurrent writer ALSO grabs the same seq (impossible by design, but
          worth verifying), the unique index on `seq` would raise DuplicateKeyError
          and the operation can be retried.
        """
        async with self._lock:
            event_id = uuid.uuid4()
            ts = datetime.now(timezone.utc)

            # Step 1: atomically advance the tail and read its previous state.
            # This is one server-side operation. The returned doc is the state
            # BEFORE the update, so `last_hash` and `last_seq` are what we need.
            tail_before = await self._tail.find_one_and_update(
                {"_id": TAIL_DOC_ID},
                {"$inc": {"last_seq": 1}},
                return_document=ReturnDocument.BEFORE,
            )
            if tail_before is None:
                raise RuntimeError("audit_log_tail singleton missing — init script not run")

            prev_hash: bytes = tail_before["last_hash"]
            new_seq: int = tail_before["last_seq"] + 1

            # Step 2: compute the new record hash
            record_hash = compute_record_hash(
                prev_hash=prev_hash,
                event_id=event_id,
                ts=ts,
                actor=actor,
                event_type=event_type,
                payload=payload,
            )

            # Step 3: insert the audit document (validator schema enforces shape)
            try:
                await self._collection.insert_one({
                    "seq": new_seq,
                    "event_id": event_id.bytes,        # BSON binData subtype 4 (UUID)
                    "correlation_id": correlation_id.bytes if correlation_id else None,
                    "ts": ts,
                    "actor": actor,
                    "event_type": event_type,
                    "payload": payload,
                    "prev_hash": prev_hash,
                    "record_hash": record_hash,
                    "schema_version": "1.0",
                })
            except DuplicateKeyError as e:
                # This should never happen with the tail-singleton pattern, but if it
                # does we MUST NOT swallow it — it means the chain has forked.
                raise AuditChainCorruption(
                    f"Duplicate key inserting seq={new_seq}: chain integrity at risk"
                ) from e

            # Step 4: commit the new hash to the tail
            await self._tail.update_one(
                {"_id": TAIL_DOC_ID},
                {"$set": {"last_hash": record_hash}},
            )

            return event_id


class AuditChainCorruption(Exception):
    """Raised when the hash chain shows signs of forking or tampering."""
```

**Note critiche sul pattern**:

- `findOneAndUpdate` con `$inc` sul tail singleton è **atomico server-side** — è l'operazione che evita la race condition senza richiedere una transazione esplicita
- Lo schema validator MongoDB rifiuta documenti malformati a livello server, indipendentemente dal client
- `DuplicateKeyError` su `seq` sarebbe sintomo di chain fork → eccezione hard, NON catturare e ignorare
- Niente `MongoClient`/`MongoDatabase` sincroni: il governance service è completamente async (motor)

## Verifica integrità

```python
# scripts/verify_audit_chain.py
from __future__ import annotations
from dataclasses import dataclass, field
from motor.motor_asyncio import AsyncIOMotorDatabase

@dataclass
class BrokenLink:
    seq: int
    reason: str
    expected: str | None = None
    found: str | None = None

@dataclass
class VerificationReport:
    total_records: int = 0
    valid: bool = False
    broken_links: list[BrokenLink] = field(default_factory=list)
    first_seq: int | None = None
    last_seq: int | None = None
    tail_consistent: bool = False


async def verify_chain(db: AsyncIOMotorDatabase) -> VerificationReport:
    report = VerificationReport()
    expected_prev = GENESIS_HASH

    cursor = db.audit_log.find().sort("seq", 1)
    async for doc in cursor:
        report.total_records += 1
        if report.first_seq is None:
            report.first_seq = doc["seq"]
        report.last_seq = doc["seq"]

        # Check prev_hash matches the running chain
        if doc["prev_hash"] != expected_prev:
            report.broken_links.append(BrokenLink(
                seq=doc["seq"],
                reason="prev_hash mismatch with running chain",
                expected=expected_prev.hex(),
                found=doc["prev_hash"].hex(),
            ))
            break

        # Recompute the record hash
        import uuid
        recomputed = compute_record_hash(
            prev_hash=doc["prev_hash"],
            event_id=uuid.UUID(bytes=doc["event_id"]),
            ts=doc["ts"],
            actor=doc["actor"],
            event_type=doc["event_type"],
            payload=doc["payload"],
        )
        if recomputed != doc["record_hash"]:
            report.broken_links.append(BrokenLink(
                seq=doc["seq"],
                reason="record_hash recomputation mismatch",
                expected=recomputed.hex(),
                found=doc["record_hash"].hex(),
            ))
            break

        expected_prev = doc["record_hash"]

    # Check tail singleton is consistent with the actual chain
    tail = await db.audit_log_tail.find_one({"_id": TAIL_DOC_ID})
    if tail:
        report.tail_consistent = (
            tail["last_seq"] == report.last_seq and
            tail["last_hash"] == expected_prev
        )

    report.valid = not report.broken_links and report.tail_consistent
    return report
```

Lo script si esegue:
- Nightly come job batch
- Pre-export per audit esterno
- Su richiesta dell'utente via `make verify-audit`

## Operazioni VIETATE sulla collection `audit_log`

Queste operazioni **non devono mai** comparire nel codice del progetto. Se l'utente le richiede, **rifiuta** e proponi l'alternativa allineata.

| Operazione MongoDB | Perché è vietata | Alternativa allineata |
|---|---|---|
| `audit_log.update_one({...}, ...)` | Mutazione di record passato → rompe la catena hash | `audit_log.insert_one({...event_type: "redaction.applied.v1", ...})` |
| `audit_log.update_many(...)` | Idem, peggio | Idem, evento per ciascuno |
| `audit_log.replace_one(...)` | Equivale a delete+insert → rompe ordering | Idem |
| `audit_log.find_one_and_update(...)` | Idem (modifica in atomic transaction) | NB: `find_one_and_update` è permesso **solo** sul `audit_log_tail`, NON sul `audit_log` |
| `audit_log.delete_one(...)` / `delete_many(...)` | Cancellazione → buco nella sequenza, GDPR-erasure non così | Vedi sezione "Right to erasure" sotto |
| `audit_log.drop()` | Cancellazione totale → distruzione delle prove | Mai. Punto. |
| `audit_log.rename(...)` | Nasconde la collection con stesso effetto | Mai |
| `audit_log.create_index(unique=False)` su `seq` | Permette duplicati → fork silenziosi | Lascia gli indici come da init script |
| Insert con `seq` deciso dall'app (non dal tail) | Bypass dell'atomicità server-side | Usa il pattern `AuditLog.append()` |

## Right to erasure (GDPR) compatibile con catena immutabile

Cancellare un documento dall'audit log è impossibile. Per soddisfare il diritto all'oblio si **appende** un nuovo evento di redazione:

```python
async def request_erasure(
    audit: AuditLog,
    *,
    subject_id: str,
    requester_id: str,
    motivation: str,
) -> uuid.UUID:
    # 1. Redact the actual PII data (Document collection, Qdrant payload, KG Person nodes)
    await pii_redactor.redact(subject_id)

    # 2. Append a redaction event to the audit chain — NEVER mutate past events
    return await audit.append(
        actor="governance-service",
        event_type="gdpr.erasure.executed.v1",
        payload={
            "subject_id_hash": hashlib.sha256(subject_id.encode()).hexdigest(),  # never raw PII
            "requester_id": requester_id,
            "motivation": motivation,
            "redacted_collections": ["documents", "qdrant:hera_it", "neo4j:Person"],
        },
    )
```

Il revisore esterno vede: il record originale ESISTE ancora ma fa riferimento a un soggetto che non è più presente nelle collection operative. La catena resta integra.

## Export firmato per audit esterno

```python
import hmac

async def export_signed(
    db: AsyncIOMotorDatabase,
    start_seq: int,
    end_seq: int,
    signing_key: bytes,
) -> dict:
    cursor = db.audit_log.find({"seq": {"$gte": start_seq, "$lte": end_seq}}).sort("seq", 1)
    records = []
    async for doc in cursor:
        records.append({
            "seq": doc["seq"],
            "event_id": doc["event_id"].hex(),
            "correlation_id": doc["correlation_id"].hex() if doc["correlation_id"] else None,
            "ts": doc["ts"].isoformat(),
            "actor": doc["actor"],
            "event_type": doc["event_type"],
            "payload": doc["payload"],
            "prev_hash": doc["prev_hash"].hex(),
            "record_hash": doc["record_hash"].hex(),
        })
    payload = canonical_json({
        "version": "1.0",
        "start_seq": start_seq,
        "end_seq": end_seq,
        "exported_at": datetime.utcnow().isoformat(),
        "records": records,
    })
    signature = hmac.new(signing_key, payload, hashlib.sha256).hexdigest()
    return {"payload": payload.decode("utf-8"), "hmac_sha256": signature}
```

Il `signing_key` vive in HashiCorp Vault, mai nel codice.

## Eventi audit canonici

Stesso set della versione PostgreSQL — il pattern di nomenclatura `{domain}.{entity}.{action}.v{n}` è invariato:

| event_type | Quando |
|---|---|
| `agent.planner.plan_created.v1` | Planner produce VerificationPlan |
| `agent.retriever.chunks_retrieved.v1` | Retriever completa step |
| `agent.verifier.completed.v1` | Verifier termina |
| `agent.generator.explanation_emitted.v1` | Generator produce output valido |
| `agent.generator.not_emittable.v1` | Grounding fails after retries |
| `llm.call.v1` | Ogni chiamata Anthropic API (in `cci_llm.LLMClient`) |
| `hitl.action.queued.v1` | HITL gate blocca azione |
| `hitl.action.approved.v1` | Human approva |
| `hitl.action.rejected.v1` | Human rifiuta |
| `gdpr.erasure.executed.v1` | Right to erasure eseguito |
| `ontology.<domain>.reloaded.v1` | Hot reload ontologia |
| `compliance.aiact.review.v1` | Periodic AI Act compliance review |

## Anti-pattern da rifiutare immediatamente

| Sintomo | Perché è grave |
|---|---|
| `db.audit_log.update_one(...)` da qualunque codice | Mutazione di evento già loggato → audit perde validità legale |
| `db.audit_log.delete_one(...)` o `delete_many(...)` | Idem |
| `db.audit_log.drop()` | Distruzione totale delle prove |
| `db.audit_log.find_one_and_update(...)` | Mutazione transazionale → idem |
| `db.audit_log.replace_one(...)` | Equivale a delete+insert |
| `mongosh ... --eval "db.audit_log.deleteOne(...)"` da shell | Bypass dell'applicazione, ma il ruolo `audit_log_writer` lo blocca lato server |
| `await audit.append(...)` con `try/except: pass` | Perdi eventi → catena lacunosa |
| Logging via `logging.info(...)` invece di `audit_log.append(...)` per decisioni | Il logging Python è observability, non prova legale |
| Insert senza il pattern del tail singleton | Race condition sotto carico, fork silenziosi |
| JSON non canonico nel payload (`json.dumps` senza `sort_keys`) | Hash diversi per stesso payload → verifica fallisce |
| `correlation_id` mancante su eventi multi-step | Impossibile ricostruire un flusso end-to-end |
| Storare PII in chiaro nel `payload` | Audit log non GDPR-compliant. Usa token o hash. |
| Permettere upgrade dello schema validator MongoDB senza ADR | Rischio di rompere documenti già esistenti |

## Test pattern

```python
import pytest
from testcontainers.mongodb import MongoDbContainer

@pytest.fixture(scope="session")
def mongo_container():
    with MongoDbContainer("mongo:7", replica_set="rs0") as c:
        yield c

@pytest.mark.asyncio
async def test_hash_chain_integrity_under_concurrent_writes(audit_db):
    audit = AuditLog(audit_db)

    async def write_event(i: int):
        await audit.append(
            actor="test-service",
            event_type="test.concurrent.v1",
            payload={"index": i},
        )

    # 100 concurrent appends from different async tasks
    await asyncio.gather(*[write_event(i) for i in range(100)])

    report = await verify_chain(audit_db)
    assert report.valid
    assert report.total_records == 100
    assert report.tail_consistent
    assert not report.broken_links


@pytest.mark.asyncio
async def test_role_rejects_update(audit_db, audit_db_writer_role):
    # Connect as the cci_audit_writer user, NOT admin
    writer_client = AsyncIOMotorClient(audit_db_writer_role.connection_string)
    audit = AuditLog(writer_client.cci_governance)
    event_id = await audit.append(actor="t", event_type="t.v1", payload={})

    # Now try to mutate as the same user → must fail with auth error
    with pytest.raises(OperationFailure, match="not authorized"):
        await writer_client.cci_governance.audit_log.update_one(
            {"event_id": event_id.bytes},
            {"$set": {"payload": {}}},
        )

    with pytest.raises(OperationFailure, match="not authorized"):
        await writer_client.cci_governance.audit_log.delete_one(
            {"event_id": event_id.bytes},
        )
```

## Retention

Default: **5 anni minimum** (AI Act art. 12 + GDPR + audit fiscali italiani). Configurabile in `docs/compliance/retention-policy.yaml`.

La retention non elimina documenti: li sposta in `audit_log_archive` (stessa struttura) tramite un job batch che usa `bulk insert + bulk find` (mai update/delete sull'attiva). La chain prosegue attraverso l'archive.

Per archiviare in modo append-only-coerente con il vincolo immutabilità:
1. Append evento `audit.retention.archive_started.v1` su `audit_log`
2. `audit_log.find({seq: {$lte: cutoff}})` → bulk insert in `audit_log_archive`
3. (Solo dopo verifica integrità sull'archive) richiesta operativa al DBA con autorizzazione DPO + Compliance Officer per il bulk delete dell'intervallo archiviato dalla collection attiva — questo è l'**unico caso autorizzato** di delete su `audit_log`, eseguito offline con ruolo admin temporaneo
4. Append evento `audit.retention.archive_completed.v1` su `audit_log` con hash dell'archive

## Riferimenti
- AI Act art. 12 (Record keeping)
- ISO 42001 § 8.2 (Operational records)
- Documento `CCI_AVCS_Technical_Specifications.html`, sezione §05 (Audit agent)
- MongoDB Schema Validation: https://www.mongodb.com/docs/manual/core/schema-validation/
- MongoDB Role-Based Access Control: https://www.mongodb.com/docs/manual/core/authorization/
- Skill correlate: `cci-ai-act-compliance`, `cci-agentic-langgraph`
