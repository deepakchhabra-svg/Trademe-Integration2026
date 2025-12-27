"""
Lifecycle Manager
The 'Brain' that decides when to promote, demote, or kill a listing.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any

class LifecycleManager:
    """
    Manages the lifecycle state of Trade Me listings based on metrics.
    States: NEW -> PROVING -> STABLE -> FADING -> KILL
    """
    
    # Configuration
    PROVING_DAYS = 7
    STABLE_VIEW_THRESHOLD = 50
    FADING_DAYS_WITHOUT_SALE = 30
    KILL_VIEWS_THRESHOLD = 10 # If < 10 views in 30 days, kill it
    
    @staticmethod
    def evaluate_state(listing: Any) -> Dict[str, Any]:
        """
        Evaluate a listing and recommend a state transition.
        input: TradeMeListing ORM object
        output: {"action": "NONE"|"PROMOTE"|"DEMOTE"|"KILL", "new_state": str, "reason": str}
        """
        current_state = listing.actual_state
        days_live = (datetime.utcnow() - listing.last_synced_at).days
        views = listing.view_count or 0
        watchers = listing.watch_count or 0
        
        # 1. NEW -> PROVING
        if current_state == "NEW":
            # Immediate transition usually, or after 24h checks
            return {
                "action": "PROMOTE",
                "new_state": "PROVING",
                "reason": "Initial incubation period started"
            }
            
        # 2. PROVING -> STABLE or FADING
        elif current_state == "PROVING":
            if days_live >= LifecycleManager.PROVING_DAYS:
                if views >= LifecycleManager.STABLE_VIEW_THRESHOLD:
                    return {
                        "action": "PROMOTE",
                        "new_state": "STABLE",
                        "reason": f"Graduated Proving: {views} views > {LifecycleManager.STABLE_VIEW_THRESHOLD}"
                    }
                else:
                    return {
                        "action": "DEMOTE",
                        "new_state": "FADING",
                        "reason": f"Failed Proving: {views} views < {LifecycleManager.STABLE_VIEW_THRESHOLD}"
                    }
        
        # 3. STABLE -> FADING
        elif current_state == "STABLE":
            # If no activity in X days, move to Fading
            # This requires 'last_sold_at' which currently might not be populated reliably
            # Fallback to pure time decay
            if days_live > 60 and views < (days_live * 0.5): # e.g. < 30 views in 60 days
                 return {
                    "action": "DEMOTE",
                    "new_state": "FADING",
                    "reason": "Performance decay detected"
                }

        # 4. FADING -> KILL
        elif current_state == "FADING":
            if days_live > LifecycleManager.FADING_DAYS_WITHOUT_SALE:
                # If it's really dead (no views), kill it
                if views < LifecycleManager.KILL_VIEWS_THRESHOLD:
                    return {
                        "action": "KILL",
                        "new_state": "WITHDRAWN",
                        "reason": f"Zombie product: < {LifecycleManager.KILL_VIEWS_THRESHOLD} views in {days_live} days"
                    }
        
        return {"action": "NONE", "new_state": current_state, "reason": "No change"}
        
    @staticmethod
    def get_repricing_recommendation(listing: Any) -> float:
        """
        Suggest a new price for FADING items.
        """
        if listing.actual_state == "FADING":
            # Suggest 10% drop, but protect margin
            current = listing.actual_price
            suggestion = current * 0.90
            return suggestion
            
        return listing.actual_price
