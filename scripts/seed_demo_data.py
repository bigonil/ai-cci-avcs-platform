"""Seed demo data — fixture Hera Q1 2026.

Crea i documenti di test in tests/fixtures/ per lo scenario pilota.
"""
from __future__ import annotations

import pathlib

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "tests" / "fixtures"


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    # Placeholder: i fixture PDF/DOCX reali vengono aggiunti in Step 11
    print(f"Fixture directory ready: {FIXTURES_DIR}")
    print("TODO: add PDF/DOCX fixtures in Step 11")


if __name__ == "__main__":
    main()
