import os
import json
import requests
from typing import Dict
from dotenv import load_dotenv

# Force load env to ensure keys are picked up
load_dotenv()

class LLMEnricher:
    
    def __init__(self):
        # We don't cache keys anymore to handle hot-reloading env vars
        pass

    @property
    def gemini_key(self):
        return os.getenv("GEMINI_API_KEY")

    @property
    def openai_key(self):
        return os.getenv("OPENAI_API_KEY")

    @property
    def provider(self):
        if self.openai_key: return "openai"
        if self.gemini_key: return "gemini"
        return None

    def is_active(self) -> bool:
        return self.provider is not None

    def enrich(self, title: str, raw_desc: str, specs: Dict) -> str:
        """
        Sends text to LLM and returns professional retail copy.
        """
        if not self.is_active():
            raise RuntimeError("LLM provider not configured (missing API key).")

        prompt = f"""
        You are a premium Retail Copywriter for a high-end e-commerce store.
        
        TASK:
        Write a BRAND NEW, compelling, and consistent product description.
        
        RULES:
        1.  **SOURCE OF TRUTH**: Use the 'Raw Description' and 'Specs' as your PRIMARY source for specific details (Condition, Capacity, RAM, Accessories).
        2.  **KNOWLEDGE FILL**: Use your own knowledge ONLY to describe general features/benefits of the product model identified in the Title.
        3.  **CLEANUP**: IGNORE all marketing fluff ("We pawn", "Cash", "Finance", "Contact").
        4.  **FORMAT**:
            -   Hook Sentence.
            -   Paragraph on features (Subjective/Salesy is okay here).
            -   **"Condition & Inclusions"** (Strictly factual from Raw Text).
            -   **"Specifications"** (Formatted list from Specs data).
        
        INPUT DATA:
        Item Title: {title}
        Raw Description: {raw_desc}
        Specs: {json.dumps(specs)}
        
        OUTPUT:
        Return ONLY the final description text.
        """

        if self.provider == "openai":
            return self._call_openai(prompt)
        if self.provider == "gemini":
            return self._call_gemini(prompt)
        # No silent fallbacks: unknown provider must fail loudly.
        raise RuntimeError(f"Unknown LLM provider: {self.provider}")

    def gemini_model(self) -> str:
        """
        Returns a Gemini model id like 'gemini-2.0-flash' that exists for this API key.
        If GEMINI_MODEL is set, it must exist (otherwise raises).
        If not set, picks a reasonable default from the live model list.
        """
        if not self.gemini_key:
            raise RuntimeError("Gemini not configured (missing GEMINI_API_KEY).")

        wanted = (os.getenv("GEMINI_MODEL") or os.getenv("RETAILOS_GEMINI_MODEL") or "").strip()
        models = self.list_gemini_models()
        if wanted:
            w = wanted.replace("models/", "").strip()
            if w not in models:
                raise RuntimeError(f"GEMINI_MODEL '{w}' not available. Available (sample): {models[:25]}")
            return w

        # Prefer flash models for speed/cost
        for m in models:
            if "flash" in m and "gemini" in m:
                return m
        for m in models:
            if "gemini" in m:
                return m
        raise RuntimeError("No Gemini models available for this key.")

    def list_gemini_models(self) -> list[str]:
        """
        Lists available Gemini models for this API key (v1beta).
        Returns model ids without the 'models/' prefix.
        """
        if not self.gemini_key:
            return []
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_key}"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        out: list[str] = []
        for m in (data.get("models") or []):
            name = str(m.get("name") or "")
            if name.startswith("models/"):
                out.append(name.replace("models/", "", 1))
        # Stable order for UX
        out = sorted(set(out))
        return out

    def health(self) -> dict:
        """
        Returns a small health summary for operator diagnostics.
        Never fakes "healthy" when misconfigured.
        """
        provider = self.provider
        base = {"provider": provider, "active": bool(provider), "configured": bool(provider)}
        if provider is None:
            return {**base, "configured": False, "error": "No LLM provider configured (set GEMINI_API_KEY or OPENAI_API_KEY)."}
        try:
            if provider == "gemini":
                model = self.gemini_model()
                return {**base, "configured": True, "model": model, "models_sample": self.list_gemini_models()[:25]}
            if provider == "openai":
                return {**base, "configured": True, "model": "gpt-4o"}
            return {**base, "configured": False, "error": f"Unknown provider: {provider}"}
        except Exception as e:
            return {**base, "configured": False, "error": str(e)[:400]}

    def _call_openai(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        # Log Token Usage (Blueprint Req)
        usage = data.get("usage", {})
        try:
            from retail_os.dashboard.data_layer import log_audit
            from retail_os.core.database import SessionLocal
            db = SessionLocal()
            log_audit(db, "AI_COST", "Enricher", "OpenAI", 
                      old_val=None, 
                      new_val=f"in:{usage.get('prompt_tokens')}, out:{usage.get('completion_tokens')}")
            db.commit()
            db.close()
        except:
            pass # Don't fail flow for logs
            
        return data["choices"][0]["message"]["content"].strip()

    def _call_gemini(self, prompt: str) -> str:
        model = self.gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        import time
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, json=payload, timeout=20)
                if resp.status_code == 429:
                    # Rate Limit Hit - Backoff
                    wait = attempt * 2
                    print(f"⚠️ Rate Limit (429). Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                
                resp.raise_for_status()
                data = resp.json()
                
                # Log usage if available (Gemini sometimes puts it in metadata)
                try:
                    usage = data.get("usageMetadata", {})
                    if usage:
                        from retail_os.dashboard.data_layer import log_audit
                        from retail_os.core.database import SessionLocal
                        db = SessionLocal()
                        log_audit(db, "AI_COST", "Enricher", "Gemini", 
                                  old_val=None, 
                                  new_val=f"in:{usage.get('promptTokenCount')}, out:{usage.get('candidatesTokenCount')}")
                        db.commit()
                        db.close()
                except:
                    pass

                # Keep output clean (no provider prefix in production copy).
                val = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return val
                
            except requests.exceptions.HTTPError as e:
                # If non-429 error, raise immediately
                if e.response.status_code != 429:
                    raise e
            except Exception as e:
                # Network error? Retry.
                time.sleep(1)
        
        raise Exception("API Rate Limit Exceeded (429) after retries.")

# Singleton
enricher = LLMEnricher()
