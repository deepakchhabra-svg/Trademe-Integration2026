"""
Title Cleaning Functions
Strips branding, SEO spam, and enriches for Trade Me

NOTE: Description cleaning is handled by retail_os/utils/seo.py:build_seo_description()
      which uses SKIP_PATTERNS for comprehensive boilerplate removal.
"""
import re


def clean_title_for_trademe(raw_title: str) -> str:
    """
    Clean title for Trade Me listing.
    Removes: Cash Converters, Noel Leeming branding, leading dashes, VALUED AT prefixes
    """
    if not raw_title:
        return ""
    
    # Remove supplier branding
    title = raw_title.replace("Cash Converters", "").replace("Noel Leeming", "")
    
    # Remove "VALUED AT $XXX" prefix
    title = re.sub(r'VALUED AT \$[\d,]+\s*[-–]\s*', '', title, flags=re.IGNORECASE)
    
    # Remove leading dashes and whitespace
    title = re.sub(r'^[-–\s]+', '', title)
    
    # Remove trailing dashes and whitespace
    title = re.sub(r'[-–\s]+$', '', title)
    
    # Normalize whitespace
    title = ' '.join(title.split())
    
    # Capitalize first letter (light touch) but preserve common brand casing.
    if title:
        title = title[0].upper() + title[1:]
        # Brand casing fixes
        title = re.sub(r"\bIphone\b", "iPhone", title)
        title = re.sub(r"\bMacbook\b", "MacBook", title)
        title = re.sub(r"\bAirpods\b", "AirPods", title)
    
    return title
