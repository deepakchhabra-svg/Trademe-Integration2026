import importlib
import os
import sqlite3
from pathlib import Path


def _reload_database_module(tmp_db_url: str):
    # Ensure module reads DATABASE_URL fresh on import.
    os.environ["DATABASE_URL"] = tmp_db_url
    import retail_os.core.database as dbmod

    return importlib.reload(dbmod)


def test_sqlite_auto_migration_adds_source_category(tmp_path: Path):
    """
    Regression test for Windows/local dev:
    older sqlite DB may be missing newly-added columns, causing 500s on /vaults/raw.
    """
    db_file = tmp_path / "retail_os.db"

    # Create an "old" supplier_products table WITHOUT source_category.
    con = sqlite3.connect(str(db_file))
    try:
        con.execute(
            """
            CREATE TABLE suppliers (
              id INTEGER PRIMARY KEY,
              name VARCHAR UNIQUE,
              base_url VARCHAR,
              is_active BOOLEAN
            );
            """
        )
        con.execute(
            """
            CREATE TABLE supplier_products (
              id INTEGER PRIMARY KEY,
              supplier_id INTEGER,
              external_sku VARCHAR NOT NULL,
              title VARCHAR,
              description TEXT,
              cost_price NUMERIC(10,2),
              stock_level INTEGER,
              product_url VARCHAR,
              images JSON,
              specs JSON,
              enrichment_status VARCHAR,
              enrichment_error TEXT,
              enriched_title VARCHAR,
              enriched_description TEXT,
              last_scraped_at DATETIME,
              snapshot_hash VARCHAR,
              sync_status VARCHAR
            );
            """
        )
        con.commit()
    finally:
        con.close()

    dbmod = _reload_database_module(f"sqlite:///{db_file.as_posix()}")
    dbmod.init_db()

    con = sqlite3.connect(str(db_file))
    try:
        cols = {row[1] for row in con.execute("PRAGMA table_info(supplier_products)").fetchall()}
        assert "source_category" in cols
    finally:
        con.close()


def test_public_image_urls_maps_local_media_paths():
    from services.api import main as api

    assert api._public_image_urls([]) == []
    assert api._public_image_urls(["https://example.com/x.jpg"]) == ["https://example.com/x.jpg"]
    assert api._public_image_urls(["data/media/a.jpg"]) == ["/media/a.jpg"]
    assert api._public_image_urls([r"data\media\b.jpg"]) == ["/media/b.jpg"]
    assert api._public_image_urls([r"/tmp/something/else.jpg"]) == []

