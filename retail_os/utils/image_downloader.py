import os
import requests
from pathlib import Path

class ImageDownloader:
    """Physical image download service with verification."""
    
    def __init__(self, base_dir="data/media"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, url: str, sku: str) -> dict:
        """
        Download image to local storage.
        Returns: {"success": bool, "path": str, "size": int, "error": str}
        """
        if not url or url.startswith("https://placehold.co"):
            return {"success": False, "path": None, "size": 0, "error": "Placeholder URL"}
        
        try:
            # Determine extension
            ext = ".jpg"
            if ".png" in url.lower():
                ext = ".png"
            elif ".webp" in url.lower():
                ext = ".webp"
            
            # Target path
            filename = f"{sku}{ext}"
            filepath = self.base_dir / filename
            
            # Download with headers to avoid 403
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Referer": "https://www.noelleeming.co.nz/",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
            # Use a session for better connection handling
            with requests.Session() as session:
                response = session.get(url, headers=headers, timeout=20, stream=True)
                response.raise_for_status()
                
                # Save
                # Save raw first
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # --- IMAGE TUNING (Added for Trade Me Compliance) ---
            # Trade Me prefers JPG. We convert everything to JPG.
            try:
                from PIL import Image
                with Image.open(filepath) as img:
                    # Convert P (indexed) or RGBA to RGB
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                        
                    # Target Filename (force .jpg)
                    jpg_filename = f"{sku}.jpg"
                    jpg_path = self.base_dir / jpg_filename
                    
                    # Resize if huge (Trade Me Max 2048x2048 recommended)
                    if img.width > 2048 or img.height > 2048:
                        img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                        
                    img.save(jpg_path, "JPEG", quality=85, optimize=True)
                    
                    # Update return path to the new JPG
                    filepath = jpg_path
                    filename = jpg_filename
                    
            except ImportError:
                print("ImageDownloader: PIL not installed. Skipping tuning.")
            except Exception as e:
                print(f"ImageDownloader: Tuning Failed ({e}). Using raw.")
            # ----------------------------------------------------
            
            # Verify
            if not filepath.exists():
                return {"success": False, "path": None, "size": 0, "error": "File not saved"}
            
            file_size = filepath.stat().st_size
            
            if file_size < 1000: # Suspiciously small (e.g. error page)
                 return {"success": False, "path": None, "size": file_size, "error": "File too small (<1KB)"}

            return {
                "success": True,
                "path": str(filepath),
                "size": file_size,
                "error": None
            }
            
        except Exception as e:
            # Fallback to system curl (robustness for Pilot)
            print(f"ImageDownloader: Python requests failed ({e}). Trying system curl...")
            try:
                import subprocess
                # Determine extension again just in case
                ext = ".jpg"
                if ".png" in url.lower(): ext = ".png"
                elif ".webp" in url.lower(): ext = ".webp"
                
                filename = f"{sku}{ext}"
                filepath = self.base_dir / filename
                
                # curl -L -o <path> <url> -A "User-Agent"
                cmd = [
                    "curl", "-L", "-o", str(filepath), url,
                    "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                
                if filepath.exists() and filepath.stat().st_size > 1000:
                    # Success via curl
                    # Optional: Convert/Tune if needed (copy-paste logic or extract to method)
                    # For now, just return this
                    return {
                        "success": True,
                        "path": str(filepath),
                        "size": filepath.stat().st_size,
                        "error": None
                    }
                else:
                     return {
                        "success": False,
                        "path": None,
                        "size": 0,
                        "error": "Curl failed to download valid file"
                     }
            except Exception as curl_e:
                return {
                    "success": False,
                    "path": None,
                    "size": 0,
                    "error": f"Requests and Curl both failed: {e} | {curl_e}"
                }
        finally:
            # Final sanity check for return
            pass
    
    def verify_image(self, sku: str) -> dict:
        """Check if image exists locally."""
        for ext in [".jpg", ".png", ".webp"]:
            filepath = self.base_dir / f"{sku}{ext}"
            if filepath.exists():
                return {
                    "exists": True,
                    "path": str(filepath),
                    "size": filepath.stat().st_size
                }
        
        return {"exists": False, "path": None, "size": 0}
