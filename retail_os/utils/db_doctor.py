import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, InternalProduct, SupplierProduct

def heal_database_links():
    print("[DB DOCTOR] Starting Link Repair...")
    session = SessionLocal()
    
    products = session.query(InternalProduct).all()
    fixed_count = 0
    
    for ip in products:
        # Assuming SKU Pattern "PREFIX-EXTERNALSKU"
        # e.g. "NL-N233790" -> "N233790"
        parts = ip.sku.split('-')
        if len(parts) < 2:
            continue
            
        external_sku = parts[1]
        
        # Find the CORRECT Supplier Product
        # (Assuming only one supplier "NL" for now, or match via Supplier ID logic)
        # Ideally we check the supplier prefix, but for Phase 3.5 MVP we check SKUs.
        
        sp = session.query(SupplierProduct).filter_by(
            external_sku=external_sku
        ).first()
        
        if sp:
            if ip.primary_supplier_product_id != sp.id:
                print(f"   [HEALING] Key: {ip.sku}")
                print(f"      Old Link: {ip.primary_supplier_product_id} (Wrong)")
                print(f"      New Link: {sp.id} ({sp.title[:30]}...)")
                
                ip.primary_supplier_product_id = sp.id
                fixed_count += 1
        else:
            print(f"   [ORPHAN] {ip.sku} has no SupplierProduct found.")

    if fixed_count > 0:
        session.commit()
        print(f"[SUCCESS] COMMITTED {fixed_count} Repairs.")
    else:
        print("[OK] Database is healthy. No repairs needed.")
        
    session.close()

if __name__ == "__main__":
    heal_database_links()
