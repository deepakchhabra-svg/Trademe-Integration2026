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


def test_discover_noel_leeming_urls_accepts_max_items_signature():
    # Backwards-compat: older code called discover_noel_leeming_urls(max_items=...).
    from scripts import discover_category
    from scripts import discover_noel_leeming

    # Just ensure signature accepts the arg (we don't hit network here).
    discover_category.discover_noel_leeming_urls("https://example.com", max_pages=1, max_items=10)
    discover_noel_leeming.discover_noel_leeming_urls("https://example.com", max_pages=1, max_items=10)


def test_worker_resolve_command_strips_whitespace():
    from retail_os.trademe.worker import CommandWorker

    class _Cmd:
        type = "ENRICH_SUPPLIER \n"
        payload = {}

    t, payload = CommandWorker.resolve_command(_Cmd())
    assert t == "ENRICH_SUPPLIER"
    assert payload == {}


def test_ops_summary_endpoint_shape(tmp_path: Path):
    """
    Ensure Ops Workbench summary endpoint is stable-shaped.
    """
    import importlib
    import os
    from fastapi.testclient import TestClient

    db_file = tmp_path / "retail_os.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"

    import services.api.main as mod

    importlib.reload(mod)
    client = TestClient(mod.app)
    res = client.get("/ops/summary", headers={"X-RetailOS-Role": "power"})
    assert res.status_code == 200
    data = res.json()
    assert "commands" in data and "vaults" in data and "orders" in data


def test_command_logs_endpoint_shape(tmp_path: Path):
    """
    Regression: per-command logs endpoint should exist and be stable-shaped.
    """
    import importlib
    import os
    from fastapi.testclient import TestClient

    db_file = tmp_path / "retail_os.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"

    import retail_os.core.database as db
    import services.api.main as mod

    importlib.reload(db)
    db.init_db()
    importlib.reload(mod)

    # Seed one command + one log line.
    with db.get_db_session() as session:
        cmd = db.SystemCommand(id="cmd-1", type="TEST_COMMAND", payload={}, status=db.CommandStatus.PENDING, priority=10)
        session.add(cmd)
        session.flush()
        session.add(db.CommandLog(command_id=cmd.id, level="INFO", logger="test", message="hello cmd_id=cmd-1"))

    client = TestClient(mod.app)
    res = client.get("/commands/cmd-1/logs?tail=true&limit=10", headers={"X-RetailOS-Role": "power"})
    assert res.status_code == 200
    data = res.json()
    assert data["command_id"] == "cmd-1"
    assert "next_after_id" in data
    assert "logs" in data


def test_supplier_policy_endpoints(tmp_path: Path):
    """
    Regression: per-supplier policy endpoints exist and are stable-shaped.
    """
    import importlib
    import os
    from fastapi.testclient import TestClient

    db_file = tmp_path / "retail_os.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"

    import retail_os.core.database as db
    import services.api.main as mod

    importlib.reload(db)
    db.init_db()

    # Seed supplier.
    with db.get_db_session() as session:
        s = session.query(db.Supplier).filter(db.Supplier.name == "ONECHEQ").first()
        if not s:
            s = db.Supplier(name="ONECHEQ", base_url="https://example.com", is_active=True)
            session.add(s)
            session.flush()
        supplier_id = int(s.id)

    importlib.reload(mod)
    client = TestClient(mod.app)

    # GET policy (power)
    r1 = client.get(f"/suppliers/{supplier_id}/policy", headers={"X-RetailOS-Role": "power"})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["supplier_id"] == supplier_id
    assert "policy" in j1 and isinstance(j1["policy"], dict)

    # PUT policy (root)
    r2 = client.put(
        f"/suppliers/{supplier_id}/policy",
        headers={"X-RetailOS-Role": "root"},
        json={"policy": {"enabled": False, "scrape": {"enabled": False, "category_presets": ["a", "b"]}}},
    )
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["policy"]["enabled"] is False
    assert j2["policy"]["scrape"]["enabled"] is False


def test_onecheq_normalize_sku_alnum_upper():
    from retail_os.scrapers.onecheq.scraper import normalize_sku

    assert normalize_sku(" LOT731 ") == "LOT731"
    assert normalize_sku("SKU: lot-731") == "LOT731"
    assert normalize_sku("OC-LOT731") == "OCLOT731"  # prefixes are handled elsewhere; normalize is alnum-only.
    assert normalize_sku("nothing-phone-2-5g") == "NOTHINGPHONE25G"

