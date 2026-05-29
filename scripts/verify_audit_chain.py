"""Verifica integrità della hash chain SHA-256 dell'audit log MongoDB.

Eseguibile con: make verify-audit
Richiede MongoDB attivo e variabile MONGODB_AUDIT_URI.
Implementazione completa in Step 9 (governance-service).
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    uri = os.getenv("MONGODB_AUDIT_URI")
    if not uri:
        print("ERROR: MONGODB_AUDIT_URI non impostata")
        sys.exit(1)
    print("CCI/AVCS — Audit Chain Verifier")
    print("TODO: implementare in Step 9 (cci_governance.audit_log)")
    sys.exit(0)


if __name__ == "__main__":
    main()
