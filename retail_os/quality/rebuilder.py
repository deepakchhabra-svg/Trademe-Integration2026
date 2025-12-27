from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

@dataclass
class ReconstructedSegment:
    """A segment of text with its provenance source."""
    text: str
    source: str  # SOURCE_PRODUCT, SOURCE_METADATA, SYSTEM_GENERATED
    tags: List[str] = field(default_factory=list)

@dataclass
class RebuildResult:
    """The result of a content rebuild."""
    final_text: str
    segments: List[ReconstructedSegment]
    is_clean: bool
    blockers: List[str]

class ContentRebuilder:
    """
    Rebuilds product descriptions from scratch using ONLY allowed fields.
    Discards raw description entirely to prevent marketing/policy leakage.
    Implements STRICT identity stripping (Condition A) and De-duplication (Condition B).
    """
    
    def __init__(self):
        self.prohibited_patterns = [
            r"stock wanted", r"cash converters", r"buy.*sell.*loan",
            r"pickup", r"shipping", r"contact", r"phone", r"\d{2,4}\s?\d{3,4}\s?\d{3,4}", # Phone numbers
            r"store.*policy", r"layby", r"finance", r"click.*collect"
        ]

    def _sanitize(self, text: str) -> str:
        """Removes unsafe characters and specific branding/marketing patterns (Condition A)."""
        if not text: return ""
        
        # 1. Basic Cleaning
        text = str(text).strip()
        text = re.sub(r'<[^>]+>', '', text) # Remove HTML
        
        # 2. RETAIL-READY TITLE CLEANUP
        # Remove leading dashes
        text = re.sub(r'^-\s*', '', text).strip()
        
        # Remove trailing brand names and store references
        text = re.sub(r'\s*-\s*Cash Converters.*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*Cash Converters\s*$', '', text, flags=re.IGNORECASE)
        
        # 3. BRANDING REMOVAL (Identity Strip)
        prohibited_phrases = [
            r"(?i)cash\s*converters?",
            r"(?i)webshop",
            r"(?i)we\s*buy\s*gold",
            r"(?i)visit\s*us",
            r"(?i)stock\s*wanted",
            r"(?i)pick\s*up.*auckland", 
            r"(?i)^title:\s*"
        ]
        
        for p in prohibited_phrases:
             text = re.sub(p, "", text)
             
        return text.strip()

    def rebuild(self, 
                title: str, 
                specs: Dict[str, str], 
                condition: str, 
                warranty_months: int = 0) -> RebuildResult:
        
        segments = []
        blockers = []
        final_lines = []
        seen_content_keys = set() # Full content de-dup
        seen_spec_keys = set() # Spec key de-dup (e.g., "Weight")
        seen_spec_values = set() # Spec value de-dup (e.g., "3.63 Grams")

        def add_line(source: str, content: str):
            if not content: return
            
            # De-duplication Logic
            normalized = re.sub(r'\W+', '', content.lower())
            
            if len(normalized) < 3: 
                pass 
            elif normalized in seen_content_keys:
                return # Skip duplicate
            
            seen_content_keys.add(normalized)
            segments.append(ReconstructedSegment(text=content, source=source))
            final_lines.append(content)

        # 1. Product Identity (Clean & Add)
        clean_title = self._sanitize(title)
        
        add_line("SYSTEM_GENERATED", "Product Details:")
        add_line("SOURCE_PRODUCT", f"Item: {clean_title}")
        
        # 2. Specs & Attributes (Condition E / B with Title De-dup)
        if specs:
            add_line("SYSTEM_GENERATED", "\nSpecifications:")
            
            # Extract title words for de-duplication
            title_words = set(clean_title.lower().split())
            
            for k, v in specs.items():
                clean_k = self._sanitize(k)
                clean_v = self._sanitize(str(v))
                
                # Skip if empty after sanitization
                if not clean_k or not clean_v: continue
                
                # DE-DUPLICATION: Skip if value is already in title
                if clean_v.lower() in clean_title.lower():
                    continue
                
                # Spec-level de-duplication
                k_norm = clean_k.lower().strip()
                v_norm = clean_v.lower().strip()
                
                if k_norm in seen_spec_keys or v_norm in seen_spec_values:
                    continue
                
                seen_spec_keys.add(k_norm)
                seen_spec_values.add(v_norm)
                
                line = f"- {clean_k}: {clean_v}"
                add_line("SOURCE_PRODUCT", line)
        
        # 3. Condition & Warranty
        add_line("SYSTEM_GENERATED", "\nTerms:")
        
        clean_condition = self._sanitize(condition) or "Used"
        add_line("SOURCE_METADATA", f"Condition: {clean_condition}")
        
        if warranty_months > 0:
             add_line("SOURCE_METADATA", f"Warranty: {warranty_months} Months")
        else:
             add_line("SOURCE_METADATA", "Covered by the Consumer Guarantees Act (CGA).")
             
        # 4. Final Compile & Trust Check
        full_text = "\n".join(final_lines)
        
        # Check for remaining prohibited patterns (Condition A Compliance Check)
        for pattern in self.prohibited_patterns:
            if re.search(pattern, full_text.lower()):
                blockers.append(f"Prohibited pattern detected: {pattern}")
                
        is_clean = len(blockers) == 0
        
        return RebuildResult(
            final_text=full_text,
            segments=segments,
            is_clean=is_clean,
            blockers=blockers
        )
