from file_utils import load_file_reference

# -----------------------------
# Add referenced files to each personas
# -----------------------------
def enrich_personas_with_file_references(personas, max_chars=3000):
    for persona in personas:
        resolved = []
        for ref in persona.get("references", []):
            if ref["type"] == "file":
                resolved.append({
                    "path": ref["value"],
                    "content": load_file_reference(ref["value"], max_chars=max_chars)
                })
                print(f"[blue]Resolved file for {persona['name']}:[/blue] {ref['value']}")
        persona["resolved_file_references"] = resolved


    return personas
