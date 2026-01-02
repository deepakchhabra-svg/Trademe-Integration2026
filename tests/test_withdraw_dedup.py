import importlib
from pathlib import Path


def test_withdraw_unavailable_items_does_not_enqueue_duplicate_withdraws(tmp_path: Path, monkeypatch):
    """
    Safety regression: bulk withdraw removed must not enqueue duplicates if a withdraw is already active.
    """
    db_file = tmp_path / "retail_os.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")

    import retail_os.core.database as db

    importlib.reload(db)
    db.init_db()

    with db.get_db_session() as session:
        # Ensure supplier exists
        s = session.query(db.Supplier).filter(db.Supplier.name == "ONECHEQ").first()
        if not s:
            s = db.Supplier(name="ONECHEQ", base_url="https://example.com", is_active=True)
            session.add(s)
            session.flush()

        sp = db.SupplierProduct(
            supplier_id=int(s.id),
            external_sku="DUP1",
            title="X",
            description="X",
            cost_price=1.0,
            stock_level=0,
            product_url="https://example.com/p/1",
            images=[],
            specs={},
            snapshot_hash="x",
            sync_status="REMOVED",
        )
        session.add(sp)
        session.flush()

        ip = db.InternalProduct(sku="OC-DUP1", title="X", primary_supplier_product_id=sp.id)
        session.add(ip)
        session.flush()

        listing = db.TradeMeListing(
            internal_product_id=ip.id,
            tm_listing_id="12345",
            actual_state="Live",
            desired_state="Live",
        )
        session.add(listing)
        session.flush()

        # Existing active withdraw command for the same listing
        session.add(
            db.SystemCommand(
                id="cmd-existing",
                type="WITHDRAW_LISTING",
                payload={"listing_id": "12345", "reason": "Already queued"},
                status=db.CommandStatus.PENDING,
                priority=10,
            )
        )
        session.commit()

        from retail_os.core.inventory_ops import InventoryOperations

        ops = InventoryOperations(session)
        enqueued = ops.withdraw_unavailable_items(supplier_id=int(s.id))
        assert enqueued == 0

        # Ensure only one withdraw command exists
        total = (
            session.query(db.SystemCommand)
            .filter(db.SystemCommand.type == "WITHDRAW_LISTING")
            .filter(db.SystemCommand.payload.isnot(None))
            .all()
        )
        # Conservative: at least the original exists, but no new duplicate should be added.
        assert len(total) == 1

