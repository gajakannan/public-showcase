# TODO: Persona-Driven Conversation Enhancements

This document tracks upcoming improvements to the multi-agent conversation CLI.

---

## ✅ Completed

- [x] Switch from `--personas` CLI arg to `--personas-file`
- [x] Read and parse persona data using `json.load()` instead of `json.loads()`
- [x] Update `parse_personas()` to accept list input instead of raw JSON string
- [x] Add `model` field per persona for LLM selection
- [x] Pretty-print persona JSON files for readability
- [x] Add `references` field to persona schema (file and vector-based)
- [x] Incorporate references into persona prompts
- [x] Add Qdrant vector search and deduplication logic
- [x] Add goal round support with configurable types (`decision`, `summary`, etc.)
- [x] Refactor retrieval pipeline into 3-stage structure (embedding, storage, retrieval)

---

## 🔜 Next Steps

### 1. Input Management
- [ ] Chunk large documents during upload
- [ ] Add support for external URLs in `references`
- [ ] Implement source refresh strategies for CAG-like data

### 2. Persona and Agent Enhancements
- [ ] Add support for additional goal types: summary, consensus, reflection, rebuttal
- [ ] Add support for persona-specific memory or state
- [ ] Implement voting, exploration, or route pruning among agents
- [ ] Add semantic grouping for reference context injection

### 3. Visualization & UX
- [ ] Introduce mindmap/workflow view of agent threads
- [ ] Add tree graph visualization to HTML output
