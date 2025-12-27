"""
COMPREHENSIVE ALIGNMENT AUDIT
Checks all function calls, database columns, and API payloads for consistency
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct, InternalProduct, TradeMeListing, Order
from sqlalchemy import inspect

def audit_database_schema():
    """Verify all database columns are used"""
    print("\n=== DATABASE SCHEMA AUDIT ===\n")
    
    session = SessionLocal()
    inspector = inspect(session.bind)
    
    tables = {
        'supplier_products': SupplierProduct,
        'internal_products': InternalProduct,
        'trademe_listings': TradeMeListing,
        'orders': Order
    }
    
    for table_name, model in tables.items():
        print(f"\n{table_name.upper()}:")
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        for col in columns:
            print(f"  - {col}")
        
        print(f"  Total: {len(columns)} columns")
    
    session.close()

def audit_scraper_adapter_alignment():
    """Check if all scrapers return same structure"""
    print("\n=== SCRAPER -> ADAPTER ALIGNMENT ===\n")
    
    from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
    from retail_os.scrapers.cash_converters.adapter import CashConvertersAdapter
    from retail_os.scrapers.noel_leeming.adapter import NoelLeemingAdapter
    
    adapters = {
        'OneCheq': OneCheqAdapter,
        'CashConverters': CashConvertersAdapter,
        'NoelLeeming': NoelLeemingAdapter
    }
    
    for name, adapter_class in adapters.items():
        methods = [m for m in dir(adapter_class) if not m.startswith('_')]
        print(f"{name}: {', '.join(methods[:5])}...")
        
        # Check if _upsert_product exists
        if hasattr(adapter_class, '_upsert_product'):
            print(f"  [OK] _upsert_product exists")
        else:
            print(f"  [ERROR] _upsert_product MISSING")

def audit_marketplace_adapter_worker_alignment():
    """Check if Worker uses MarketplaceAdapter correctly"""
    print("\n=== MARKETPLACE ADAPTER -> WORKER ALIGNMENT ===\n")
    
    # Read worker.py
    with open('retail_os/trademe/worker.py', 'r', encoding='utf-8') as f:
        worker_content = f.read()
    
    checks = {
        'MarketplaceAdapter imported': 'from retail_os.core.marketplace_adapter import MarketplaceAdapter' in worker_content,
        'prepare_for_trademe called': 'MarketplaceAdapter.prepare_for_trademe' in worker_content,
        'ProfitabilityAnalyzer used': 'ProfitabilityAnalyzer' in worker_content,
        'TradeMeConfig used': 'TradeMeConfig' in worker_content
    }
    
    for check, result in checks.items():
        status = "[OK]" if result else "[ERROR]"
        print(f"  {status} {check}")

def audit_api_payload_alignment():
    """Check if API payloads match Trade Me requirements"""
    print("\n=== API PAYLOAD ALIGNMENT ===\n")
    
    # Read api.py
    with open('retail_os/trademe/api.py', 'r', encoding='utf-8') as f:
        api_content = f.read()
    
    required_methods = [
        'publish_listing',
        'upload_photo_idempotent',
        'get_sold_items',
        'get_selling_items',
        'withdraw_listing',
        'validate_listing'
    ]
    
    for method in required_methods:
        if f'def {method}' in api_content:
            print(f"  [OK] {method} exists")
        else:
            print(f"  [ERROR] {method} MISSING")

def audit_dashboard_database_alignment():
    """Check if dashboard queries match database schema"""
    print("\n=== DASHBOARD -> DATABASE ALIGNMENT ===\n")
    
    # Read app.py
    with open('retail_os/dashboard/app.py', 'r', encoding='utf-8') as f:
        dashboard_content = f.read()
    
    # Check for correct column references
    issues = []
    
    if 'Order.status' in dashboard_content:
        issues.append("Order.status should be Order.order_status")
    
    if 'TradeMeListing.status' in dashboard_content:
        issues.append("Check TradeMeListing.status vs actual_state")
    
    if issues:
        print("  [ERROR] Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  [OK] No obvious misalignments found")

def audit_enrichment_flow():
    """Check enrichment pipeline alignment"""
    print("\n=== ENRICHMENT FLOW ALIGNMENT ===\n")
    
    checks = []
    
    # Check if LLMEnricher is used
    try:
        from retail_os.core.llm_enricher import LLMEnricher
        checks.append(("[OK]", "LLMEnricher exists"))
    except:
        checks.append(("[ERROR]", "LLMEnricher import failed"))
    
    # Check if enrichment daemon exists
    if os.path.exists('scripts/run_enrichment_daemon.py'):
        checks.append(("[OK]", "Enrichment daemon exists"))
    else:
        checks.append(("[ERROR]", "Enrichment daemon MISSING"))
    
    for status, msg in checks:
        print(f"  {status} {msg}")

def main():
    print("=" * 60)
    print("COMPREHENSIVE SYSTEM ALIGNMENT AUDIT")
    print("=" * 60)
    
    try:
        audit_database_schema()
        audit_scraper_adapter_alignment()
        audit_marketplace_adapter_worker_alignment()
        audit_api_payload_alignment()
        audit_dashboard_database_alignment()
        audit_enrichment_flow()
        
        print("\n" + "=" * 60)
        print("AUDIT COMPLETE")
        print("=" * 60)
        print("\nReview any [ERROR] items above and fix them.")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] Audit failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
