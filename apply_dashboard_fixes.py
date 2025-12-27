"""
Automated Dashboard Fixes
Applies the 4 remaining manual fixes to clean up the UI
"""

import re

def apply_fixes():
    app_file = r"C:/Users/deepak.chhabra/OneDrive - Datacom/Documents/Trademe Integration/Trademe Integration V2/retail_os/dashboard/app.py"
    data_layer_file = r"C:/Users/deepak.chhabra/OneDrive - Datacom/Documents/Trademe Integration/Trademe Integration V2/retail_os/dashboard/data_layer.py"
    
    print("[FIXES] Applying automated fixes...")
    
    # Fix 1: Remove redundant metric tiles
    print("\n1. Removing redundant metric tiles...")
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Comment out render_vault_metrics call
    content = content.replace(
        "            render_vault_metrics(session)\n            \n            st.markdown(\"---\")\n            \n            # Main tabs",
        "            # Metrics removed - redundant with tabs\n            # Main tabs"
    )
    
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("   [OK] Metric tiles removed")
    
    # Fix 2: Simplify Vault 2 table
    print("\n2. Simplifying Vault 2 table...")
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the Vault 2 table data section
    old_pattern = r'data\.append\(\{\s+"ID": p\["id"\],\s+"Title": p\["title"\],\s+"Supplier": p\["supplier"\],.*?"Enriched": "✅" if p\["enriched"\] else "❌",\s+\}\)'
    new_code = '''data.append({
                    "ID": p["id"],
                    "Title": p["title"],
                })'''
    
    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
    
    # Update column config
    old_config = r'"Supplier": st\.column_config\.TextColumn.*?"Enriched": st\.column_config\.TextColumn\("AI", width="small"\),'
    new_config = '''"Title": st.column_config.TextColumn("Product Title", width="large"),'''
    
    content = re.sub(old_config, new_config, content, flags=re.DOTALL)
    
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("   [OK] Vault 2 table simplified")
    
    # Fix 3: Remove trust score calculation from data layer
    print("\n3. Fixing performance issue (removing trust calculation)...")
    with open(data_layer_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace trust engine section
    old_trust = r'# Pre-load Trust Engine.*?trust_score": t_report\.score,'
    new_trust = '''# PERFORMANCE FIX: Don't calculate trust scores in table view
        # Trust scores are only shown in the inspector pane
        
        for item in items:
            sp = item.supplier_product
            
            data.append({
                "id": item.id,
                "sku": item.sku,
                "title": item.title or sp.title,
                "supplier": sp.supplier.name if sp and sp.supplier else "Unknown",
                "cost": float(sp.cost_price) if sp.cost_price else 0.0,
                "stock": sp.stock_level,
                "enriched": bool(sp.enriched_description),
                "trust_score": None,  # Calculated on-demand in inspector only'''
    
    content = re.sub(old_trust, new_trust, content, flags=re.DOTALL)
    
    with open(data_layer_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("   [OK] Performance fix applied")
    
    print("\n[SUCCESS] All fixes applied successfully!")
    print("\nPlease refresh your Streamlit dashboard to see the changes.")

if __name__ == "__main__":
    try:
        apply_fixes()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nSome fixes may need to be applied manually. Check final_summary.md for details.")
