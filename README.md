# folpipe

Folder-based agentic AI pipeline framework. No programming required to use.

```bash
pip install folpipe
folpipe run ./my-pipeline --watch
```

---

## The idea

A pipeline is a folder. Instructions live in plain-English markdown files. Tools are drop-in folders. The model is swappable with one line.

```
my-pipeline/
├── pipeline.yaml       ← steps, model, routing
├── SKILL.md            ← global instructions (plain English)
├── .env                ← API keys
├── input/              ← drop files here
├── output/             ← results land here
├── tools/              ← drop-in custom tools
├── step-01-ingest/
│   └── SKILL.md        ← what this step does
└── step-02-process/
    ├── SKILL.md
    └── sub-01-chunk/   ← sub-steps, recursively
        └── SKILL.md
```

Zip the folder, share it, version it in git. No server, no database, no cloud account.

---

## Quick start

**1. Install**

```bash
pip install folpipe
```

**2. Create a pipeline**

```bash
folpipe new my-pipeline
cd my-pipeline
```

**3. Configure the model** — edit `.env`:

```bash
DEEPSEEK_API_KEY=sk-...
```

**4. Write your step** — edit `step-01-start/SKILL.md`:

```markdown
# Summarise input

Read the file from input/ and write a 3-paragraph summary to output/summary.md.

## Task

Use read_file to read the input file.
Use write_file to write output/summary.md.
Leave a handoff note when done.
```

**5. Run it**

```bash
cp myfile.txt input/
folpipe run . --watch
```

---

## What it can do

**Linear pipelines** — steps run in order, each hands off to the next via shared state.

**Agent branching** — the model decides which step comes next from a declared whitelist:

```yaml
- id: step-03-validate
  can_goto: [step-04-output, step-05-partial-output]
```

**Parallel dispatch** — the model fires multiple `dispatch_task` calls in one response; the runner detects the batch and executes them concurrently:

```markdown
## Task
Process all documents at once — send them all for chunking
in the same breath rather than one at a time.
```

**Sub-steps** — steps contain named sub-step folders with their own SKILL.md and tools:

```
dispatch_task(task="chunk intro-to-ml.txt", substep="sub-01-chunk", context={...})
```

**Human-in-the-loop** — steps can pause for console input, file review, or a custom tool (Slack, email, webhook):

```yaml
- id: step-03-review
  human_input:
    mode: console
    prompt: "Approve this output? (yes/no):"
```

**Model-driven context** — each step's `## Context` section tells the model what state to pay attention to and what to ignore. Skip signals are respected; the model never sees irrelevant data.

**Any model** — DeepSeek, Anthropic, OpenAI, Ollama, Groq, or any OpenAI-compatible endpoint. Change one line in `pipeline.yaml`. Optional per-step overrides for cost optimisation.

---

## Custom tools

Drop a folder into `tools/`:

```
tools/
└── send_slack/
    ├── tool.json    ← MCP-compatible schema + deps declaration
    └── run.py       ← stdin JSON in, stdout JSON out
```

```json
{
  "name": "send_slack",
  "description": "Post a message to a Slack channel. Use for approvals and failures that need human eyes.",
  "inputSchema": { ... },
  "deps": ["slack-sdk"]
}
```

Dependencies declared in `deps` are installed automatically before the first run. No manual `pip install`.

Any language works — `run.py`, `run.sh`, or `run.js`.

---

## Example pipelines

### doc-pipeline

Ingests documents → chunks → embeds → indexed output.

```bash
folpipe run ./doc-pipeline --watch
```

Demonstrates: parallel dispatch, sub-steps, agent branching, partial-failure routing.

### cv-pipeline

Job URL → developer profile → tailored CV + styled PDF.

```bash
folpipe run ./cv-pipeline --input "https://example.com/jobs/engineer" --watch
```

Demonstrates: custom tools (`fetch_page`, `render_pdf`), linear pipeline, HTML→PDF via Edge headless.

---

## CLI

```bash
folpipe run ./my-pipeline               # run
folpipe run ./my-pipeline --watch       # run with live output
folpipe run ./my-pipeline --from step-03  # resume after failure
folpipe run ./my-pipeline --dry-run     # validate config without running
folpipe new my-pipeline                 # scaffold new pipeline
folpipe new step step-05-review --in ./my-pipeline
folpipe new tool send_email --in ./my-pipeline/tools
folpipe validate ./my-pipeline          # check config
folpipe tools list --pipeline ./my-pipeline
folpipe tools install ./my-pipeline     # pre-install tool deps
folpipe log ./my-pipeline               # show run log
folpipe log ./my-pipeline --errors      # show last error report
```

---

## Documentation

- [Getting Started](docs/getting-started.md)
- [Pipeline Structure](docs/pipeline-structure.md) — `pipeline.yaml` and `SKILL.md` reference
- [State & Handoffs](docs/state.md)
- [Tools](docs/tools.md) — built-ins, custom tools, resolution order
- [Execution Patterns](docs/execution-patterns.md) — linear, branching, loops, dispatch, sub-steps
- [Context Management](docs/context-management.md)
- [Human Input](docs/human-input.md)
- [CLI Reference](docs/cli.md)
- [Examples](docs/examples.md)

---

## Requirements

- Python 3.10+
- A model with tool calling support (DeepSeek, Claude, GPT-4, Llama 3.1+)
- For PDF rendering in cv-pipeline: Edge or Chrome installed
