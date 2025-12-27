import os

import pytest


@pytest.mark.live
def test_live_onecheq_scrape_writes_db():
    # Real code, real site. Requires outbound network.
    from retail_os.core.database import init_db, SessionLocal, Supplier, SupplierProduct
    from retail_os.scrapers.onecheq.adapter import OneCheqAdapter

    init_db()

    # Use a real collection handle if provided, else default "all" (may be slow/large).
    collection = os.getenv("RETAILOS_ONECHEQ_COLLECTION", "all")
    pages = int(os.getenv("RETAILOS_ONECHEQ_PAGES", "1"))

    OneCheqAdapter().run_sync(pages=pages, collection=collection)

    session = SessionLocal()
    try:
        supplier = session.query(Supplier).filter(Supplier.name == "ONECHEQ").first()
        assert supplier is not None
        count = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier.id).count()
        assert count > 0
    finally:
        session.close()


@pytest.mark.live
def test_live_cash_converters_scrape_writes_db():
    from retail_os.core.database import init_db, SessionLocal, Supplier, SupplierProduct
    from retail_os.scrapers.cash_converters.adapter import CashConvertersAdapter

    init_db()

    browse_url = os.getenv(
        "RETAILOS_CC_BROWSE_URL",
        "https://shop.cashconverters.co.nz/Browse/R160787-R160789/North_Island-Auckland",
    )
    pages = int(os.getenv("RETAILOS_CC_PAGES", "1"))

    CashConvertersAdapter().run_sync(pages=pages, browse_url=browse_url)

    session = SessionLocal()
    try:
        supplier = session.query(Supplier).filter(Supplier.name == "CASH_CONVERTERS").first()
        assert supplier is not None
        count = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier.id).count()
        assert count > 0
    finally:
        session.close()


@pytest.mark.live
def test_live_noel_leeming_scrape_writes_db():
    # NOTE: Noel Leeming scraper is selenium-based and requires a working browser/driver.
    # Noel Leeming blocks some hosted environments (HTTP 403). If blocked, this run is not feasible.
    from retail_os.core.database import init_db, SessionLocal, Supplier, SupplierProduct
    from retail_os.scrapers.noel_leeming.adapter import NoelLeemingAdapter

    init_db()

    category_url = os.getenv(
        "RETAILOS_NL_CATEGORY_URL",
        "https://www.noelleeming.co.nz/shop/computers-office-tech/computers",
    )
    pages = int(os.getenv("RETAILOS_NL_PAGES", "1"))

    try:
        NoelLeemingAdapter().run_sync(pages=pages, category_url=category_url, deep_scrape=False, headless=True)
    except RuntimeError as e:
        if "HTTP 403" in str(e):
            pytest.skip(str(e))
        raise

    session = SessionLocal()
    try:
        supplier = session.query(Supplier).filter(Supplier.name == "NOEL_LEEMING").first()
        assert supplier is not None
        count = session.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier.id).count()
        assert count > 0
    finally:
        session.close()


@pytest.mark.live
def test_live_trademe_account_summary():
    # Real code, real credentials (must be present in env).
    # This is non-destructive.
    from retail_os.trademe.api import TradeMeAPI

    if not all(
        [
            os.getenv("CONSUMER_KEY"),
            os.getenv("CONSUMER_SECRET"),
            os.getenv("ACCESS_TOKEN"),
            os.getenv("ACCESS_TOKEN_SECRET"),
        ]
    ):
        pytest.skip("Trade Me credentials not set in environment")

    api = TradeMeAPI()
    summary = api.get_account_summary()
    assert isinstance(summary, dict)
    # Must at least return something stable-shaped
    assert "account_balance" in summary or "balance" in summary

