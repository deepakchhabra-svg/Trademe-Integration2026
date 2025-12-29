"""
Standardizer Engine V2.
"The Semantic Filter"
Uses heuristic analysis to separate "Product" sentences from "Marketing" sentences.
Mimics LLM behavior by understanding context rather than just patterns.
"""

import re

class Standardizer:
    
    # Words that strongly imply the sentence is about the STORE/SERVICE, not the PRODUCT.
    BANNED_TOPICS = {
        "pawn", "loan", "cash", "finance", "credit",
        "store", "shop", "branch", "location", "address",
        "contact", "phone", "email", "call", "visit", "speak",
        "team", "staff", "friendly", "expert",
        "id required", "valid id", "drivers license", "passport",
        "stock", "inventory", "clearance", "sale",
        "warranty", "guarantee", "refund", "return", # Policies, not product
        "pickup", "shipping", "delivery", "postage", # Logistics
        "we are", "we offer", "we buy", "we sell",
    }
    
    # Subjects that usually start marketing sentences
    BANNED_STARTERS = ["we ", "our ", "us ", "contact ", "visit ", "come "]

    @staticmethod
    def is_marketing_sentence(sentence: str) -> bool:
        """
        Returns True if the sentence is likely marketing garbage.
        """
        s = sentence.lower().strip()
        if not s: return True
        
        # 1. Check Banned Topics
        # We use regex with word boundaries to avoid false positives (e.g., 'phone' in 'iPhone')
        for topic in Standardizer.BANNED_TOPICS:
            # Topic can be a phrase like 'valid id'
            if re.search(r'\b' + re.escape(topic) + r'\b', s):
                return True
                
        # 2. Check Banned Starters
        for starter in Standardizer.BANNED_STARTERS:
            if s.startswith(starter):
                return True
                
        # 3. Check Phone Numbers / Addresses (Heuristic)
        # Matches (09) 123 4567 or 021 123 4567
        if re.search(r'\(\d{2,3}\)\s?\d{3}', s) or re.search(r'\d{3}\s\d{4}', s):
            return True
        # Matches addresses like "123 Great South Road"
        if re.search(r'\d+\s[A-Z][a-z]+\s(Road|St|Ave|Street|Avenue)', s):
            return True
            
        return False

    @staticmethod
    def polish(text: str) -> str:
        """
        Main entry point. filters lines/sentences.
        """
        if not text: return ""
        
        # 1. Normalize bullets without destroying markdown.
        # NOTE: Do NOT replace '*' because it breaks markdown (e.g. **bold**).
        text = text.replace("\u2022", "•")
        
        # 2. Split into semantic units (Lines or Sentences)
        # We prefer line-based processing for lists, sentence-based for paragraphs
        lines = text.split('\n')
        kept_lines = []
        
        for line in lines:
            line = line.strip()
            if not line: 
                continue
                
            # If it's a bullet point, treat it as a unit
            if line.startswith("•"):
                content = line[1:].strip()
                if not Standardizer.is_marketing_sentence(content):
                    kept_lines.append(f"• {Standardizer.fix_casing(content)}")
            else:
                # Standard paragraph
                # Split paragraph into sentences to surgically remove garbage sentences
                # heuristic split: . ! ?
                sentences = re.split(r'(?<=[.!?])\s+', line)
                clean_sentences = []
                for sent in sentences:
                    if not Standardizer.is_marketing_sentence(sent):
                        clean_sentences.append(Standardizer.fix_casing(sent))
                
                if clean_sentences:
                    kept_lines.append(" ".join(clean_sentences))
        
        return '\n\n'.join(kept_lines)

    @staticmethod
    def fix_casing(text: str) -> str:
        # CAPS FIX
        upper = sum(1 for c in text if c.isupper())
        if len(text) > 5 and (upper / len(text)) > 0.5:
             return text.capitalize()
        return text
