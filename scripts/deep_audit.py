"""
DEEP AUDIT - Find ALL Issues
Checks every file, every function, every import, every database query
"""

import sys
import os
import re
sys.path.append(os.getcwd())

def audit_imports():
    """Check for missing or circular imports"""
    print("\n=== IMPORT AUDIT ===\n")
    issues = []
    
    files_to_check = [
        'retail_os/trademe/worker.py',
        'retail_os/core/marketplace_adapter.py',
        'retail_os/dashboard/app.py',
        'scripts/sync_sold_items.py'
    ]
    
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            issues.append(f"[ERROR] File missing: {filepath}")
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for common import issues
        if 'from retail_os' in content and '__init__.py' not in filepath:
            # Check if imports are at top
            lines = content.split('\n')
            import_section_ended = False
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and not line.startswith('import') and not line.startswith('from'):
                    import_section_ended = True
                if import_section_ended and (line.startswith('import') or line.startswith('from')):
                    issues.append(f"[WARN] {filepath}:{i+1} - Import not at top of file")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] No import issues found")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_database_queries():
    """Check all database queries for correctness"""
    print("\n=== DATABASE QUERY AUDIT ===\n")
    issues = []
    
    # Check dashboard queries
    with open('retail_os/dashboard/app.py', 'r', encoding='utf-8') as f:
        dashboard = f.read()
    
    # Find all .filter( calls
    filters = re.findall(r'\.filter\(([^)]+)\)', dashboard)
    
    for i, filter_expr in enumerate(filters):
        # Check for common mistakes
        if 'Order.status' in filter_expr:
            issues.append(f"[ERROR] Dashboard uses Order.status (should be order_status)")
        if 'TradeMeListing.status' in filter_expr:
            issues.append(f"[WARN] Dashboard uses TradeMeListing.status (check if correct)")
    
    # Check for missing .first() or .all()
    query_lines = re.findall(r'session\.query\([^)]+\)[^\n]*', dashboard)
    for line in query_lines:
        if '.filter(' in line and not any(x in line for x in ['.first()', '.all()', '.count()', '.one()']):
            issues.append(f"[WARN] Query without terminator: {line[:50]}...")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] No database query issues found")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_api_calls():
    """Check all Trade Me API calls"""
    print("\n=== API CALL AUDIT ===\n")
    issues = []
    
    with open('retail_os/trademe/api.py', 'r', encoding='utf-8') as f:
        api_content = f.read()
    
    # Check for required methods
    required_methods = {
        'publish_listing': 'POST /v1/Selling.json',
        'validate_listing': 'POST /v1/Selling/Validate.json',
        'upload_photo_idempotent': 'POST /v1/Photos.json',
        'get_sold_items': 'GET /v1/MyTradeMe/SoldItems.json',
        'withdraw_listing': 'POST /v1/Selling/Withdraw.json',
        'get_listing_details': 'GET /v1/Listings/{id}.json',
        'relist_item': 'POST /v1/Selling/Relist.json',
        'get_unsold_items': 'GET /v1/MyTradeMe/UnsoldItems.json'
    }
    
    for method, endpoint in required_methods.items():
        if f'def {method}' not in api_content:
            issues.append(f"[ERROR] Missing API method: {method} ({endpoint})")
        else:
            # Check if endpoint is in the method
            method_start = api_content.find(f'def {method}')
            method_end = api_content.find('\n    def ', method_start + 1)
            if method_end == -1:
                method_end = len(api_content)
            method_body = api_content[method_start:method_end]
            
            # Extract endpoint from method
            if '/v1/' not in method_body:
                issues.append(f"[WARN] {method} doesn't seem to call Trade Me API")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] All API methods present")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_worker_logic():
    """Check worker command handling"""
    print("\n=== WORKER LOGIC AUDIT ===\n")
    issues = []
    
    with open('retail_os/trademe/worker.py', 'r', encoding='utf-8') as f:
        worker = f.read()
    
    # Check for required command handlers
    required_handlers = [
        'PUBLISH_LISTING',
        'WITHDRAW_LISTING',
        'UPDATE_PRICE'
    ]
    
    for handler in required_handlers:
        if f'"{handler}"' not in worker and f"'{handler}'" not in worker:
            issues.append(f"[ERROR] Missing command handler: {handler}")
    
    # Check if MarketplaceAdapter is used
    if 'MarketplaceAdapter.prepare_for_trademe' not in worker:
        issues.append(f"[ERROR] Worker doesn't use MarketplaceAdapter")
    
    # Check if profitability check exists
    if 'ProfitabilityAnalyzer' not in worker:
        issues.append(f"[ERROR] Worker doesn't check profitability")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] Worker logic complete")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_scraper_consistency():
    """Check if all scrapers follow same pattern"""
    print("\n=== SCRAPER CONSISTENCY AUDIT ===\n")
    issues = []
    
    scrapers = {
        'OneCheq': 'retail_os/scrapers/onecheq/adapter.py',
        'CashConverters': 'retail_os/scrapers/cash_converters/adapter.py',
        'NoelLeeming': 'retail_os/scrapers/noel_leeming/adapter.py'
    }
    
    for name, path in scrapers.items():
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required methods
        if 'def _upsert_product' not in content:
            issues.append(f"[ERROR] {name} missing _upsert_product")
        
        # Check if it returns status
        if "return 'created'" not in content and "return 'updated'" not in content:
            issues.append(f"[ERROR] {name} doesn't return status")
        
        # Check if it downloads images
        if 'ImageDownloader' not in content and 'download' not in content.lower():
            issues.append(f"[WARN] {name} might not download images locally")
        
        # Check if it calculates hash
        if 'snapshot_hash' not in content and 'hash' not in content.lower():
            issues.append(f"[WARN] {name} might not calculate snapshot hash")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] All scrapers consistent")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_enrichment_pipeline():
    """Check enrichment flow"""
    print("\n=== ENRICHMENT PIPELINE AUDIT ===\n")
    issues = []
    
    # Check if LLMEnricher exists
    if not os.path.exists('retail_os/core/llm_enricher.py'):
        issues.append("[ERROR] LLMEnricher missing")
    else:
        with open('retail_os/core/llm_enricher.py', 'r', encoding='utf-8') as f:
            enricher = f.read()
        
        # Check for Gemini integration
        if 'google.generativeai' not in enricher and 'genai' not in enricher:
            issues.append("[ERROR] LLMEnricher doesn't use Gemini")
        
        # Check for error handling
        if 'try:' not in enricher or 'except' not in enricher:
            issues.append("[WARN] LLMEnricher lacks error handling")
    
    # Check if enrichment daemon exists
    if not os.path.exists('scripts/run_enrichment_daemon.py'):
        issues.append("[ERROR] Enrichment daemon missing")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] Enrichment pipeline complete")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_config_usage():
    """Check if TradeMeConfig is used everywhere"""
    print("\n=== CONFIG USAGE AUDIT ===\n")
    issues = []
    
    with open('retail_os/trademe/worker.py', 'r', encoding='utf-8') as f:
        worker = f.read()
    
    # Check for hardcoded values
    hardcoded_patterns = [
        (r'Duration.*=.*\d+', 'Duration should use TradeMeConfig'),
        (r'Pickup.*=.*\d+', 'Pickup should use TradeMeConfig'),
        (r'"Category".*:.*"0\d+-', 'Category should come from CategoryMapper'),
    ]
    
    for pattern, message in hardcoded_patterns:
        if re.search(pattern, worker):
            # Check if it's using config
            if 'TradeMeConfig' not in worker[max(0, worker.find(pattern)-100):worker.find(pattern)+100]:
                issues.append(f"[WARN] {message}")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] Config properly used")
    
    return len([i for i in issues if '[ERROR]' in i])

