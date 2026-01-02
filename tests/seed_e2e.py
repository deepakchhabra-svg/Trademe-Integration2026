"""
Offline, idempotent E2E seed for CI/Playwright.

- Creates schema via init_db()
- Seeds minimal rows so "power" pages render without 404/500
- NEVER calls external systems (Trade Me, supplier sites, LLM)
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def main() -> None:
    # Ensure repo root is on sys.path (works from any cwd).
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    db_url = (os.getenv("RETAILOS_E2E_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not db_url:
        raise SystemExit("Missing RETAILOS_E2E_DATABASE_URL (or DATABASE_URL).")

    # Force database module to pick up DATABASE_URL.
    os.environ["DATABASE_URL"] = db_url

    import retail_os.core.database as db

    importlib.reload(db)
    db.init_db()

    with db.get_db_session() as session:
        # Ensure baseline suppliers exist (ids may vary; the UI enumerates by query anyway).
        for name, url in (
            ("ONECHEQ", "https://example.com"),
            ("CASH_CONVERTERS", "https://example.com"),
            ("NOEL_LEEMING", "https://example.com"),
        ):
            s = session.query(db.Supplier).filter(db.Supplier.name == name).first()
            if not s:
                session.add(db.Supplier(name=name, base_url=url, is_active=True))

        # Ensure store mode is NORMAL (publishing endpoints still require real Trade Me creds).
        row = session.query(db.SystemSetting).filter(db.SystemSetting.key == "store.mode").first()
        if not row:
            session.add(db.SystemSetting(key="store.mode", value="NORMAL"))
        else:
            row.value = "NORMAL"

        session.commit()


if __name__ == "__main__":
    main()

