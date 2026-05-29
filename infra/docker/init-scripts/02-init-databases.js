// Crea database, utenti e indici per CCI/AVCS
// Eseguito dopo 01-init-replicaset.js

// --- Database cci_governance -------------------------------------------------
const govDb = db.getSiblingDB("cci_governance");

// Utente write-only per audit_log (R5 — audit log immutabile)
// Ha solo insert; update/delete/drop esplicitamente negati a livello di role
govDb.createUser({
  user: "cci_audit_writer",
  pwd: process.env.MONGODB_AUDIT_WRITER_PASSWORD || "changeme_audit",
  roles: [
    {
      role: "read",         // lettura per verifica hash chain
      db: "cci_governance",
    },
  ],
});

// Ruolo custom insert-only su audit_log
govDb.createRole({
  role: "auditLogWriter",
  privileges: [
    {
      resource: { db: "cci_governance", collection: "audit_log" },
      actions: ["insert", "find"],
    },
  ],
  roles: [],
});

govDb.grantRolesToUser("cci_audit_writer", [
  { role: "auditLogWriter", db: "cci_governance" },
]);

// Indici audit_log — unique su seq, event_id, record_hash (tre garanzie indipendenti)
govDb.audit_log.createIndex({ seq: 1 }, { unique: true, name: "audit_log_seq_unique" });
govDb.audit_log.createIndex({ event_id: 1 }, { unique: true, name: "audit_log_event_id_unique" });
govDb.audit_log.createIndex({ record_hash: 1 }, { unique: true, name: "audit_log_record_hash_unique" });
govDb.audit_log.createIndex({ correlation_id: 1 }, { name: "audit_log_correlation_id" });
govDb.audit_log.createIndex({ ts: 1 }, { name: "audit_log_ts" });
govDb.audit_log.createIndex({ event_type: 1 }, { name: "audit_log_event_type" });

// Tail singleton per hash chain (unico punto di sincronizzazione atomica)
govDb.createCollection("audit_log_tail");
govDb.audit_log_tail.createIndex({ _id: 1 }, { unique: true });
govDb.audit_log_tail.insertOne({
  _id: "singleton",
  last_seq: NumberLong(0),
  // 32 zero bytes = GENESIS_HASH (base64: A×43 + =)
  last_hash: BinData(0, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="),
});

// Indice su hitl_actions
govDb.createCollection("hitl_actions");
govDb.hitl_actions.createIndex({ action_id: 1 }, { unique: true, name: "hitl_action_id_unique" });
govDb.hitl_actions.createIndex({ status: 1, created_at: -1 }, { name: "hitl_status_ts" });

// Collection LangGraph checkpoints
govDb.createCollection("langgraph_checkpoints");
govDb.langgraph_checkpoints.createIndex(
  { thread_id: 1, checkpoint_id: 1 },
  { unique: true, name: "lg_checkpoint_pk" }
);

print("cci_governance: database, user, ruoli e indici creati");

// --- Database cci_operational ------------------------------------------------
const opDb = db.getSiblingDB("cci_operational");

// Utente applicativo con accesso lettura/scrittura su cci_operational
opDb.createUser({
  user: "cci_app",
  pwd: process.env.MONGODB_APP_PASSWORD || "changeme_app",
  roles: [{ role: "readWrite", db: "cci_operational" }],
});

// Time-series collection per KPI e metriche
opDb.createCollection("metrics", {
  timeseries: {
    timeField: "ts",
    metaField: "meta",
    granularity: "hours",
  },
  expireAfterSeconds: 7776000, // 90 giorni
});

// Collection documenti operativi
opDb.documents.createIndex({ document_id: 1 }, { unique: true });
opDb.documents.createIndex({ domain: 1, ingested_at: -1 });
opDb.documents.createIndex({ "metadata.source_type": 1 });

print("cci_operational: database, user e indici creati");
