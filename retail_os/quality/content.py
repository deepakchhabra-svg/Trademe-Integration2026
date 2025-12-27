import re
import httpx
from typing import List, Tuple, Dict

def sanitize_description(raw_text: str) -> str:
    """
    Cleans supplier descriptions by removing contact info, marketing spam, and excessive whitespace.
    """
    if not raw_text:
        return ""
        
    text = raw_text
    
    # 1. Boilerplate Removal (Case Insensitive)
    denylist = [
        r"WE PAWN CARS",
        r"WE BUY & SELL",
        r"CASH CONVERTERS",
        r"NOEL LEEMING",
        r"CONTACT US",
        r"PH: [0-9]+",
        r"PHONE: [0-9]+",
        r"@[a-zA-Z0-9\.]+", # Emails / twitter handles
        r"www\.[a-zA-Z0-9\.]+", # URLs
        r"http[s]?://[a-zA-Z0-9\./]+" # URLs
    ]
    
    for pattern in denylist:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
    # 2. Email / Phone Specifics
    # Simple regex for phone numbers often found: 021 xxx xxx or 09 xxx xxxx
    text = re.sub(r"0\d{1,2}[\s-]?\d{3}[\s-]?\d{3,4}", "", text)
    
    # 3. HTML Cleanup (Basic)
    text = re.sub(r"<[^>]+>", "\n", text) # Replace tags with newlines
    
    # 4. Whitespace Normalization
    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()
    
    return text

def verify_images(image_urls: List[str]) -> Tuple[bool, List[Dict]]:
    """
    Checks if images are reachable.
    Returns: (All Good?, Details List)
    """
    if not image_urls:
        return False, [{"status": "MISSING", "url": "N/A"}]
        
    results = []
    all_ok = True
    
    client = httpx.Client(timeout=5.0)
    
    for url in image_urls:
        try:
            # We use HEAD first, fallback to GET if needed
            resp = client.head(url)
            if resp.status_code == 405: # Method not allowed
                resp = client.get(url)
                
            if resp.status_code == 200:
                # Check Content-Type
                ct = resp.headers.get("content-type", "")
                if "image" in ct:
                    results.append({"status": "OK", "url": url, "size": resp.headers.get("content-length", "0")})
                else:
                    results.append({"status": "INVALID_TYPE", "url": url, "type": ct})
                    all_ok = False
            else:
                results.append({"status": f"ERROR_{resp.status_code}", "url": url})
                all_ok = False
        except Exception as e:
            results.append({"status": "EXCEPTION", "url": url, "error": str(e)})
            all_ok = False
            
    client.close()
    return all_ok, results