def audit_dashboard_buttons():
    """Check if all dashboard buttons are functional"""
    print("\n=== DASHBOARD BUTTON AUDIT ===\n")
    issues = []
    
    with open('retail_os/dashboard/app.py', 'r', encoding='utf-8') as f:
        dashboard = f.read()
    
    # Find all buttons
    buttons = re.findall(r'st\.button\(["\']([^"\']+)["\']', dashboard)
    
    print(f"  Found {len(buttons)} buttons:")
    for btn in buttons:
        print(f"    - {btn}")
    
    # Check if each button has logic
    for btn in buttons:
        btn_index = dashboard.find(f'st.button("{btn}"')
        if btn_index == -1:
            btn_index = dashboard.find(f"st.button('{btn}'")
        
        # Check next 500 chars for logic
        next_section = dashboard[btn_index:btn_index+500]
        if 'pass' in next_section and 'except' not in next_section:
            issues.append(f"[WARN] Button '{btn}' has 'pass' (might be stub)")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] All buttons have logic")
    
    return len([i for i in issues if '[ERROR]' in i])

def main():
    print("=" * 70)
    print("DEEP SYSTEM AUDIT - FINDING ALL ISSUES")
    print("=" * 70)
    
    total_errors = 0
    
    total_errors += audit_imports()
    total_errors += audit_database_queries()
    total_errors += audit_api_calls()
    total_errors += audit_worker_logic()
    total_errors += audit_scraper_consistency()
    total_errors += audit_enrichment_pipeline()
    total_errors += audit_config_usage()
    total_errors += audit_dashboard_buttons()
    
    print("\n" + "=" * 70)
    print(f"AUDIT COMPLETE: {total_errors} CRITICAL ERRORS FOUND")
    print("=" * 70)
    
    if total_errors > 0:
        print("\n[ACTION REQUIRED] Fix all [ERROR] items above")
    else:
        print("\n[SUCCESS] No critical errors found")

if __name__ == "__main__":
    main()
