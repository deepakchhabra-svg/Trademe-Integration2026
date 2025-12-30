"""
Image Guard.
Uses Gemini 1.5 Flash Vision to detect if an image is product photo or marketing junk.
"""
import os
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class ImageGuard:
    
    def __init__(self):
        pass

    @property
    def api_key(self):
        return os.getenv("GEMINI_API_KEY")

    def is_active(self):
        return self.api_key is not None

    def _get_hash(self, image_bytes: bytes) -> str:
        import hashlib
        return hashlib.md5(image_bytes).hexdigest()

    def _load_cache(self):
        self.cache_file = "image_audit_cache.json"
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f)

    def check_image(self, image_path: str) -> dict:
        """
        Returns {'is_safe': bool, 'reason': str}
        """
        if not hasattr(self, 'cache'): self._load_cache()
        if not self.is_active():
            return {"is_safe": True, "reason": "Guard Inactive"}

        if not os.path.exists(image_path):
             return {"is_safe": False, "reason": "File not found"}

        # Read and Hash
        try:
            with open(image_path, "rb") as img_file:
                img_bytes = img_file.read()
                img_hash = self._get_hash(img_bytes)
                b64_image = base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            return {"is_safe": True, "reason": f"Read Error: {e}"}

        # Check Cache
        if img_hash in self.cache:
            return self.cache[img_hash]

        # Gemini Vision Call (model must exist; no silent fallbacks)
        try:
            from retail_os.core.llm_enricher import enricher
            model = enricher.gemini_model()
        except Exception as e:
            return {"is_safe": False, "reason": f"Image audit blocked: {str(e)[:200]}"}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        prompt = """
        Analyze this image. Returns JSON only.
        Is this image a photo of a SPECIFIC PHYSICAL PRODUCT for sale (like a camera, drill, guitar, ring), 
        OR is it a GENERIC BANNER / ADVERTISEMENT containing text (like 'We Pawn Cars', 'Sale', 'Finance Available')?
        
        Format:
        {"is_marketing": boolean, "description": string}
        
        Set is_marketing=true if it contains large text overlays, phone numbers, or looks like a generic digital flyer.
        Set is_marketing=false if it is a photo of a real object on a bench/table/floor.
        """
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64_image
                    }}
                ]
            }]
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            result = resp.json()['candidates'][0]['content']['parts'][0]['text']
            # Clean JSON markdown
            result = result.replace("```json", "").replace("```", "").strip()
            data = json.loads(result)
            
            outcome = {
                "is_safe": not data.get("is_marketing", False),
                "reason": data.get("description", "No description")
            }
            
            # Save to Cache
            self.cache[img_hash] = outcome
            self._save_cache()
            
            return outcome
            
        except Exception as e:
            # No silent "safe" fallback: if guard is active, failure blocks.
            msg = str(e)[:200]
            try:
                print(f"ImageGuard Error: {msg}")
            except Exception:
                pass
            return {"is_safe": False, "reason": f"Image audit failed: {msg}"}

guard = ImageGuard()
