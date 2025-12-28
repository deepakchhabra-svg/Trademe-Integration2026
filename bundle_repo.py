import os

def bundle(out="repo_bundle.txt"):
    ignore = {".git", "__pycache__", "venv", ".venv", "data", "logs", ".env", out, "bundle_repo.py"}
    with open(out, "w", encoding="utf-8") as f:
        for r, d, files in os.walk("."):
            for file in files:
                path = os.path.join(r, file)
                if any(x in path for x in ignore):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as src:
                        content = src.read()
                        f.write(f"\n{'='*50}\nFILE: {path}\n{'='*50}\n\n{content}\n")
                except:
                    continue
    print(f"Successfully created: {out}")

if __name__ == "__main__":
    bundle()
