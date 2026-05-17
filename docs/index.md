# pipelinex

Folder-based agentic AI pipeline framework. No programming required to use.

---

## What it is

A pipeline is a folder. Drop it anywhere, zip it, share it, version it in git.
Instructions live in plain-English markdown files. Tools are drop-in folders.
The model is swappable with one line.

```
pipelinex run ./my-pipeline
```

That's it.

---

## Core ideas

| Idea | What it means |
|---|---|
| **Pipeline = folder** | Everything self-contained. No server, no database, no cloud account. |
| **Instructions = markdown** | SKILL.md files are the "code." Plain English. |
| **Tools = drop-in** | Add a folder to `tools/`. Done. |
| **Model = swappable** | Change one line in `pipeline.yaml`. Steps never know which model runs them. |
| **Failures = natural language** | Error handling lives in SKILL.md, not in runner logic. |

---

## Pages

- [Getting Started](getting-started.md) — install, create a pipeline, run it
- [Pipeline Structure](pipeline-structure.md) — folders, `pipeline.yaml`, `SKILL.md`
- [State & Handoffs](state.md) — shared memory between steps
- [Tools](tools.md) — built-in tools, custom tools, tool resolution
- [Execution Patterns](execution-patterns.md) — linear, branching, loops, parallel dispatch, sub-steps
- [Context Management](context-management.md) — what gets injected into each step
- [Human Input](human-input.md) — pausing for human decisions
- [CLI Reference](cli.md) — all commands
- [Examples](examples.md) — doc-pipeline and cv-pipeline walkthroughs
