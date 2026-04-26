# Work Session: Local LLM for Company Validation

**Date:** 2026-04-26

## Goal

Replace the `/validate-company` Claude skill (manual, slow, overkill) with a fully automated Python script that uses a local LLM to batch-validate company web presence.

## Approach

Feed each company's SIREN data + DDG search results to a local LLM in a single prompt, ask it to pick the best match and assign a confidence level (`good` / `strange` / `wrong`), output 3 lines. Append results to `status.csv`.

Script created: `tools/llm_validate.py`
- Loops over all DDG files (or specific SIRENs)
- Builds a compact prompt (~800 tokens): official name, NAF code, city, top 8 search results
- Calls Ollama via the `ollama` Python lib
- Parses `MATCH / CONFIDENCE / REASON` from response
- Appends to `data/company_data/insights/status.csv`
- Supports `--dry-run`, `--skip-existing`, `--model` flags

## Hardware Constraints Discovered

**GPU:** Quadro K2200 — 4GB VRAM  
**Problem:** Most 3b+ models crash with `cudaMalloc failed: out of memory` or a segfault in the CPU runner.

- `qwen3:4b` — works (splits 52% CPU / 48% GPU), but has a thinking mode that produces very verbose output; `<think>` blocks stripped in parser
- `qwen2.5:3b` — segfault on load (corrupted blob or runner bug)
- `phi4-mini:3.8b` — segfault on load
- `llama3.2:3b` — not tested
- `OLLAMA_NUM_GPU=0` (force CPU) — also crashes, points to bug in Ollama 0.18.x CPU runner

**Workaround in script:** `num_ctx: 2048` (half of default 4096) to reduce KV cache VRAM usage.

## Current State

Script is written and functional in structure. `qwen3:4b` is the only confirmed working model. The `<think>` block stripping via regex handles the verbose output.

## Next Steps

- Test full batch run with `qwen3:4b`
- Consider Groq free tier (OpenAI-compatible API) as fallback — `llama-3.1-8b-instant` would be faster and cleaner than local 4b
- If adding Groq: `--provider groq` flag, keep Ollama as default
