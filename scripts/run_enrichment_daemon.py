"""
Enrichment Daemon
Continuously runs enrichment batches in the background.
"""
import sys
import os
import time
sys.path.append(os.getcwd())

from scripts.enrich_products import enrich_batch

def run_daemon(batch_size=10, delay=5):
    print("=" * 60)
    print("ENRICHMENT DAEMON STARTED")
    print("Continuous AI processing of pending products...")
    print("=" * 60)
    
    batch_count = 0
    
    while True:
        try:
            # Run a batch
            enrich_batch(batch_size=batch_size, delay_seconds=delay)
            
            # Short rest between batches
            time.sleep(2)
            batch_count += 1
            
            if batch_count % 10 == 0:
                print(f"--- Daemon Heartbeat: {batch_count} batches processed ---")
                
        except KeyboardInterrupt:
            print("Daemon stopping...")
            break
        except Exception as e:
            print(f"Daemon Error: {e}")
            time.sleep(10) # Wait longer on error

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RetailOS Enrichment Daemon")
    parser.add_argument("--batch-size", "-b", type=int, default=10, help="Items per batch")
    parser.add_argument("--delay", "-d", type=int, default=5, help="Seconds delay between items")
    
    args = parser.parse_args()
    
    print(f"Starting enrichment worker")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Delay: {args.delay}s between items")
    print()
    
    run_daemon(batch_size=args.batch_size, delay=args.delay)
