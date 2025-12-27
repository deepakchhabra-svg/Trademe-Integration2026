import sys
import os
# Ensure repo root is on sys.path regardless of cwd
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from retail_os.core.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
indexes = inspector.get_indexes('supplier_products')
print(f'Indexes on supplier_products: {len(indexes)}')
for idx in indexes:
    print(f"  - {idx['name']}")

print('\nIndexes on orders:')
indexes = inspector.get_indexes('orders')
for idx in indexes:
    print(f"  - {idx['name']}")
