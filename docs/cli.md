# CLI Reference

## pipelinex run

Run a pipeline.

```bash
pipelinex run ./my-pipeline
```

**Options:**

| Flag | Description |
|---|---|
| `--input TEXT` | Input text or path to a file. Available to the first step. |
| `--from STEP_ID` | Resume from a specific step (uses existing `state.json`). |
| `--watch` | Show live step transitions and tool calls during execution. |
| `--model PROVIDER/NAME` | Override the model for this run (e.g. `ollama/llama3.1`). |
| `--dry-run` | Validate config and env vars. Don't execute. |

**Examples:**

```bash
# Run with input
pipelinex run ./cv-pipeline --input "https://jobs.example.com/engineer"

# Resume after failure
pipelinex run ./my-pipeline --from step-03-validate

# Watch live progress
pipelinex run ./my-pipeline --watch

# Override model for this run only
pipelinex run ./my-pipeline --model anthropic/claude-sonnet-4-5

# Validate without running
pipelinex run ./my-pipeline --dry-run
```

---

## pipelinex new

Scaffold a pipeline, step, or tool.

```bash
# New pipeline
pipelinex new my-pipeline

# New step inside an existing pipeline
pipelinex new step step-05-review --in ./my-pipeline

# New tool inside an existing pipeline
pipelinex new tool send_email --in ./my-pipeline/tools
```

---

## pipelinex validate

Validate pipeline config without running. Checks:
- Required fields in `pipeline.yaml`
- `can_goto` targets exist as step IDs
- All referenced `${VAR}` are present in `.env` or the environment

```bash
pipelinex validate ./my-pipeline
```

---

## pipelinex tools

Manage tools.

```bash
# List available tools (built-ins + pipeline tools)
pipelinex tools list
pipelinex tools list --pipeline ./my-pipeline

# Install tool deps without running the pipeline
pipelinex tools install ./my-pipeline
```

`tools install` reads `deps` from every `tool.json` in the pipeline and installs them to `~/.pipelinex/envs/default`. This happens automatically on `run` too — use `install` to pre-warm or check deps.

---

## pipelinex log

Show the run log or error report from the last execution.

```bash
# Show run log (step transitions, tool calls, model responses)
pipelinex log ./my-pipeline

# Show error report from last failed run
pipelinex log ./my-pipeline --errors
```

**Error report** (`output/errors/`) contains:
- `report.md` — what failed, which step, what the model saw
- `state.json` — state at the point of failure
- `last-response.md` — the model's last response before failure

---

## Watch mode output

`--watch` shows:

```
[18:14:19] > step-01-ingest
[18:14:21]   | read_file({"path": "input/report.txt"})
[18:14:22]   | write_state({"key": "documents", ...})
[18:15:07] v step-01-ingest (done)
[18:15:07] > step-02-process
[18:15:11]   | dispatch_task({"task": "chunk intro-to-ml.txt", ...})
[18:18:11] v step-02-process → step-03-validate
```

`>` = step started, `v` = step finished, `|` = tool call.
