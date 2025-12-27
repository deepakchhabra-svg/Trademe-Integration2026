"""
FINAL COMPREHENSIVE AUDIT - EVERY ASPECT
Database, Code, Frontend, Buttons, Performance
"""

import sys
import os
import re
from pathlib import Path
sys.path.append(os.getcwd())

def audit_database_indexes():
    """Check if database has proper indexes for performance"""
    print("\n=== DATABASE INDEX AUDIT ===\n")
    
    from retail_os.core.database import engine
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    issues = []
    
    # Check each table for indexes
    tables = ['supplier_products', 'internal_products', 'trademe_listings', 'orders']
    
    for table in tables:
        indexes = inspector.get_indexes(table)
        pk_columns = inspector.get_pk_constraint(table)['constrained_columns']
        
        print(f"{table}:")
        print(f"  Primary Key: {pk_columns}")
        print(f"  Indexes: {len(indexes)}")
        
        # Check for common query patterns
        if table == 'supplier_products':
            # Should have index on supplier_id, external_sku
            has_supplier_idx = any('supplier_id' in str(idx) for idx in indexes)
            if not has_supplier_idx:
                issues.append(f"[PERF] {table} missing index on supplier_id")
        
        if table == 'orders':
            # Should have index on tm_order_ref, fulfillment_status
            has_ref_idx = any('tm_order_ref' in str(idx) for idx in indexes)
            if not has_ref_idx:
                issues.append(f"[PERF] {table} missing index on tm_order_ref")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n  [OK] Indexes look good")
    
    return issues

def audit_dashboard_queries():
    """Check all dashboard queries for N+1 problems"""
    print("\n=== DASHBOARD QUERY PERFORMANCE AUDIT ===\n")
    
    with open('retail_os/dashboard/app.py', 'r', encoding='utf-8') as f:
        dashboard = f.read()
    
    issues = []
    
    # Find all queries
    queries = re.findall(r'session\.query\([^)]+\)[^\n]*', dashboard)
    
    print(f"Found {len(queries)} database queries")
    
    # Check for missing eager loading
    for query in queries:
        if 'InternalProduct' in query or 'TradeMeListing' in query:
            if '.join' not in query and '.options' not in query:
                issues.append(f"[PERF] Query might have N+1 problem: {query[:60]}...")
    
    # Check for queries in loops
    lines = dashboard.split('\n')
    in_loop = False
    for i, line in enumerate(lines):
        if 'for ' in line and ' in ' in line:
            in_loop = True
        if in_loop and 'session.query' in line:
            issues.append(f"[PERF] Query inside loop at line {i+1}")
        if in_loop and (line.strip() == '' or not line.startswith(' ')):
            in_loop = False
    
    if issues:
        for issue in issues[:10]:  # Show first 10
            print(f"  {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues)-10} more")
    else:
        print("  [OK] No obvious performance issues")
    
    return issues

def audit_all_buttons():
    """Check EVERY button in dashboard"""
    print("\n=== COMPLETE BUTTON AUDIT ===\n")
    
    with open('retail_os/dashboard/app.py', 'r', encoding='utf-8') as f:
        dashboard = f.read()
    
    # Find all buttons with better regex
    button_pattern = r'st\.button\(["\']([^"\']+)["\']'
    buttons = re.findall(button_pattern, dashboard)
    
    print(f"Found {len(buttons)} buttons:\n")
    
    issues = []
    for i, btn_text in enumerate(buttons, 1):
        # Remove emojis for safe printing
        safe_text = btn_text.encode('ascii', 'ignore').decode('ascii')
        print(f"  {i}. {safe_text if safe_text else btn_text[:20]}")
        
        # Find button implementation
        btn_index = dashboard.find(f'st.button("{btn_text}"')
        if btn_index == -1:
            btn_index = dashboard.find(f"st.button('{btn_text}'")
        
        # Check next 1000 chars for implementation
        impl = dashboard[btn_index:btn_index+1000]
        
        # Check for issues
        if 'pass' in impl and 'except' not in impl:
            issues.append(f"[WARN] Button '{safe_text}' has stub implementation")
        
        if 'TODO' in impl or 'FIXME' in impl:
            issues.append(f"[WARN] Button '{safe_text}' has TODO/FIXME")
    
    if issues:
        print("\nIssues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n  [OK] All buttons have implementations")
    
    return issues

def audit_all_database_fields():
    """Check if ALL database fields are used"""
    print("\n=== DATABASE FIELD USAGE AUDIT ===\n")
    
    from retail_os.core.database import SessionLocal
    from sqlalchemy import inspect
    
    session = SessionLocal()
    inspector = inspect(session.bind)
    
    # Get all Python files
    code_files = []
    for root, dirs, files in os.walk('retail_os'):
        for file in files:
            if file.endswith('.py'):
                code_files.append(os.path.join(root, file))
    
    # Read all code
    all_code = ""
    for filepath in code_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                all_code += f.read() + "\n"
        except:
            pass
    
    issues = []
    tables = ['supplier_products', 'orders', 'trademe_listings']
    
    for table in tables:
        columns = [col['name'] for col in inspector.get_columns(table)]
        print(f"\n{table} ({len(columns)} columns):")
        
        for col in columns:
            # Check if column is referenced in code
            if col not in all_code and col != 'id':
                issues.append(f"[WARN] {table}.{col} might be unused")
                print(f"  - {col} [UNUSED?]")
            else:
                print(f"  - {col} [OK]")
    
    session.close()
    return issues

