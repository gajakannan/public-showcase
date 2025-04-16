import json
import uuid
import os
import argparse
from pathlib import Path
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

# Initialize OpenAI client
openai_client = OpenAI()

# CLI + ENV fallback
parser = argparse.ArgumentParser(description="Upload domain-specific markdown documents to Qdrant")

parser.add_argument(
    "--folder",
    required=True,
    help="Base folder where the markdown files referenced in the JSON live"
)
parser.add_argument(
    "--manifest",
    required=True,
    help="Path to the manifest JSON (e.g., hello-underwriting-manual.json)"
)
parser.add_argument(
    "--collection",
    required=True,
    help="Qdrant collection name (e.g., underwriting_manual, care_guidelines)"
)
parser.add_argument(
    "--host",
    default=os.environ.get("QDRANT_HOST", "localhost"),
    help="Qdrant host"
)
parser.add_argument(
    "--port",
    type=int,
    default=int(os.environ.get("QDRANT_PORT", 6333)),
    help="Qdrant port"
)

args = parser.parse_args()

# Setup Qdrant client
qdrant = QdrantClient(host=args.host, port=args.port)
VECTOR_SIZE = 1536
VECTOR_NAME = "content_embedding"

# Create collection if it doesn't exist
if not qdrant.collection_exists(collection_name=args.collection):
    qdrant.create_collection(
        collection_name=args.collection,
        vectors_config={VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)}
    )
    print(f"✅ Created collection: {args.collection}")

# Load JSON manifest
with open(args.manifest, "r", encoding="utf-8") as f:
    documents = json.load(f)

base_folder = Path(args.folder)
batch = []

for doc in documents:
    doc_path = base_folder / doc["filename"]
    if not doc_path.exists():
        print(f"[ERROR] File not found: {doc_path}")
        continue

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=content
    )
    embedding = response.data[0].embedding

    point = PointStruct(
        id=str(uuid.uuid4()),
        vector={VECTOR_NAME: embedding},
        payload={
            "section_id": doc.get("section_id"),
            "title": doc.get("title"),
            "filename": doc.get("filename"),
            "product": doc.get("product"),
            "tags": [tag.lower() for tag in doc.get("tags", [])],
            "content": content
        }
    )
    batch.append(point)

qdrant.upsert(collection_name=args.collection, points=batch)
print(f"✅ Uploaded {len(batch)} documents to Qdrant in collection '{args.collection}'.")
