import os
import requests
from pathlib import Path
from urllib.parse import urlparse
import time

class ImageDownloader:
    """Physical image download service with verification."""
    
    def __init__(self, base_dir="data/media"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def download_image(self, url: str, sku: str, should_abort=None) -> dict:
        """
        Download image to local storage.
        Returns: {"success": bool, "path": str, "size": int, "error": str}
        """
        try:
            if should_abort and bool(should_abort()):
                return {"success": False, "path": None, "size": 0, "error": "Cancelled"}
        except Exception:
            pass

        if not url or url.startswith("https://placehold.co"):
            return {"success": False, "path": None, "size": 0, "error": "Placeholder URL"}
        
        def _referer_for(u: str) -> str | None:
            try:
                host = urlparse(u).netloc.lower()
            except Exception:
                return None
            if "noelleeming.co.nz" in host:
                return "https://www.noelleeming.co.nz/"
            if "onecheq.co.nz" in host:
                return "https://onecheq.co.nz/"
            return None

        referer = _referer_for(url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/*,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = referer

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
            
            # Use a session for better connection handling + retries (NL can be flaky)
            last_err: Exception | None = None
            for attempt in range(1, 4):
                try:
                    try:
                        if should_abort and bool(should_abort()):
                            return {"success": False, "path": None, "size": 0, "error": "Cancelled"}
                    except Exception:
                        pass
                    with requests.Session() as session:
                        response = session.get(url, headers=headers, timeout=20, stream=True, allow_redirects=True)
                        response.raise_for_status()

                        ctype = (response.headers.get("content-type") or "").lower()
                        if ctype and "image" not in ctype:
                            raise RuntimeError(f"Non-image response content-type: {ctype}")

                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                try:
                                    if should_abort and bool(should_abort()):
                                        return {"success": False, "path": None, "size": 0, "error": "Cancelled"}
                                except Exception:
                                    pass
                                if chunk:
                                    f.write(chunk)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(min(2.0, 0.5 * (2 ** (attempt - 1))))
            if last_err is not None:
                raise last_err
            
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
            
            # Suspiciously small (often an HTML error page), but allow very small legit thumbs.
            # Trade Me may still reject low-res images; LaunchLock separately enforces "exists".
            if file_size < 300:
                 return {"success": False, "path": None, "size": file_size, "error": "File too small (<300B)"}

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
                
                # curl -L --retry ... --fail -o <path> <url> with browser-like headers
                cmd = [
                    "curl",
                    "-L",
                    "--retry", "3",
                    "--retry-delay", "1",
                    "--fail",
                    "-o", str(filepath),
                    "-A", headers["User-Agent"],
                    "-H", f"Accept: {headers['Accept']}",
                ]
                if referer:
                    cmd += ["-H", f"Referer: {referer}"]
                cmd += [url]
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
