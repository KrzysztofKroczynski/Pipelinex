# Pipeline Structure

## Folder layout

```
my-pipeline/
│
├── pipeline.yaml          # steps, model, routing
├── SKILL.md               # global instructions — every step sees this
├── .env                   # secrets and config (never commit)
│
├── input/                 # drop files here before running
├── output/                # runner writes results here
│   ├── step-01/
│   ├── step-02/
│   └── errors/            # failed runs land here
│
├── tools/                 # pipeline-level custom tools
│   └── my-tool/
│       ├── tool.json
│       └── run.py
│
├── step-01-ingest/
│   ├── SKILL.md
│   └── tools/             # step-local tools (override pipeline-level)
│
└── step-02-process/
    ├── SKILL.md
    ├── tools/
    └── sub-01-chunk/      # sub-steps (optional)
        └── SKILL.md
```

---

## pipeline.yaml

Full reference:

```yaml
name: my-pipeline
version: 1.0.0

# Model — change one line to switch providers
model:
  provider: deepseek          # deepseek | anthropic | openai | ollama | groq | bedrock
  name: deepseek-chat
  api_key: ${DEEPSEEK_API_KEY}

  # Optional fallback if primary fails or rate-limits
  fallback:
    provider: deepseek
    name: deepseek-reasoner
    api_key: ${DEEPSEEK_API_KEY}

# Parallel dispatch limits
dispatch:
  max_parallel: 10        # max concurrent dispatch_task calls
  max_depth: 5            # max dispatch-within-dispatch nesting
  timeout_s: 300          # wall-clock ceiling for a parallel batch

steps:
  - id: step-01-ingest
    # uses global model

  - id: step-02-process
    model:                # per-step override
      provider: ollama
      name: llama3.1
    max_iterations: 500   # safety ceiling — stop if model loops too long
    can_goto:
      - step-02-process   # self-reference = model can loop
      - step-03-validate

  - id: step-03-validate
    can_goto:
      - step-04-output
      - step-05-partial-output

  - id: step-04-output
    terminal: true        # pipeline ends here
```

### Model

Any provider LiteLLM supports. Common examples:

```yaml
# DeepSeek
model:
  provider: deepseek
  name: deepseek-chat
  api_key: ${DEEPSEEK_API_KEY}

# Anthropic
model:
  provider: anthropic
  name: claude-sonnet-4-5
  api_key: ${ANTHROPIC_API_KEY}

# OpenAI
model:
  provider: openai
  name: gpt-4o
  api_key: ${OPENAI_API_KEY}

# Ollama (local, no key)
model:
  provider: ollama
  name: llama3.1

# Any OpenAI-compatible endpoint
model:
  provider: openai
  name: my-model
  base_url: https://my-endpoint.com/v1
  api_key: ${MY_KEY}
```

The runner checks that the model supports tool calling at startup. Hard stop with a clear error if it doesn't.

### Steps

| Field | Required | Description |
|---|---|---|
| `id` | yes | Folder name of the step |
| `model` | no | Override global model for this step |
| `max_iterations` | no | Safety ceiling (default 200) |
| `can_goto` | no | Whitelist of step IDs the model may route to |
| `terminal` | no | Pipeline ends when this step completes |
| `human_input` | no | Pause for human input before running this step |

### can_goto

When a step has `can_goto`, the model must include a routing JSON block in its final response:

```json
{"next": "step-03-validate", "reason": "all documents processed"}
```

The runner validates `next` is in the whitelist. If the model omits it, the runner retries once then fails with an error report.

### dispatch

Controls parallel `dispatch_task` execution:

| Field | Default | Description |
|---|---|---|
| `max_parallel` | 10 | Max concurrent tasks in a parallel batch |
| `max_depth` | 5 | Max dispatch-within-dispatch nesting |
| `timeout_s` | 300 | Wall-clock seconds before timed-out tasks return an error |

---

## SKILL.md

The instruction file a pipeline author writes. Read by the model at the start of each step.

### Structure

```markdown
# Step name

One paragraph describing what this step does and why.

## Context

What the model needs to know going in. Signal what matters:
- "X is essential" → always injected in full
- "Y is important" → injected, model prioritises it  
- "you don't need Z" → excluded from context injection

## Task

What to do — written for a smart colleague.
Mention which tools to use and when.

## When things go wrong

What to do if something fails. When to retry, skip, or stop.

## Notes

Edge cases. Examples. Anything that's bitten people before.
```

### Global SKILL.md

The `SKILL.md` at the pipeline root is prepended to every step's SKILL.md. Use it for:
- What the pipeline is for
- Tone, style, output format expectations
- Domain knowledge every step shares
- Global rules ("always cite sources", "never guess numbers")
- Which tools are available across all steps

Keep it short — it's injected into every step.

### SKILL.md stacking

Files concatenate in order, most specific wins on conflict:

```
global SKILL.md     → pipeline context, shared rules
  step SKILL.md     → step-specific task
    sub-step SKILL.md → narrowest scope
```

### Context section and injection tiers

The model reads the `## Context` section and classifies each state key as `essential`, `include`, or `skip`. Keys marked skip are never injected. Keys marked essential are tagged `[ESSENTIAL]` in the context prompt.

```markdown
## Context

The original contract text is essential — read it in full.
The metadata from the previous step is important.
You don't need the raw API response or the chunk index.
```

Use plain English. The model understands any natural phrasing of these signals.

---

## Environment variables

Secrets and config live in `.env` next to the pipeline. Never commit this file.

```bash
# my-pipeline/.env
DEEPSEEK_API_KEY=sk-...
SLACK_TOKEN=xoxb-...
```

Reference them in `pipeline.yaml` with `${VAR_NAME}`. If a variable is missing, the runner stops immediately before executing anything with a clear error.

Values that differ between machines (endpoints, paths, non-secret config) also go here.
