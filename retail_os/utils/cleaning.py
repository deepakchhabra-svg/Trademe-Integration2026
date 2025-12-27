"""
Title and Description Cleaning Functions
Strips branding, SEO spam, and enriches for Trade Me
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
    
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]
    
    return title

def clean_description_for_trademe(raw_description: str, specs: dict = None) -> str:
    """
    Clean and enrich description for Trade Me.
    Removes branding, adds specs if available.
    """
    if not raw_description:
        description = ""
    else:
        # Remove supplier branding
        description = raw_description.replace("Cash Converters", "").replace("Noel Leeming", "")
        
        # Aggressive Boilerplate Removal
        boilerplate_phrases = [
            r"\*\*\*Stock Wanted\*\*\*.*", # Matches the start of the unwanted block and everything after if it's at the end
            r"We are looking for more stock for our shop floor!.*",
            r"Bring your good quality second hand goods.*",
            r"All you need is your item and a valid ID.*",
            r"Warranty only valid when.*",
            r"Products must be paid within.*",
            r"After payment Items must be held.*",
            r"ID is required upon collecting.*",
            r"If you have any issues please give us.*",
            r"If you like our service.*",
            r"Pickup is available.*", # Common variation
            r"Items are available for collection.*"
        ]
        
        for phrase in boilerplate_phrases:
            # Case insensitive, DOTALL to match across lines if needed, though most seem line-based
            description = re.sub(phrase, "", description, flags=re.IGNORECASE | re.DOTALL)

        # Remove excessive whitespace that might be left behind
        description = re.sub(r'\n\s*\n', '\n\n', description)
        description = description.strip()
    
    # Add specs if available
    if specs and len(specs) > 0:
        description = f"Specifications:\n" + "\n".join([f"• {key}: {value}" for key, value in specs.items()]) + "\n\n" + description
    
    return description.strip()

def extract_specs_from_description(description: str) -> dict:
    """
    Extract structured specs from description text.
    Returns dict of key-value pairs.
    """
    specs = {}
    
    if not description:
        return specs
    
    # Common spec patterns
    patterns = [
        (r'Model:\s*([A-Z0-9\-\s]+?)(?=\n|Condition|Brand|Type|$)', 'Model'),
        (r'Condition:\s*([A-Za-z\s]+?)(?=\n|Model|Brand|Type|$)', 'Condition'),
        (r'Brand:\s*([A-Za-z\s]+?)(?=\n|Model|Condition|Type|$)', 'Brand'),
        (r'Type:\s*([A-Za-z\s]+?)(?=\n|Model|Condition|Brand|$)', 'Type'),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            specs[key] = match.group(1).strip()
    
    return specs
