from file_utils import load_file_reference
import sys
import hashlib
from pathlib import Path
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue


# -----------------------------
# Add referenced files to each personas
# -----------------------------
import sys
from pathlib import Path

def enrich_personas_with_file_references(personas, max_chars=3000):
    for persona in personas:
        resolved = []
        qdrant_titles = []  # ✅ initialize here

        for ref in persona.get("references", []):
            if ref["type"] == "file":
                file_path = ref["value"]
                if not Path(file_path).exists():
                    print(f"[red]ERROR: File not found for {persona['name']}[/red]: {file_path}")
                    sys.exit(1)
                try:
                    resolved.append({
                        "path": file_path,
                        "content": load_file_reference(file_path, max_chars=max_chars)
                    })
                    print(f"[blue]Resolved file for {persona['name']}:[/blue] {file_path}")
                except Exception as e:
                    print(f"[red]ERROR reading file {file_path} for {persona['name']}[/red]: {e}")
                    sys.exit(1)

            elif ref["type"].startswith("vector:qdrant"):
                try:
                    query_seed = persona.get("regular_prompt")
                    if not query_seed:
                        print(f"[yellow]Warning: No regular_prompt found for {persona['name']} — skipping Qdrant lookup.[/yellow]")
                        continue

                    print(f"[green]Querying Qdrant for {persona['name']} using:[/green] {ref['value']}")
                    matches = get_qdrant_matches(  
                        query_text=query_seed,
                        filter_value=ref["value"].replace("vector:qdrant:", ""),
                        top_k=3
                    )
                    resolved += matches
                    qdrant_titles += [match["path"] for match in matches if match["path"].startswith("[Qdrant match")]

                except Exception as e:
                    print(f"[red]ERROR querying Qdrant for {persona['name']}[/red]: {e}")
                    sys.exit(1)

        persona["resolved_file_references"] = resolved
        if qdrant_titles:
            persona["resolved_qdrant_titles"] = qdrant_titles  

    return personas




# -----------------------------
# Retrieve top matching chunks from Qdrant
# -----------------------------
def get_qdrant_matches(query_text, filter_value, top_k=3):
    # field, value = filter_value.split(":", 1)

    try:
        # Require and parse both collection and filter key=value pair(s)
        parts = dict(part.split("=", 1) for part in filter_value.split(","))
        if "collection" not in parts:
            raise ValueError("Missing required 'collection=' in filter_value")

        collection_name = parts["collection"]
        # Only support a single filter field for now (excluding 'collection')
        filter_fields = [(k, v) for k, v in parts.items() if k != "collection"]
        if len(filter_fields) != 1:
            raise ValueError("filter_value must contain exactly one field to filter on (besides 'collection')")

        field, value = filter_fields[0]
    except Exception as e:
        print(f"[red]ERROR parsing Qdrant filter_value:[/red] {filter_value} – {e}")
        sys.exit(1)

    client = QdrantClient(host="localhost", port=6333)
    vector = OpenAI().embeddings.create(
        input=query_text,
        model="text-embedding-3-small"
    ).data[0].embedding

    results = client.search(
        collection_name=collection_name,
        query_vector={"name": "content_embedding", "vector": vector},
        limit=top_k,
        query_filter=Filter(
            must=[FieldCondition(key=field, match=MatchValue(value=value))]
        )
    )

    # Deduplicate by title and hash
    seen_titles = set()
    seen_hashes = set()
    unique_matches = []

    for pt in results:
        title = pt.payload.get("title", "unknown")
        content = pt.payload.get("content", "")
        # content_hash = hash(content)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        if title not in seen_titles and content_hash not in seen_hashes:
            seen_titles.add(title)
            seen_hashes.add(content_hash)
            unique_matches.append({
                "path": f"[Qdrant match: {title}]",
                "content": f"{title}\n\n{content}"
            })

    return unique_matches


# -----------------------------
# Generate a 2–3 sentence summary of the discussion.
# -----------------------------
def summarize_discussion(messages, client, model="gpt-4o"):
    summary_prompt = (
        "Summarize this multi-agent discussion in 2–3 sentences. "
        "Focus on the topic, key decisions or arguments, and the overall outcome. "
        "Avoid naming specific personas."
    )

    full_text = "\n\n".join([f"{m['persona']}: {m['text']}" for m in messages if m.get("text")])

    messages = [
        {"role": "system", "content": "You are a helpful summarizer of multi-agent conversations."},
        {"role": "user", "content": summary_prompt + "\n\n" + full_text}
    ]

    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content.strip()