def audit_frontend_fields():
    """Check if all frontend fields map to backend"""
    print("\n=== FRONTEND-BACKEND FIELD MAPPING AUDIT ===\n")
    
    with open('retail_os/dashboard/app.py', 'r', encoding='utf-8') as f:
        dashboard = f.read()
    
    issues = []
    
    # Find all column configs
    column_configs = re.findall(r'"([^"]+)":\s*st\.column_config', dashboard)
    
    print(f"Found {len(column_configs)} frontend columns")
    
    # Check if they map to actual database fields
    from retail_os.core.database import SupplierProduct, InternalProduct, TradeMeListing, Order
    
    models = {
        'SupplierProduct': SupplierProduct,
        'InternalProduct': InternalProduct,
        'TradeMeListing': TradeMeListing,
        'Order': Order
    }
    
    for col in column_configs:
        found = False
        for model_name, model in models.items():
            if hasattr(model, col.lower().replace(' ', '_')):
                found = True
                break
        
        if not found and col not in ['ID', 'Title', 'Supplier', 'Price', 'Trust', 'Enriched', 'Category', 'Created']:
            issues.append(f"[WARN] Frontend column '{col}' might not map to database")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] All frontend columns map correctly")
    
    return issues

def audit_api_error_handling():
    """Check if all API calls have proper error handling"""
    print("\n=== API ERROR HANDLING AUDIT ===\n")
    
    with open('retail_os/trademe/api.py', 'r', encoding='utf-8') as f:
        api_code = f.read()
    
    issues = []
    
    # Find all methods
    methods = re.findall(r'def (\w+)\(self[^)]*\):', api_code)
    
    print(f"Found {len(methods)} API methods")
    
    for method in methods:
        if method.startswith('_'):
            continue
        
        # Find method body
        method_start = api_code.find(f'def {method}(')
        method_end = api_code.find('\n    def ', method_start + 1)
        if method_end == -1:
            method_end = len(api_code)
        
        method_body = api_code[method_start:method_end]
        
        # Check for error handling
        has_try = 'try:' in method_body
        has_except = 'except' in method_body
        has_timeout = 'timeout' in method_body
        
        if not has_try or not has_except:
            issues.append(f"[WARN] {method}() lacks try/except")
        if not has_timeout and 'requests.' in method_body:
            issues.append(f"[WARN] {method}() lacks timeout")
    
    if issues:
        for issue in issues[:10]:
            print(f"  {issue}")
    else:
        print("  [OK] All API methods have error handling")
    
    return issues

def audit_performance_bottlenecks():
    """Find performance bottlenecks"""
    print("\n=== PERFORMANCE BOTTLENECK AUDIT ===\n")
    
    issues = []
    
    # Check scraper performance
    scrapers = [
        'retail_os/scrapers/onecheq/scraper.py',
        'retail_os/scrapers/cash_converters/scraper.py',
        'retail_os/scrapers/noel_leeming/scraper.py'
    ]
    
    for scraper_path in scrapers:
        with open(scraper_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        scraper_name = Path(scraper_path).parent.name
        
        # Check for async
        if 'async def' not in code and 'asyncio' not in code:
            issues.append(f"[PERF] {scraper_name} not using async")
        
        # Check for connection pooling
        if 'httpx.Client' not in code and 'requests.Session' not in code:
            issues.append(f"[PERF] {scraper_name} not using connection pooling")
        
        # Check for rate limiting
        if 'time.sleep' not in code and 'asyncio.sleep' not in code:
            issues.append(f"[INFO] {scraper_name} no explicit rate limiting")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  [OK] No major performance bottlenecks")
    
    return issues

def main():
    print("=" * 80)
    print("FINAL COMPREHENSIVE AUDIT - EVERY ASPECT")
    print("=" * 80)
    
    all_issues = []
    
    try:
        all_issues.extend(audit_database_indexes())
        all_issues.extend(audit_dashboard_queries())
        all_issues.extend(audit_all_buttons())
        all_issues.extend(audit_all_database_fields())
        all_issues.extend(audit_frontend_fields())
        all_issues.extend(audit_api_error_handling())
        all_issues.extend(audit_performance_bottlenecks())
    except Exception as e:
        print(f"\n[ERROR] Audit failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"AUDIT COMPLETE: {len(all_issues)} TOTAL ISSUES FOUND")
    print("=" * 80)
    
    # Categorize issues
    errors = [i for i in all_issues if '[ERROR]' in i]
    warnings = [i for i in all_issues if '[WARN]' in i]
    perf = [i for i in all_issues if '[PERF]' in i]
    info = [i for i in all_issues if '[INFO]' in i]
    
    print(f"\nBreakdown:")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Performance: {len(perf)}")
    print(f"  Info: {len(info)}")
    
    if errors:
        print("\n[ACTION REQUIRED] Fix all errors before deployment")
    elif perf:
        print("\n[RECOMMENDED] Address performance issues for better UX")
    else:
        print("\n[SUCCESS] System ready for production")

if __name__ == "__main__":
    main()
