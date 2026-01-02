
import os
import re
import pytest

WEB_ROOT = os.path.join(os.path.dirname(__file__), "..", "services", "web", "src")

def test_frontend_no_direct_fetch():
    """
    Contract: Frontend code must use apiGet/apiPostClient helpers, not raw fetch() or axios,
    to ensure auth headers and error handling are consistent.
    """
    if not os.path.exists(WEB_ROOT):
        pytest.skip("Frontend source not found")

    # Patterns to forbid
    # We allow "fetch" inside api_client.ts itself
    forbidden = [
        (re.compile(r"fetch\("), "Direct fetch() call"),
        (re.compile(r"axios\."), "Direct axios usage"),
    ]

    violations = []

    for root, _, files in os.walk(WEB_ROOT):
        for file in files:
            if not file.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue
            
            # Skip the client wrapper itself
            if "api_client.ts" in file or "api.ts" in file:
                continue
            
            path = os.path.join(root, file)

            # Skip Next.js API Routes (proxies) as they legitimately use fetch()
            if "src\\app\\api\\" in path or "src/app/api/" in path:
                continue
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                # Simple comment filtering
                if line.strip().startswith("//"):
                    continue

                for pattern, msg in forbidden:
                    if pattern.search(line):
                        violations.append(f"{path}:{i+1} - {msg}: {line.strip()}")

    assert not violations, "Found forbidden direct API calls in frontend source:\n" + "\n".join(violations)
