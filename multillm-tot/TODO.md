# TODO: Persona-Driven Conversation Enhancements

This document tracks upcoming improvements to the multi-agent conversation CLI.

---

## ✅ Completed

- [x] Switch from `--personas` CLI arg to `--personas-file`
- [x] Read and parse persona data using `json.load()` instead of `json.loads()`
- [x] Update `parse_personas()` to accept list input instead of raw JSON string
- [x] Add `model` field per persona for LLM selection
- [x] Pretty-print persona JSON files for readability

---

## 🔜 Next Steps

### 1. JSON Schema Validation
- [x] Create JSON Schema for persona structure (required: `name`, `llm`, `model`)
- [x] Integrate validation using `jsonschema` before parsing
- [ ] Add CI validation for all persona files (optional)

### 2. Add References Field
- [ ] Allow each persona to specify a list of `references`
  - Example:
    ```json
    "references": [
      { "type": "url", "value": "https://example.com/doc" },
      { "type": "file", "value": "docs/concepts.md" }
    ]
    ```
- [ ] Update persona files to include sample references

### 3. Incorporate References into Prompts
- [ ] Prepend relevant reference content to system/user prompts in `agent_reply()`
- [ ] Support loading reference file contents safely
- [ ] (Optional) Sanitize and summarize large reference documents

---

## ⚙️ Future Enhancements

- [ ] Support multiple LLM providers based on `llm` field
- [ ] Per-persona LLM tuning (e.g., temperature, top_p)
- [ ] Persona-specific memory (state tracking)
- [ ] Reference caching for performance

---

