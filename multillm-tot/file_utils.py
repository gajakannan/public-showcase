
# -----------------------------
# Loading all reference files
# -----------------------------
def load_file_reference(path, max_chars=3000):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return content[:max_chars]
    except Exception as e:
        return f"[Could not load file: {path} – {str(e)}]"