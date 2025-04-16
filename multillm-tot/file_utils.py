from pathlib import Path

# -----------------------------
# Loading all reference files
# -----------------------------
def load_file_reference(path, max_chars=3000):
    if not Path(path).exists():
        raise FileNotFoundError(f"Reference file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()[:max_chars]
