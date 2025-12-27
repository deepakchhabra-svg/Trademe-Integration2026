import sys
import os
sys.path.append(os.getcwd())

import argparse
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Import Scrapers & Adapters
from scripts.discover_category import discover_cash_converters_urls
from scripts.discover_noel_leeming import discover_noel_leeming_urls
from retail_os.scrapers.onecheq.scraper import discover_products_from_collection, scrape_onecheq_product

from retail_os.scrapers.cash_converters.scraper import scrape_single_item as scrape_cc
from retail_os.scrapers.noel_leeming.scraper import scrape_category as scrape_nl

# Import Adapters (The logic engines)
from retail_os.scrapers.onecheq.adapter import OneCheqAdapter
from retail_os.scrapers.cash_converters.adapter import CashConvertersAdapter
# Assuming Noel Leeming has an adapter too, but for robust import:
# from retail_os.scrapers.noel_leeming.adapter import NoelLeemingAdapter

# Import Core
from retail_os.core.unified_schema import normalize_onecheq_row, normalize_cash_converters_row, normalize_noel_leeming_row

class UnifiedPipeline:
    def __init__(self, max_pages: int = 200, batch_size: int = 50, log_file: str = "production_sync.log"):
        self.max_pages = max_pages
        self.batch_size = batch_size
        self.log_file = log_file
        
        # Initialize Adapters
        self.adapters = {
            'OC': OneCheqAdapter(),
            'CC': CashConvertersAdapter(),
            # 'NL': NoelLeemingAdapter() # If exists, else fallback
        }
        
        # Ensure log file exists/reset
        with open(self.log_file, 'w') as f:
            f.write(f"Pipeline started at {datetime.now()}\n")
        
        self.stats = {
            'cc_discovered': 0,
            'nl_discovered': 0,
            'oc_discovered': 0,
            'total_scraped': 0,
            'total_new': 0, 
            'total_skipped': 0,
            'total_updated': 0,
            'total_failed': 0,
            'start_time': time.time()
        }

    def log(self, message: str, level: str = "INFO"):
        """Log to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"[{timestamp}] [{level}] {message}"
        print(full_msg, flush=True)
        # Append to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(full_msg + "\n")

    async def run(self, suppliers=None, custom_url=None):
        """Main execution flow."""
        self.log("=" * 80)
        self.log("UNIFIED TRI-SITE PRODUCTION PIPELINE (With Delta Detection)")
        self.log("=" * 80)
        
        # --- PHASE 1: DISCOVERY ---
        self.log("PHASE 1: DISCOVERY")
        
        self.stats['oc_discovered'] = 0
        self.stats['cc_discovered'] = 0
        self.stats['nl_discovered'] = 0
        
        work_queue = []

        # 1. OneCheq
        if not suppliers or 'OC' in suppliers:
            self.log("Discovering OneCheq products...")
            url = custom_url if custom_url and len(suppliers) == 1 else "https://onecheq.co.nz/collections/all"
            oc_items = await asyncio.to_thread(
                discover_products_from_collection, 
                url, 
                self.max_pages
            )
            self.stats['oc_discovered'] = len(oc_items)
            self.log(f"OneCheq: Found {len(oc_items)} listings")
            
            for item in oc_items:
                work_queue.append(('OC', item['url'], scrape_onecheq_product, item))

        # 2. Cash Converters
        if not suppliers or 'CC' in suppliers:
            self.log("Discovering Cash Converters products...")
            url = custom_url if custom_url and len(suppliers) == 1 else "https://shop.cashconverters.co.nz/Browse/R160787-R160789/North_Island-Auckland"
            cc_urls = await asyncio.to_thread(discover_cash_converters_urls, url, self.max_pages)
            self.stats['cc_discovered'] = len(cc_urls)
            self.log(f"Cash Converters: Found {len(cc_urls)} listings")
            
            for url in cc_urls:
                work_queue.append(('CC', url, scrape_cc, {}))

        # 3. Noel Leeming
        if not suppliers or 'NL' in suppliers:
            self.log("Discovering Noel Leeming products...")
            url = custom_url if custom_url and len(suppliers) == 1 else "https://www.noelleeming.co.nz/shop/computers-office-tech/computers"
            nl_urls = await asyncio.to_thread(discover_noel_leeming_urls, url, 10 if self.max_pages > 50 else self.max_pages) 
            self.stats['nl_discovered'] = len(nl_urls)
            self.log(f"Noel Leeming: Found {len(nl_urls)} listings")
            
            for url in nl_urls:
                work_queue.append(('NL', url, scrape_nl, {}))

        total_discovered = len(work_queue)
        self.log(f"TOTAL DISCOVERED: {total_discovered} items")
        self.log("-" * 80)

        # --- PHASE 2: BATCH PROCESSING ---
        self.log(f"PHASE 2: PROCESSING {len(work_queue)} ITEMS")
        
        total = len(work_queue)
        for i in range(0, total, self.batch_size):
            batch = work_queue[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size
            
            self.log(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
            
            await self.process_batch(batch)

        # --- PHASE 3: RECONCILIATION ---
        # Only run if we are doing a FULL scan (max_pages >= 200 or 0)
        SAFE_THRESHOLD = 50 
        
        # We need the pipeline start time in UTC for reconciliation
        pipeline_utc_start = datetime.utcfromtimestamp(self.stats['start_time'])
        
        if self.max_pages >= SAFE_THRESHOLD or self.max_pages == 0:
            self.log("-" * 80)
            self.log(f"PHASE 3: RECONCILIATION (Threshold met: {self.max_pages} >= {SAFE_THRESHOLD})")
            
            from retail_os.core.reconciliation import ReconciliationEngine
            from retail_os.core.database import SessionLocal, Supplier
            
            db = SessionLocal()
            engine = ReconciliationEngine(db)
            
            # Map code to Name
            sup_map = {'OC': 'ONECHEQ', 'CC': 'CASH_CONVERTERS', 'NL': 'NOEL_LEEMING'}
            
            targets = suppliers if suppliers else ['OC', 'CC', 'NL']
            
            for code in targets:
                if code in sup_map:
                    sup_name = sup_map[code]
                    sup = db.query(Supplier).filter_by(name=sup_name).first()
                    if sup:
                        engine.process_orphans(sup.id, pipeline_utc_start)
                        self.log(f"Reconciled {sup_name}")
            
            db.close()
        else:
             self.log(f"PHASE 3: SKIPPED RECONCILIATION (Limit {self.max_pages} < {SAFE_THRESHOLD})")

        self.log("=" * 80)
        self.log("PIPELINE COMPLETED")

    async def process_batch(self, batch):
        tasks = []
        for item in batch:
            tasks.append(self.process_item(*item))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def process_item(self, supplier_code, url, scraper_func, extra_data):
        try:
            # 1. Scrape
            data = await asyncio.to_thread(scraper_func, url)
            if not data:
                self.stats['total_failed'] += 1
                return

            # 2. Add Extra Metadata (Rank/Page for OneCheq)
            if supplier_code == 'OC':
                data['collection_rank'] = extra_data.get('rank')
                data['collection_page'] = extra_data.get('page')

            # 3. Normalize & Upsert via Adapter (Delta Detection occurs here)
            await asyncio.to_thread(self.upsert_via_adapter, supplier_code, data)
            
            self.stats['total_scraped'] += 1

        except Exception as e:
            self.stats['total_failed'] += 1

    def upsert_via_adapter(self, supplier_code, raw_data):
        """Use the official Adapter to upsert, ensuring hash check & audit logs."""
        try:
            if supplier_code == 'OC':
                unified = normalize_onecheq_row(raw_data)
                unified['collection_rank'] = raw_data.get('collection_rank')
                unified['collection_page'] = raw_data.get('collection_page')
                result = self.adapters['OC']._upsert_product(unified)
                if result == 'created': self.stats['total_new'] += 1
                elif result == 'updated': self.stats['total_updated'] += 1
                
            elif supplier_code == 'CC':
                unified = normalize_cash_converters_row(raw_data)
                result = self.adapters['CC']._upsert_product(unified)
                if result == 'created': self.stats['total_new'] += 1
                elif result == 'updated': self.stats['total_updated'] += 1
                
            # Add NL logic here similar to others
                
        except Exception as e:
            pass

def main():
    parser = argparse.ArgumentParser(description="RetailOS Unified Pipeline Runner")
    parser.add_argument("--suppliers", "-s", nargs="+", choices=['OC', 'CC', 'NL'], help="Suppliers to scrape (default: ALL)")
    parser.add_argument("--limit", "-l", type=int, default=200, help="Max pages/items to discover per supplier")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Batch size for parallel processing")
    parser.add_argument("--url", "-u", type=str, help="Override discovery URL (Only valid if single supplier selected)")
    
    args = parser.parse_args()
    
    print(f"Starting Pipeline with args: {args}")
    
    pipeline = UnifiedPipeline(max_pages=args.limit, batch_size=args.batch_size)
    
    # Run async loop
    asyncio.run(pipeline.run(suppliers=args.suppliers, custom_url=args.url))

if __name__ == "__main__":
    main()
