from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from retail_os.core.database import ListingMetricSnapshot, TradeMeListing, InternalProduct

class MetricsEngine:
    """
    Calculates Performance Metrics (Velocity, Health).
    Ref: Master Requirements Section 21.
    """
    
    def __init__(self, session: Session):
        self.session = session

    def calculate_listing_velocity(self, listing_id: int, days: int = 1) -> float:
        """
        Computes Views Per Day over the last N days.
        """
        now = datetime.utcnow()
        past = now - timedelta(days=days)
        
        # Get Current (or latest snapshot)
        # Ideally we use the current listing state or the latest snapshot
        latest = self.session.query(ListingMetricSnapshot)\
            .filter(ListingMetricSnapshot.listing_id == listing_id)\
            .order_by(ListingMetricSnapshot.captured_at.desc())\
            .first()
            
        if not latest:
            return 0.0
            
        # Get Past Snapshot (closest to 'past')
        # We look for the first snapshot AFTER the cut-off, to handle gaps
        historic = self.session.query(ListingMetricSnapshot)\
            .filter(ListingMetricSnapshot.listing_id == listing_id)\
            .filter(ListingMetricSnapshot.captured_at <= past)\
            .order_by(ListingMetricSnapshot.captured_at.desc())\
            .first()
            
        if not historic:
            # If no history old enough, use the oldest available?
            # Or just return 0 (not enough data)?
            # Let's fallback to "Total Views / Days Live" if strictly needed,
            # but Master Req says "observable demand".
            # For now, return 0.0 if we can't compute a delta.
            return 0.0
            
        delta_views = latest.view_count - historic.view_count
        delta_time = (latest.captured_at - historic.captured_at).total_seconds() / 86400 # Days
        
        if delta_time < 0.1: # Too small time window
            return 0.0
            
        velocity = delta_views / delta_time
        return round(velocity, 2)

    def get_store_saturation_metrics(self) -> dict:
        """
        Store-Wide Aggregates.
        """
        listings = self.session.query(TradeMeListing).filter_by(actual_state="Live").all()
        
        total_views = sum(l.view_count or 0 for l in listings)
        total_watchers = sum(l.watch_count or 0 for l in listings)
        count = len(listings)
        
        return {
            "active_listings_count": count,
            "total_views": total_views,
            "total_watchers": total_watchers,
            "avg_views_per_listing": round(total_views / count, 1) if count else 0
        }
