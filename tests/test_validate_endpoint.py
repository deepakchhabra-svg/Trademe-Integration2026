import importlib
import os
from pathlib import Path


def test_validate_endpoint_enforces_trust_gate_by_default(tmp_path: Path, monkeypatch):
    """
    Regression: production validate endpoint must NOT bypass trust gate.

    It may only bypass when:
    - ?test_bypass=1 AND
    - RETAIL_OS_ALLOW_TEST_BYPASS=1
    """
    from fastapi.testclient import TestClient

    db_file = tmp_path / "retail_os.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("RETAIL_OS_POWER_TOKEN", "test-power")
    monkeypatch.delenv("RETAIL_OS_ALLOW_TEST_BYPASS", raising=False)

    import retail_os.core.database as db
    import services.api.main as mod

    importlib.reload(db)
    db.init_db()
    importlib.reload(mod)

    # Create a minimal InternalProduct that will fail LaunchLock (no supplier product link).
    with db.get_db_session() as session:
        ip = db.InternalProduct(sku="X-1", title="X", primary_supplier_product_id=None)
        session.add(ip)
        session.flush()
        internal_id = int(ip.id)

    client = TestClient(mod.app)

    # Default path must enforce full gates (so it should fail with a real reason).
    r1 = client.get(f"/validate/internal-products/{internal_id}", headers={"X-RetailOS-Token": "test-power"})
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["internal_product_id"] == internal_id
    assert j1["ok"] is False
    assert isinstance(j1["reason"], str) and j1["reason"]

    # Even with test_bypass=1, unless env allows it, it must still enforce full gates.
    r2 = client.get(f"/validate/internal-products/{internal_id}?test_bypass=1", headers={"X-RetailOS-Token": "test-power"})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["ok"] is False


def test_validate_endpoint_allows_bypass_only_when_env_enabled(tmp_path: Path, monkeypatch):
    from fastapi.testclient import TestClient

    db_file = tmp_path / "retail_os.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("RETAIL_OS_POWER_TOKEN", "test-power")
    monkeypatch.setenv("RETAIL_OS_ALLOW_TEST_BYPASS", "1")

    import retail_os.core.database as db
    import services.api.main as mod

    importlib.reload(db)
    db.init_db()
    importlib.reload(mod)

    # Monkeypatch LaunchLock.validate_publish to assert the bypass flag is only used when expected.
    from retail_os.core.validator import LaunchLock

    called = {"test_mode": None}
    orig = LaunchLock.validate_publish

    def _wrapped(self, product, test_mode=False):
        called["test_mode"] = bool(test_mode)
        # Simulate success regardless; we only care about the flag.
        return True

    monkeypatch.setattr(LaunchLock, "validate_publish", _wrapped, raising=True)

    with db.get_db_session() as session:
        ip = db.InternalProduct(sku="X-2", title="X2", primary_supplier_product_id=None)
        session.add(ip)
        session.flush()
        internal_id = int(ip.id)

    client = TestClient(mod.app)
    r = client.get(f"/validate/internal-products/{internal_id}?test_bypass=1", headers={"X-RetailOS-Token": "test-power"})
    assert r.status_code == 200
    assert called["test_mode"] is True

    # Restore original method to avoid cross-test leakage (defensive; monkeypatch also restores).
    monkeypatch.setattr(LaunchLock, "validate_publish", orig, raising=True)

