import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, SupplierProduct, Supplier

db = SessionLocal()

print("\n=== SCRAPING STATUS ===\n")

suppliers = db.query(Supplier).all()

for s in suppliers:
    total = db.query(SupplierProduct).filter_by(supplier_id=s.id).count()
    with_desc = db.query(SupplierProduct).filter_by(supplier_id=s.id).filter(
        SupplierProduct.description != None, 
        SupplierProduct.description != ""
    ).count()
    with_specs = db.query(SupplierProduct).filter_by(supplier_id=s.id).filter(
        SupplierProduct.specs != None
    ).count()
    
    print(f"{s.name}:")
    print(f"  Total Products: {total}")
    print(f"  With Description: {with_desc} ({int(with_desc/total*100) if total > 0 else 0}%)")
    print(f"  With Specs: {with_specs} ({int(with_specs/total*100) if total > 0 else 0}%)")
    print()

# Enrichment status
print("=== ENRICHMENT STATUS ===\n")
pending = db.query(SupplierProduct).filter_by(enrichment_status="PENDING").count()
success = db.query(SupplierProduct).filter_by(enrichment_status="SUCCESS").count()
failed = db.query(SupplierProduct).filter_by(enrichment_status="FAILED").count()

print(f"Pending: {pending}")
print(f"Success: {success}")
print(f"Failed: {failed}")
print(f"Total: {pending + success + failed}")

db.close()
