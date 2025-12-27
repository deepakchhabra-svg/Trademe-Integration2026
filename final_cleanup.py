"""
Final cleanup script - Remove metric tiles and simplify pagination
"""

def final_cleanup():
    file_path = r"C:/Users/deepak.chhabra/OneDrive - Datacom/Documents/Trademe Integration/Trademe Integration V2/retail_os/dashboard/app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("[CLEANUP] Starting final cleanup...")
    
    # 1. Replace render_vault_metrics function with empty stub
    print("\n1. Removing metric tiles function...")
    import re
    
    # Find and replace the entire render_vault_metrics function
    pattern = r'def render_vault_metrics\(session\):.*?st\.markdown\("<br>", unsafe_allow_html=True\)'
    replacement = '''def render_vault_metrics(session):
    """Metrics removed - redundant with tabs"""
    pass'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("   [OK] Metric tiles function replaced with stub")
    
    # 2. Remove pagination buttons - replace with simple text
    print("\n2. Simplifying pagination...")
    
    # Find the pagination section and replace with simple page indicator
    old_pagination = r'# Pagination controls at bottom.*?st\.rerun\(\)'
    new_pagination = '''# Simple page indicator
    if total_pages > 1:
        st.caption(f"Page {page} of {total_pages}")'''
    
    content = re.sub(old_pagination, new_pagination, content, flags=re.DOTALL)
    print("   [OK] Pagination simplified")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n[SUCCESS] Final cleanup complete!")
    print("\nRefresh your browser to see:")
    print("  - No metric tiles")
    print("  - Simple page numbers instead of big buttons")

if __name__ == "__main__":
    final_cleanup()
