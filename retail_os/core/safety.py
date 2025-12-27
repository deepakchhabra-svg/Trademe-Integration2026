class SafetyGuard:
    """
    Step 2D: Safety Rails.
    Prevents catastrophic data loss by blocking reconciliation during bad runs.
    """
    
    MIN_SUCCESS_RATE = 0.90  # 90% must succeed
    Min_TOTAL_ITEMS = 5      # Don't reconcile if we only got 1 item (unless store is tiny)
    
    @staticmethod
    def is_safe_to_reconcile(total_attempted: int, total_failed: int) -> bool:
        """
        Determines if we should proceed with processing orphans.
        """
        if total_attempted == 0:
            print("SafetyGuard: Aborting. 0 items attempted.")
            return False
            
        success_count = total_attempted - total_failed
        rate = success_count / total_attempted
        
        print(f"SafetyGuard: Scrape Health = {rate*100:.1f}% ({success_count}/{total_attempted})")
        
        if rate < SafetyGuard.MIN_SUCCESS_RATE:
            print(f"SafetyGuard: BLOCKING Reconciliation. Success Rate {rate:.2f} < {SafetyGuard.MIN_SUCCESS_RATE}")
            return False
            
        return True
