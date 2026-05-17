# State & Handoffs

## What state is

`output/state.json` is the pipeline's shared memory. Every step can read from it and write to it. The runner injects relevant parts into each step's context automatically.

Think of it as the shared desk between steps — not a database, not a log. Just the current working surface.

---

## Writing to state

The model uses the `write_state` built-in tool:

```
write_state(key="summary", value="47 documents processed...")
write_state(key="failed", value=["doc-12", "doc-31"])
write_state(key="config", value={"threshold": 0.8, "language": "en"})
```

Values can be strings, numbers, lists, or objects. Multiple writes in one step are merged. Earlier keys are preserved unless overwritten.

---

## Reading from state

The runner injects state into each step's context automatically — the model doesn't need to call a tool to read it. It's already there when the step starts.

Steps can also use `read_file` to load large content from output files rather than storing it in state. State is for small, structured data; files are for large, raw content.

---

## The handoff note

Every step should leave a handoff note before finishing:

```
write_state(key="handoff", value="Processed 47 documents. 45 indexed, 2 failed (see 'failed' list).")
```

The runner injects the handoff at the top of the next step's context automatically. It's the sticky note on the desk — gives the next step orientation without reading everything that came before.

In SKILL.md, just ask for it:

```markdown
## Task
...do the work...

Before finishing, leave a brief handoff note summarising what was done
and what the next step should know.
```

---

## Context injection tiers

When a step runs, the runner asks the model to classify each state key based on the `## Context` section of the SKILL.md. Keys the model marks `skip` are excluded entirely.

```markdown
## Context

The "documents" list from step-01 is essential — read it in full.
You don't need the raw ingestion logs.
```

The model sees the context section and decides which keys matter. Skipped keys stay in `state.json` on disk — they just aren't injected.

---

## Resuming a run

If a pipeline fails mid-run, resume from a specific step:

```bash
folpipe run ./my-pipeline --from step-03-validate
```

The runner loads the existing `state.json` and picks up from there. State written by completed steps is preserved.

**Version mismatch warning:** If `pipeline.yaml` has a different `version` than when the state was saved, the runner warns before continuing:

```
WARNING: Pipeline version mismatch — saved state is v1.0.0, current pipeline is v1.1.0.
State structure may have changed.
```

This is a warning, not a stop — the run continues, but check that state keys from earlier steps are still valid.

---

## state.json structure

```json
{
  "_meta": {
    "started": "2026-05-17T18:00:00",
    "pipeline_version": "1.0.0",
    "current_step": "step-03-validate",
    "completed_steps": ["step-01-ingest", "step-02-process"]
  },
  "handoff": "Processed 3 documents into 9 chunks.",
  "documents": [...],
  "processed": [...],
  "failed": []
}
```

`_meta` is managed by the runner. Everything else is written by the model via `write_state`.
