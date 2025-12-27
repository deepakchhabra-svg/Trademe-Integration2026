"""
Boilerplate Detector.
Automatically identifies repeated marketing text across the inventory.
"If it appears everywhere, it's garbage."
"""

from collections import Counter
import re
from typing import List, Set
from retail_os.core.database import SessionLocal, SupplierProduct

class BoilerplateDetector:
    
    def __init__(self, sample_size: int = 100, threshold_ratio: float = 0.05):
        """
        :param sample_size: Number of items to analyze.
        :param threshold_ratio: If a sentence appears in > 5% of items, it's boilerplate.
        """
        self.sample_size = sample_size
        self.threshold = int(sample_size * threshold_ratio)
        if self.threshold < 2:
            self.threshold = 2 # Minimum 2 occurences
            
    def detect_patterns(self) -> List[str]:
        """
        Scans DB and returns a list of high-frequency sentences/phrases.
        """
        db = SessionLocal()
        try:
            # Fetch recent descriptions
            items = db.query(SupplierProduct.description).limit(self.sample_size).all()
            descriptions = [i[0] for i in items if i[0]]
            
            sentence_counter = Counter()
            
            for desc in descriptions:
                # 1. Normalize
                # Split by newlines or periods followed by space
                # We need to be careful not to split "approx. 5kg"
                sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s|\n+', desc)
                
                for s in sentences:
                    clean_s = s.strip()
                    # Filter out short fragments like "Specs:" or "Condition:"
                    if len(clean_s) > 15: 
                        sentence_counter[clean_s] += 1
            
            # Filter by threshold
            boilerplate = []
            for sentence, count in sentence_counter.most_common(50):
                if count >= self.threshold:
                    # Exclude common but valid text? No, if it repeats 5 times in 100 items, strip it.
                    # Unless it's "Used condition" which is fine to keep? 
                    # Actually for TradeMe we want UNIQUE descriptions, so stripping repeats is good.
                    boilerplate.append(sentence)
                    
            return boilerplate
            
        finally:
            db.close()

# Singleton for Dashboard usage
detector = BoilerplateDetector()
