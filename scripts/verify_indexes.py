import sys
import os
sys.path.append(os.getcwd())

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
