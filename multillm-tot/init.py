
import json
from openai import OpenAI
from pathlib import Path

def get_openai_client():
    return OpenAI()

def load_persona_schema(schema_path: str = "persona.schema.json"):
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
