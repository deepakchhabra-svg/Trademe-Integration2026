"""
Minimal test-framework DB adapter used by the Streamlit requirements dashboard.

This is *not* a mock: it's a small persistence layer that creates the tables
expected by `retail_os/dashboard/test_dashboard.py` so imports and the dashboard work.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


__test__ = False  # prevent pytest from collecting this module as tests


@dataclass
class TestDatabase:
    """
    Stores test run/results in a local sqlite DB.
    Default path: /workspace/data/test_results.db (repo-root anchored).
    """

    db_path: str | None = None
    __test__ = False  # prevent pytest from collecting as a test class

    def __post_init__(self) -> None:
        if not self.db_path:
            repo_root = Path(__file__).resolve().parent.parent
            data_dir = repo_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "test_results.db")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        assert self.db_path is not None
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_name TEXT,
                  started_at TEXT,
                  completed_at TEXT,
                  status TEXT,
                  total_requirements INTEGER,
                  total_tests INTEGER,
                  passed INTEGER,
                  failed INTEGER,
                  blocked INTEGER,
                  partial INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_results (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id INTEGER,
                  requirement_id TEXT,
                  module TEXT,
                  test_case_name TEXT,
                  category TEXT,
                  status TEXT,
                  message TEXT,
                  executed_at TEXT,
                  FOREIGN KEY(run_id) REFERENCES test_runs(id)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

