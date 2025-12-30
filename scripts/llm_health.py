import json

from retail_os.core.llm_enricher import enricher


def main() -> None:
    print("LLM health\n---------")
    h = enricher.health()
    print(json.dumps(h, indent=2))
    if h.get("provider") == "gemini" and h.get("configured"):
        print("\nGemini models (sample)\n----------------------")
        for m in (h.get("models_sample") or []):
            print("-", m)


if __name__ == "__main__":
    main()

