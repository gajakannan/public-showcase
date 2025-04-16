# 🧠 multiagent-convo

Simulate structured, multi-round conversations between AI personas using OpenAI-compatible models. Designed for running debates, ideation sessions, or goal-driven discussions where each persona can contribute independently based on schema-defined traits.

---

## 🚀 Features

- Persona-driven AI replies using `OpenAI API` or any chat-completion-compatible backend.
- Supports round-based conversations with randomized engagement.
- Goal round support (`decision`, `summary`, `consensus`, `reflection`, `rebuttal`)
- Per-persona references (file or vector-based) with Qdrant RAG integration
- RAG-based chunk retrieval with deduplication logic
- Output in multiple formats: `markdown`, `html`, `json`, `tree`
- Social media (Reddit-inspired) style threaded HTML export with engagement analytics
- CLI-first, designed for scripting and automation
- Persona schema validation using `jsonschema`

---

## ⚙️ Setup

### 1. Clone and Install

```bash
git clone https://github.com/yourname/multiagent-convo.git
cd multiagent-convo

# Setup Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Set your API Key

```bash
# macOS/Linux
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."
```

---

## 🧪 Example Usage

```powershell
# powershell

python main.py `
--prompt "You are developing a personalized care plan for Mrs. Elaine Carter, a 62-year-old woman recovering from a total left hip replacement. Collaborate across clinical, care coordination, and family perspectives to ensure a safe recovery, appropriate support services, and readiness for outpatient transition." `
--rounds 2 `
--personas-file './input/caremgmt-hip/care-personas.json' `
--output html `
--save-to './output/caremgmt-hip/care-plan-discussion.html' `
--goal-round decision 
```


```bash

# bash
python main.py \
--prompt "You are developing a personalized care plan for Mrs. Elaine Carter, a 62-year-old woman recovering from a total left hip replacement. Collaborate across clinical, care coordination, and family perspectives to ensure a safe recovery, appropriate support services, and readiness for outpatient transition." \
--rounds 2 \
--personas-file './input/caremgmt-hip/care-personas.json' \
--output html \
--save-to './output/caremgmt-hip/care-plan-discussion.html' \
--goal-round decision 

```

---

## 📁 Input Files

- `*.json`: Define your personas with fields like `name`, `llm`, `model`, `references`, etc.
- `persona.schema.json`: JSON Schema used to validate persona definitions before execution.

---

## 📝 Output Formats

- `markdown`: Easy-to-read threaded summary.
- `html`: Richly styled thread explorer (with colors, badges, and metadata).
- `json`: Raw tree-structured output.
- `tree`: Textual, indented view of conversation depth.

---

## 🔗 Vector Embedding Setup

One time docker setup
Note: This will start Qdrant locally using Docker Compose.

```bash
docker compose -f docker-compose-qdrant.yml up -v
```

Ongoing everytime you need the vector embedding updated. At this moment, we delete everything and add new

```bash

# For Care Management

# delete collections
curl -X DELETE http://localhost:6333/collections/care_guidelines

# create vector embeddings
docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e QDRANT_HOST=host.docker.internal \
  -v "${PWD}/vector-setup:/app" \
  multillm-tot-vector-setup \
  python /app/upload_to_qdrant.py \
    --folder /app/caremgmt-hip \
    --manifest /app/hello-care-guidelines.json \
    --collection care_guidelines

# list collections
curl -X POST http://localhost:6333/collections/care_guidelines/points/scroll \
-H 'Content-Type: application/json' \
-d '{"limit": 100, "with_payload": true}'


# for Underwriting

# delete collections
curl -X DELETE http://localhost:6333/collections/underwriting_manual

# creating vector embeddings

docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e QDRANT_HOST=host.docker.internal \
  -v "${PWD}/vector-setup:/app" \
  multillm-tot-vector-setup \
  python /app/upload_to_qdrant.py \
    --folder /app/underwriting-auto \
    --manifest /app/hello-underwriting-manual.json \
    --collection underwriting_manual

# list collections

curl -X POST http://localhost:6333/collections/underwriting_manual/points/scroll \
-H 'Content-Type: application/json' \
-d '{"limit": 100, "with_payload": true}'

```


## 💠 Development & TODOs

See [`TODO.md`](./TODO.md) for planned enhancements:

---

## 📄 License

MIT

---

## ✨ Contributions Welcome

Feel free to submit PRs for:
- Plug-in architecture for other LLM providers


