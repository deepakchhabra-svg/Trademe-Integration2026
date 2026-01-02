import json
import csv
from pathlib import Path
import os

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "operations_registry.json"
CATALOG_PATH = REPO_ROOT / "docs" / "ui-action-catalog-gen.csv"
USE_CASES_PATH = REPO_ROOT / "docs" / "backend-use-cases-gen.md"

def main():
    if not REGISTRY_PATH.exists():
        print(f"Registry not found at {REGISTRY_PATH}")
        return

    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)
        registry = data.get("operations", {})

    print(f"Generating docs from {len(registry)} operations...")

    # Generate CSV
    with open(CATALOG_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["operation_id", "uri", "method", "auth", "description", "payload"])
        for op_id, op in registry.items():
            payload = op.get("payload", {})
            payload_keys = "|".join(payload.keys()) if isinstance(payload, dict) else str(payload)
            writer.writerow([
                op_id, 
                op["uri"], 
                op["method"], 
                op.get("auth", ""), 
                op.get("description", ""),
                payload_keys
            ])
    print(f"Functions generated: {CATALOG_PATH}")
    
    # Generate MD
    with open(USE_CASES_PATH, "w", encoding="utf-8") as f:
        f.write("# Backend Use Cases\n\n")
        f.write("> **Source:** `docs/operations_registry.json`\n\n")
        f.write("| Operation ID | URI | Method | Auth | Description |\n")
        f.write("|---|---|---|---|---|\n")
        for op_id, op in registry.items():
            f.write(f"| `{op_id}` | `{op['uri']}` | **{op['method']}** | {op.get('auth','')} | {op.get('description','')} |\n")
    print(f"Functions generated: {USE_CASES_PATH}")

if __name__ == "__main__":
    main()
