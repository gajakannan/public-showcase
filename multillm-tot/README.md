# 🧠 multiagent-convo

Simulate structured, multi-round conversations between AI personas using OpenAI-compatible models. Designed for running debates, ideation sessions, or roundtable discussions where each persona can contribute independently based on schema-defined traits.

---

## 🚀 Features

- Persona-driven AI replies using `OpenAI API` or any chat-completion-compatible backend.
- Supports round-based conversations with randomized engagement.
- Output in multiple formats: `markdown`, `html`, `json`, `tree`.
- Social media(reddit inspired) style threaded HTML export with engagement analytics.
- CLI-first, designed for scripting and automation.
- Persona schema validation using `jsonschema`.

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

Run a 5-round discussion about frontend frameworks:

```bash
python main.py \
  --prompt "You all work for Acme corp, and discussing about next big web application and tool set to use for that application" \
  --rounds 5 \
  --personas-file "./input/frontend-personas.json" \
  --output html \
  --save-to "./output/frontend-discussion.html"
```

Microservices vs Modular Monoliths (8 rounds):

```bash
python main.py \
  --prompt "With increased complexity should we relook proliferation of Microservice and build Modular Monoliths" \
  --rounds 8 \
  --personas-file "./input/microservice-personas.json" \
  --output html \
  --save-to "./output/microservice-discussion.html"
```

AI replacing Primary Care Physicians (20 rounds):

```bash
python main.py \
  --prompt "Can a specialized AI or AGI replace primary care physicians" \
  --rounds 20 \
  --personas-file "./input/pcp-personas.json" \
  --output html \
  --save-to "./output/pcp-discussion.html"
```

Windows PowerShell equivalents:

```powershell
python main.py `
  --prompt "You all work for Acme corp, and discussing about next big web application and tool set to use for that application" `
  --rounds 5 `
  --personas-file "./input/frontend-personas.json" `
  --output html `
  --save-to "./output/frontend-discussion.html"

python main.py `
  --prompt "With increased complexity should we relook proliferation of Microservice and build Modular Monoliths" `
  --rounds 8 `
  --personas-file './input/microservice-personas.json' `
  --output html `
  --save-to "./output/microservice-discussion.html"

python main.py `
  --prompt "Can a specialized AI or AGI replace primary care physicians" `
  --rounds 20 `
  --personas-file './input/pcp-personas.json' `
  --output html `
  --save-to "./output/pcp-discussion.html"

```

---

## 📁 Input Files

- `*.json`: Define your personas with fields like `name`, `llm`, `model`, and `engagement`.
- `persona.schema.json`: JSON Schema used to validate persona definitions before execution.

Example persona:
```json
{
  "name": "react developer",
  "llm": "ChatGPT",
  "model": "gpt-3.5-turbo",
  "engagement": 0.8
}
```

---

## 📝 Output Formats

- `markdown`: Easy-to-read threaded summary.
- `html`: Richly styled thread explorer (with colors, badges, and metadata).
- `json`: Raw tree-structured output.
- `tree`: Textual, indented view of conversation depth.

---

## 💠 Development & TODOs

See [`TODO.md`](./TODO.md) for planned enhancements:
- Reference-aware prompts
- Multi-provider LLM support
- CI persona schema validation

---

## 📄 License

MIT

---

## ✨ Contributions Welcome

Feel free to submit PRs for:
- New output formats
- Persona enhancements
- Plug-in architecture for other LLM providers


