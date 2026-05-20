# CLI Reference

## folpipe run

Run a pipeline.

```bash
folpipe run ./my-pipeline
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
folpipe run ./cv-pipeline --input "https://jobs.example.com/engineer"

# Resume after failure
folpipe run ./my-pipeline --from step-03-validate

# Watch live progress
folpipe run ./my-pipeline --watch

# Override model for this run only
folpipe run ./my-pipeline --model anthropic/claude-sonnet-4-6

# Validate without running
folpipe run ./my-pipeline --dry-run
```

---

## folpipe new

Scaffold a pipeline, step, or tool.

```bash
# New pipeline
folpipe new my-pipeline

# New step inside an existing pipeline
folpipe new step step-05-review --in ./my-pipeline

# New tool inside an existing pipeline
folpipe new tool send_email --in ./my-pipeline/tools
```

`--in` is optional for `step` and `tool` — the runner auto-detects the pipeline by walking up from the current directory. Run with no arguments for interactive mode:

```bash
folpipe new
# prompts: What to create? (pipeline / step / tool), then Name
```

---

## folpipe add

Add a step or tool to the pipeline in the current directory. Auto-detects the pipeline from cwd by looking for `pipeline.yaml`.

```bash
# Add a step
folpipe add step step-05-review

# Add a tool
folpipe add tool send_email
```

Both commands accept `--in` to target a specific pipeline directory instead of auto-detecting.

---

## folpipe validate

Validate pipeline config without running. Checks:
- Required fields in `pipeline.yaml`
- `can_goto` targets exist as step IDs
- All referenced `${VAR}` are present in `.env` or the environment

```bash
folpipe validate ./my-pipeline
```

---

## folpipe tools

Manage tools.

```bash
# List available tools (built-ins + pipeline tools)
folpipe tools list
folpipe tools list --pipeline ./my-pipeline

# Install tool deps without running the pipeline
folpipe tools install ./my-pipeline
```

`tools install` reads `deps` from every `tool.json` in the pipeline and installs them to `~/.pipelinex/envs/default`. This happens automatically on `run` too — use `install` to pre-warm or check deps.

---

## folpipe log

Show the run log or error report from the last execution.

```bash
# Show run log (step transitions, tool calls, model responses)
folpipe log ./my-pipeline

# Show error report from last failed run
folpipe log ./my-pipeline --errors
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
