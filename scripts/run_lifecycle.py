
"""
Lifecycle Automation Script.
Runs the 'Brain' to Promote/Demote/Kill listings based on performance metrics.
"""

import sys
import os
sys.path.append(os.getcwd())

from retail_os.core.database import SessionLocal, TradeMeListing, SystemCommand, CommandStatus
from retail_os.strategy.lifecycle import LifecycleManager
from datetime import datetime, timezone
import uuid

def run_lifecycle_analysis():
    print("🧠 Starting RetailOS Lifecycle Analysis...")
    
    session = SessionLocal()
    
    # Fetch all Live listings
    listings = session.query(TradeMeListing).filter(
        TradeMeListing.actual_state.in_(["NEW", "PROVING", "STABLE", "FADING"])
    ).all()
    
    print(f"Analyzing {len(listings)} active listings...")
    
    updates = 0
    commands = 0
    
    for listing in listings:
        # Evaluate
        recommendation = LifecycleManager.evaluate_state(listing)
        action = recommendation["action"]
        reason = recommendation["reason"]
        
        if action == "NONE":
            continue
            
        print(f"[{listing.tm_listing_id}] {action} -> {recommendation['new_state']} ({reason})")
        
        # Apply State Change (Local)
        listing.actual_state = recommendation["new_state"]
        listing.last_synced_at = datetime.now(timezone.utc)
        updates += 1
        
        # Dispatch Commands?
        if action == "KILL":
            # Queue Withdraw Command
            cmd = SystemCommand(
                id=str(uuid.uuid4()),
                type="WITHDRAW_LISTING",
                payload={"listing_id": listing.tm_listing_id, "reason": reason},
                status=CommandStatus.PENDING,
                priority=10
            )
            session.add(cmd)
            commands += 1
            
        elif action == "DEMOTE":
            # Reprice?
            new_price = LifecycleManager.get_repricing_recommendation(listing)
            if new_price < listing.actual_price:
                 # Queue Reprice Command
                 cmd = SystemCommand(
                    id=str(uuid.uuid4()),
                    type="UPDATE_PRICE",
                    payload={"listing_id": listing.tm_listing_id, "price": new_price, "reason": "Demotion Reprice"},
                    status=CommandStatus.PENDING,
                    priority=5
                 )
                 session.add(cmd)
                 commands += 1
                 
    session.commit()
    print(f"Cycle Complete. {updates} State Updates. {commands} Tasks Queued.")

if __name__ == "__main__":
    run_lifecycle_analysis()
