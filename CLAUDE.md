# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`folpipe` — a folder-based agentic AI pipeline framework. A pipeline is a directory; each step is a subdirectory with a `SKILL.md` (plain-English instructions) and optional custom tools. No programming required to build pipelines.

Package lives at `src/pipelinex/`. Installed CLI command: `folpipe`.

## Commands

```bash
# Install for development
pip install -e .

# Run tests
pytest tests/

# Run a pipeline
folpipe run ./examples/doc-pipeline
folpipe run ./examples/doc-pipeline --watch          # live progress
folpipe run ./examples/doc-pipeline --from step-03   # resume from step
folpipe run ./examples/doc-pipeline --dry-run        # validate only

# Scaffold
folpipe new my-pipeline
folpipe new step step-05-review --in ./my-pipeline
folpipe new tool send_email --in ./my-pipeline/tools

# Debug
folpipe log ./examples/doc-pipeline
folpipe log ./examples/doc-pipeline --errors
folpipe validate ./examples/doc-pipeline
```

## Architecture

### Execution flow

`PipelineRunner` (`runner.py`) drives the loop:

1. **Loader** (`loader.py`) reads `pipeline.yaml`, `.env` (with `${VAR}` substitution), and SKILL.md files.
2. For each step: build context → call LLM → execute tool calls → repeat until step is complete.
3. **ContextMgr** (`context_mgr.py`) manages token budget via 3-tier state classification: `essential` (always injected), `include` (summarized if tight), `skip` (never injected). Classification is stored in step SKILL.md or auto-derived by a fast model call.
4. **State** (`state.py`) persists a shared `state.json` across all steps. Steps leave handoff notes for successors.
5. Routing: model can output `{"next": "step-id"}` to branch; validated against `can_goto` whitelist in `pipeline.yaml`.

### Tool system

Resolution order: substep-local → step-local → pipeline-level → global cache (`~/.pipelinex/tools/`) → built-ins.

10 built-ins in `tools/builtin.py`: `read_file`, `write_file`, `write_state`, `web_search`, `http_request`, `run_script`, `extract_json`, `template`, `dispatch_task`, `ask_human`.

Custom tools: a folder containing `tool.json` (MCP-compatible schema) + `run.py`/`run.sh`/`run.js`. Tool receives JSON on stdin, outputs JSON to stdout; non-zero exit = failure. Optional `deps` array is auto-installed to `~/.pipelinex/envs/default` before first run.

`dispatch_task` enables parallel sub-steps: multiple calls in a single LLM response are detected and executed concurrently up to `dispatch.max_parallel`.

### SKILL.md cascading

Instructions merge: global `SKILL.md` → step `SKILL.md` → substep `SKILL.md`. Later files extend/override earlier ones. The `## Context` section controls state tier classification.

### Model layer

`model.py` wraps LiteLLM. Provider/model set in `pipeline.yaml`; per-step overrides allowed for cost optimization. Tool-calling capability is verified at startup. Fallback model config supported.

### Logging

`logger.py` writes structured JSON to `output/run.log`. Errors dump to `output/errors/` (report.md, state snapshot, last LLM response). `--watch` streams colorized live output.

## Key files

| File | Purpose |
|---|---|
| `src/pipelinex/runner.py` | Main execution loop, step orchestration, self-reflection |
| `src/pipelinex/loader.py` | Pipeline config & SKILL.md loading |
| `src/pipelinex/context_mgr.py` | Token budget & context tier management |
| `src/pipelinex/tools/builtin.py` | All 10 built-in tool implementations |
| `src/pipelinex/tools/resolver.py` | Tool discovery & dep installation |
| `PIPELINE_SPEC.md` | Full technical specification (authoritative reference) |
