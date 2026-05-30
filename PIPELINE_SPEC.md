# Agentic pipeline framework — spec v0.1

A folder-based framework for building agentic AI pipelines. No programming required to use. Code only lives in the runner (installed once) and in tools you drop in.

---

## Core philosophy

- **Pipeline = folder.** Zip it, share it, version it in git. No database, no server, no cloud account.
- **Instructions = markdown.** SKILL.md files are the "code." Plain English.
- **Tools = drop-in.** Drop a folder into `tools/`. Done.
- **Model = swappable.** Change one line in config. Steps never know which model runs them.
- **Failures = natural language.** Error handling lives in SKILL.md, not in runner logic.

---

## Installation

One command, installs globally:

```bash
pip install folpipe
```

After that: `folpipe run ./my-pipeline`. No other setup.

Dependencies declared per-pipeline are installed automatically into a shared local cache (`~/.pipelinex/envs/`). Same dependency across 10 pipelines — installed once, reused everywhere.

---

## Folder structure

```
my-pipeline/
│
├── pipeline.yaml          # pipeline definition — steps, model, routing
├── SKILL.md               # global instructions, applies to all steps
├── .env                   # secrets and environment overrides (never commit this)
│
├── input/                 # drop files here before running
├── output/                # runner writes results here
│   ├── step-01/           # each step gets its own output folder
│   ├── step-02/
│   └── errors/            # failed runs land here with full error report
│
├── tools/                 # pipeline-level tools (available to all steps)
│   ├── _builtin/          # ships with runner, never edit
│   └── my-custom-tool/    # drop-in tool folder
│       ├── tool.json      # MCP-compatible schema
│       ├── run.py         # or run.sh / run.js
│       └── README.md      # optional, for humans
│
├── step-01-ingest/
│   ├── SKILL.md           # instructions for this step
│   └── tools/             # step-local tools (override pipeline-level)
│
├── step-02-process/
│   ├── SKILL.md
│   ├── tools/
│   ├── sub-01-chunk/      # sub-steps: same structure, recursive
│   │   ├── SKILL.md
│   │   └── tools/
│   ├── sub-02-embed/
│   └── sub-03-index/
│
├── step-03-validate/
│   └── SKILL.md
│
└── step-04-output/
    └── SKILL.md
```

### Input

Drop any files the pipeline needs into the `input/` folder before running.
The first step's SKILL.md describes what to expect there and how to use it.

For simple cases, a path or value can also be passed directly at run time:

```bash
folpipe run ./my-pipeline --input report.pdf
folpipe run ./my-pipeline --input "quarterly results for Q3"
```

Both end up available to the first step. The SKILL.md describes which to expect.

### Output

Every step writes its results to `output/step-name/`. Steps refer to previous
steps' output by folder name — "the output from step-01" means `output/step-01/`.

Final pipeline output lives in `output/` directly, written by the terminal step.

### Errors

When a pipeline fails, the runner writes a full error report to `output/errors/`:

```
output/errors/
├── report.md          # what failed, which step, what the model saw
├── state.json         # state at the point of failure
└── last-response.md   # the model's last response before failure
```

This gives everything needed to understand what went wrong and resume or fix it.

### Global tool cache

Tools shared across all pipelines on the machine live in:

```
~/.pipelinex/tools/
```

Drop a tool folder there once — every pipeline can use it.

### Tool resolution order

Most specific wins:

```
step-local tools/       →  step-02/tools/send_slack/
pipeline-level tools/   →  tools/send_slack/
global cache            →  ~/.pipelinex/tools/send_slack/
_builtin                →  tools/_builtin/send_slack/
```

---

## Environment variables and secrets

Sensitive values — API keys, passwords, tokens — live in a `.env` file
next to the pipeline. Never commit this file.

```bash
# my-pipeline/.env
ANTHROPIC_API_KEY=sk-ant-...
SLACK_TOKEN=xoxb-...
DATABASE_URL=postgres://...
```

Reference them in `pipeline.yaml` with `${VAR_NAME}`:

```yaml
model:
  provider: anthropic
  name: claude-sonnet-4-5
  api_key: ${ANTHROPIC_API_KEY}
```

If a referenced variable is missing, the runner stops immediately with a clear
error before executing anything:

```
ERROR: Missing environment variable: ANTHROPIC_API_KEY
       Add it to my-pipeline/.env or export it in your shell.
```

For values that differ between machines (paths, endpoints, non-secret config),
`.env` works for those too — it's not just for secrets, it's for anything
that shouldn't be hardcoded in the pipeline itself.

---

## pipeline.yaml

Full reference:

```yaml
name: my-pipeline
version: 1.0.0

# Model config — change this one line to switch providers
model:
  provider: anthropic           # anthropic | openai | ollama | groq | bedrock | any LiteLLM provider
  name: claude-sonnet-4-5
  api_key: ${ANTHROPIC_API_KEY} # env var reference

  # Optional: manual pricing (used when LiteLLM has no pricing data for the provider)
  pricing:
    input_per_million: 3.00     # cost per million input tokens
    output_per_million: 15.00   # cost per million output tokens
    currency: USD               # any string — shown as-is in the run summary

  # Optional: fallback if primary fails or rate-limits
  fallback:
    provider: openai
    name: gpt-4o

# Dispatch safety limits
dispatch:
  max_parallel: 10        # max concurrent dispatch_task calls per step
  max_depth: 5            # max dispatch-within-dispatch recursion
  timeout_s: 300          # wall-clock ceiling for a parallel batch

# Steps — executed in order unless agent branches
steps:

  - id: step-01-ingest
    # no model override — uses global model

  - id: step-02-process
    model:                      # per-step model override (cost optimization)
      provider: ollama
      name: llama3.1
    max_iterations: 100         # safety ceiling — stop if model loops too long
    context_budget_tokens: 4000 # optional: summarize include-tier state if context exceeds this
    self_reflection: true       # optional: enable self-reflection for this step (overrides global)
    can_goto:
      - step-02-process         # self-reference = model can loop back
      - step-03-validate

  - id: step-03-validate
    can_goto:                   # whitelist — agent can only jump to these
      - step-03-validate        # can jump to self = loop
      - step-03-human-review
      - step-04-output
    # no default next — model must choose

  - id: step-03-human-review
    human_input:                # how to collect human input for this step
      mode: console             # console | file | tool
      prompt: "Review the validation report in output/step-03/ and type your decision:"
    can_goto:
      - step-03-validate
      - step-04-output

  - id: step-04-output
    terminal: true              # pipeline ends here
```

### Human input modes

Steps that need a human decision can collect it three ways:

**Console** — runner pauses and prints a prompt. User types a response.
Good for simple approvals and quick decisions during local runs.

```yaml
human_input:
  mode: console
  prompt: "Approve this output? (yes / no / revise):"
```

**File** — runner writes the question to `output/step-name/waiting.md`
and pauses. Human edits or replaces the file, then signals ready.
Good for decisions that need more context or deliberation.

```yaml
human_input:
  mode: file
  prompt: "Review output/step-03/report.md and write your decision in output/step-03/decision.md"
```

**Tool** — step uses a custom tool to collect input however makes sense
for the pipeline — Slack message, email, form, webhook. The tool handles
the waiting and returns the human's response.

```yaml
human_input:
  mode: tool
  tool: request_slack_approval   # custom tool in tools/
```

The step's SKILL.md describes what to do with the human's response
once it arrives, just like any other input.

### Cancelling a run

Any step can stop the pipeline immediately by calling the `cancel_pipeline` tool:

```
cancel_pipeline(reason="Job requires 5+ years iOS/Swift. Applicant has no mobile experience.")
```

The runner:
1. Writes `output/cancelled.md` — reason, step name, full state snapshot
2. Prints the reason and token/cost summary
3. Exits cleanly (no error, no error report written)

`reason` is required. Use it for genuine early-exit conditions — a mismatch that makes
continuing pointless, a missing required input, a user explicitly declining to proceed.
Don't use it for recoverable errors; those should go through `## When things go wrong`.

Unlike routing to a terminal step, `cancel_pipeline` needs no `can_goto` plumbing and
works from any point in a step, including mid-execution before a routing decision.

### Version and resumption

`version` in `pipeline.yaml` is used when resuming a saved run.
If a saved run's version doesn't match the current pipeline version,
the runner warns before resuming — state structure may have changed
and the run may not be compatible.

---

## SKILL.md

The main file a pipeline author writes. Plain English. Model reads it at the start of each step.

### Structure

```markdown
# Step name

One-paragraph description of what this step does and why.
Who handed off to this step and what the next step expects.

## Context

What the model needs to know going in. What's already been done.
What the input looks like. Any important background.
Signal what's essential, what's useful, what can be ignored —
the runner uses these signals to manage what gets injected.

## Task

What to do — written the way you'd explain it to a smart colleague.
Not a list of operations, but a description of the work.
Mention which tools exist and when they're useful.

## When things go wrong

What to do if something fails. How to decide whether to retry,
skip, or stop. When to handle it silently versus raise the alarm.

## Notes

Edge cases worth knowing. Examples. Anything that's bitten people before.
```

### Global SKILL.md

The SKILL.md at the pipeline root sets the context for the whole pipeline.
It's the right place for things every step needs to know:

- What the pipeline is for and who it serves
- Tone, language, and output style expectations
- Domain knowledge every step shares
- Rules that apply everywhere ("always cite sources", "never guess at numbers")
- Which tools are available globally and when to reach for them

Keep it short. It's injected into every step, so every word costs.
Step-level SKILL.md files handle the specifics.

### Resolution and merging

SKILL.md files stack — child extends parent:

```
global SKILL.md           →  pipeline context, shared rules
  step SKILL.md           →  step-specific task
    sub-step SKILL.md     →  narrowest scope
```

Runner concatenates them in order. When instructions conflict,
the most specific one wins — sub-step overrides step, step overrides global.
Rules not mentioned in a child still apply from the parent.

---

## Writing good SKILL.md files

### Style is your choice

The framework has no opinion on how you write SKILL.md files.
Plain English works. Numbered steps work. Precise technical language works.
Pseudocode works. Whatever communicates the task clearly to the model is correct.

The only thing the framework avoids in its own design is forcing
programmatic thinking on authors. But if that's how you think,
write that way.

**Plain English:**
```markdown
## Task
You have a document that needs to be broken into pieces for embedding.
Split it into manageable chunks — around 500 words each, keeping
paragraphs intact. Then send each chunk for embedding in parallel.
```

**More structured — equally valid:**
```markdown
## Task
1. Read the document text.
2. Split into chunks of ~500 words. Preserve paragraph boundaries.
3. Send all chunks for embedding in parallel using dispatch_task.
4. Save the results and leave a handoff note.
```

Both work. The model handles either. Use whatever feels natural.

### The only real failure mode — vagueness

The one thing that reliably breaks steps is being too vague.
The model can't do good work without knowing what good looks like.

**Too vague:**
```markdown
## Task
Process the input data and produce output.
```

**Clear enough to act on (either style):**
```markdown
## Task
You're embedding text chunks so they can be searched later.
Send all chunks for embedding at once. Quality matters more than
speed — don't cut corners on chunk boundaries.
```

```markdown
## Task
1. Split the document into ~500-word chunks.
2. Embed all chunks in parallel.
3. Write results to the output folder.
```

### When things go wrong — cover the real cases

This section is what the model reads the moment something fails.
Write it for that moment — calm, specific, prioritized.

**Too vague:**
```markdown
## When things go wrong
Handle errors gracefully.
```

**Good:**
```markdown
## When things go wrong

If embedding fails for a chunk: try once more with a shorter version
of the text. If it fails again, skip that chunk and note which one
was skipped in your handoff.

If more than a fifth of chunks fail: don't continue to the output step.
Hand off to the partial-output step instead, explaining what succeeded
and what didn't.

If the embedding tool is completely unavailable: hand off to output
anyway — the output step knows how to handle missing embeddings.
```

### Notes — teach the edge cases

```markdown
## Notes

Paragraphs that start with a heading should stay with the heading —
don't split them apart.

If the document is empty, hand off immediately to the output step.
There's nothing to embed.

Very long documents (book-length) should be split by chapter or section
first, then chunked within each section. Look for the major headings.
```

---

## Execution patterns

### Pattern 1 — linear (default)

Steps run in order. No extra config.

```
step-01 → step-02 → step-03 → step-04
```

### Pattern 2 — model-driven loop

The model loops naturally when the SKILL.md describes iterative work.
No special loop config needed — the model dispatches items, processes
them, and decides when it's done.

```markdown
## Task

You have a list of documents to process. Work through each one —
send it through chunking, embedding, and indexing. You can process
several in parallel. When all are done, move to validation and leave
a handoff summarizing what succeeded and what didn't.
```

Looping is just the model branching back to itself via `can_goto`.
`max_iterations` is a safety ceiling in case something goes wrong —
not a loop controller.

```yaml
- id: step-02-process
  max_iterations: 500     # stop if model loops unexpectedly long
  can_goto:
    - step-02-process     # model can loop back to process more
    - step-03-validate    # or move on when done
```

The model decides when the work is complete. The runner just enforces
the ceiling and the valid transitions.

### Pattern 3 — agent branch

Model decides which step comes next. Runner enforces the whitelist.

Model output must include:
```json
{
  "next": "step-04-output",
  "reason": "validation passed, confidence 0.97"
}
```

Runner validates `next` is in `can_goto`. Rejects anything not on the list.
If model omits `next`, runner retries the step once, then writes an error report.
`reason` is logged — useful for understanding why the pipeline took a path.

### Pattern 4 — dynamic dispatch

Agent discovers work at runtime and spawns ad-hoc tasks.

**Single task:**
```
model calls dispatch_task(task, name, skill)
runner executes, returns result as tool response
model continues
```

**Parallel batch (map-reduce):**
```
model calls dispatch_task × N in a single response
runner detects batch, spawns all concurrently
runner awaits all, returns array of results
model receives all results, merges, continues
```

SKILL.md tells the model to parallelize in plain English:
```markdown
## Task
Process all documents at once — dispatch them all in the same response
rather than one at a time. Give each dispatch a short descriptive name.
You'll get all the results back together.
```

No special syntax. Model fires multiple tool calls. Runner recognizes the batch automatically.

**Naming ad-hoc agents:**

Each inline `skill` dispatch should include a `name` — a short kebab-case label describing
what the agent is doing (e.g. `search-fundamentals`, `embed-doc-3`). The runner uses this
name as the agent's output subdirectory:

```
output/
└── step-02-search/
    ├── search-fundamentals/
    │   └── results.md
    ├── search-recent-news/
    │   └── results.md
    └── search-applications/
        └── results.md
```

If two dispatches in the same step share a name, the second gets a `-1` suffix, the third
`-2`, and so on. If no `name` is provided, the runner slugifies the first 40 characters of
`task` as a fallback.

Ad-hoc agents have full access to built-in and custom tools. `write_file` paths resolve
into their own subdirectory — agents write there without knowing their full output path.

Dispatched tasks inherit the step's model. If no step model is set, they use the global model.

**Failure in a parallel batch:**

Runner packages every failure alongside successes and returns the whole
picture to the model. The model reads its "When things go wrong" section
and decides what to do. The runner doesn't decide — it just reports.

### Pattern 5 — early cancellation

Model determines that continuing is pointless and stops the run with a reason.

```
model calls cancel_pipeline(reason="...")
runner writes output/cancelled.md
runner exits cleanly
```

Use this when continuing would produce meaningless output — a severe input mismatch,
a missing required resource, or an explicit user decision not to proceed.

```markdown
## Task

1. Score the applicant against the job's must-have requirements.
2. If fewer than 40% of must-haves are covered, call cancel_pipeline
   with a clear summary of what's missing and why tailoring would be futile.
3. Otherwise proceed with tailoring.
```

`cancel_pipeline` requires no `can_goto` and works from any step at any point.
The reason is written to `output/cancelled.md` alongside a state snapshot.

---

## State

`state.json` is the pipeline's shared memory. Created by the runner, passed to every step.

The runner injects relevant parts into the model's context at the start of each step.
The model reads it, does its work, and uses the `write_state` tool to save what the
next step needs. Think of it as a shared desk — not a database, not a log.
Just the current working surface.

### Writing to state

The model uses the built-in `write_state` tool:

```
I'll save the results now.
[calls write_state with: key "summary", value "47 documents processed..."]
[calls write_state with: key "failed", value ["doc-12", "doc-31"]]
```

The model writes naturally as part of its response — no special formatting required.
The runner reads these tool calls and updates `state.json` automatically.
Multiple writes in one step are merged. Earlier keys are preserved unless overwritten.

### The handoff note

Every step leaves a handoff note before finishing — one or two sentences
saying what was done and what matters right now. The next step reads this first.
It's the sticky note on the desk.

```
"Processed 47 documents. 45 embedded successfully, 2 failed (see the
failed list). The output is ready for validation."
```

The runner injects this note at the top of every step's context automatically.
Models get orientation without reading everything that came before.

In SKILL.md, simply ask for it:

```markdown
## Task
...do the work...

Before finishing, leave a brief note explaining what you did and
what the next step should know.
```

---

## Keeping context healthy

The model works better with less, better-organized information. Think of context
like a desk — a tidy desk helps you think. A buried desk slows you down.

Context fills up in long pipelines. The framework manages this automatically,
but it needs to know what matters to each step. The author tells it — in plain
English, in the Context section of SKILL.md.

---

### Telling the runner what matters

Every step's Context section signals three tiers of importance.
The runner reads these signals and manages what gets injected automatically.

**Essential — always injected in full, never compacted:**
```markdown
## Context

The original contract text is essential — read it in full.
```

Phrases like "essential", "in full", "read the whole thing", "don't summarize this"
tell the runner this content must arrive complete. If it won't fit, the runner
stops and surfaces a clear error rather than silently truncating something critical.

**Important — injected in full if space allows, summarized if tight:**
```markdown
## Context

The metadata and tags from the previous step are important,
but a summary is fine if space is tight.
```

Phrases like "important", "useful to have", "summary is fine", "the gist is enough"
tell the runner this content is valuable but compressible. When context is tight,
the runner summarizes it automatically before injection.

**Not needed — stripped entirely:**
```markdown
## Context

You don't need the raw ingestion logs or the intermediate chunk data.
```

Phrases like "don't need", "ignore", "not relevant here", "skip" tell the runner
to leave this out completely. It stays in state on disk — just never injected.

**All three together:**
```markdown
## Context

The document metadata from step-01 is essential — read it in full.
The previous step's validation notes are important; a summary is fine.
You don't need the raw API response or the chunk index.
```

Runner injects metadata complete, summarizes validation notes if tight,
strips everything else. Model gets exactly what it needs.

---

### Two ways to bring content in

Both patterns work. Both support the same three tiers. Use whichever fits
the nature of the content.

**Pattern A — from state**

For small, structured content that travels naturally between steps.
Summaries, decisions, counts, short results. The runner injects it directly.

```markdown
## Context

The summary of what was ingested is in state from the previous step — essential.
The list of failed documents is important; a brief version is fine.
You don't need the raw configuration values.
```

Runner reads state, applies the tiers, injects the right slice.
Model never sees a bloated state dump — just the curated view.

**Pattern B — from files**

For large, raw, or partially-read content. The file stays on disk.
The model requests what it needs via tool — nothing more is ever loaded.

```markdown
## Context

The full transcript is saved in the output folder from step-01.
Don't load it all — search for sections relevant to the current topic,
then read those sections in full. You don't need anything from state.
```

The tool call is the context boundary. Model requests a slice, gets a slice.
A 200k-token transcript never enters context if the model only asks for three paragraphs.

**Combining both:**
```markdown
## Context

The document metadata and previous handoff are in state — both essential.
The full document text is in the output folder from step-01. Don't load
it all — search for the sections relevant to this validation task.
You don't need the embedding data or the chunk index.
```

Runner injects the state slice. File stays on disk until the model calls the tool.
Model works with exactly what it needs from each source.

---

### When content is too big to summarize

Sometimes a step's job is compression itself — reading a large file and
producing something smaller that downstream steps can work from.

```markdown
## Task

Read the full report from the output folder. Your job is to produce
a short briefing that the next step can work from without reading
the original. Be opinionated — pull out what matters for a go/no-go
decision, leave everything else behind.
```

The output of this step is the summary. Future steps get the summary,
never the original. One step pays the cost of reading the full content;
every downstream step is free.

---

### Loops start fresh by default

When a step loops back to itself, each pass starts clean — current state
and the handoff note from the previous pass. Full conversation history
is not carried forward.

Design step instructions that work on one pass at a time:

**Good:**
```markdown
## Task
Work through the next batch of documents. When done with this batch,
leave a note summarizing what was processed and what's still remaining.
Move to validation when everything is done.
```

**Avoid:**
```markdown
## Task
Review everything you've done across all previous passes, then continue.
```

If a step genuinely needs continuity across passes, say so in the SKILL.md:

```markdown
## Context

Read the handoff from the previous pass — it contains the running
summary you'll need to continue from where you left off.
```

The model carries what it wrote in the handoff. Everything else starts fresh.

---

### Under the hood

The runner measures context size before every LLM call. If everything fits,
it injects content as declared. If it's tight, it works through the tiers:

1. Strip anything marked unneeded or not mentioned
2. Summarize "important but summary is fine" content
3. Compress further if still tight
4. Stop and surface a clear error if essential content won't fit

Summarization uses a fast, cheap model call — invisible to the pipeline author.
The compaction step never touches essential content and never silently drops
anything the step declared it needs.

When a step loops back to itself, each pass gets a fresh context. The runner carries
only the handoff note from the previous pass, not the full conversation history.

None of this requires any configuration beyond what the author already writes
in the Context section. The plain-English tiers are both the human briefing
and the runner's instructions.

---

## Tools

### Built-in tools (ship with runner)

| Tool | Does |
|---|---|
| `read_file` | Read a file — sandboxed to the pipeline directory |
| `write_file` | Write or append to a file |
| `write_state` | Save a value to pipeline state |
| `web_search` | Search the web |
| `http_request` | Any HTTP call (GET, POST, etc.) |
| `run_script` | Execute a shell command — working dir must be inside pipeline directory |
| `extract_json` | Parse and query JSON |
| `template` | Fill a template with current values |
| `dispatch_task` | Spawn an ad-hoc sub-task; `name` sets its output subdirectory |
| `cancel_pipeline` | Stop the run immediately with a mandatory reason |
| `ask_human` | Pause and collect a human response (console mode) |

### Self-reflection tools (available only during self-reflection)

| Tool | Does |
|---|---|
| `get_run_usage` | Return token and cost totals accumulated so far in this run |

`get_run_usage` is only available to the self-reflection LLM call, not during normal step execution. The model calls it on demand — it is never injected automatically. Use it by instructing the model in a `## Self-Reflection` section of SKILL.md:

```markdown
## Self-Reflection

Review what happened. Call get_run_usage to check token efficiency.
If total_tokens exceeded 3000, rewrite this SKILL.md with a note in the
instructions suggesting a tighter context approach for next time.
```

Return value:
```json
{
  "prompt_tokens": 1500,
  "completion_tokens": 300,
  "total_tokens": 1800,
  "cost": 0.023400,
  "currency": "USD"
}
```

Note: the counts are cumulative for the entire run up to that point, not just this step.

### Dropping in a custom tool

Create a folder anywhere in the tool resolution path:

```
tools/
└── send_slack/
    ├── tool.json
    ├── run.py
    └── README.md     (optional)
```

**`tool.json`** — MCP-compatible schema:

```json
{
  "name": "send_slack",
  "description": "Post a message to a Slack channel. Use when the pipeline needs to notify a human — for approvals, failures worth flagging, or results that need a decision. Not for routine logging; use write_file for that.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "channel": {
        "type": "string",
        "description": "Slack channel name, e.g. #alerts"
      },
      "message": {
        "type": "string",
        "description": "Message text. Markdown supported."
      }
    },
    "required": ["channel", "message"]
  },
  "run": "run.py",
  "deps": ["slack-sdk"]
}
```

Runner reads `deps`, installs them to the shared cache before first run.
User never runs pip manually.

**`run.py`** — receives args as JSON on stdin, writes result as JSON to stdout,
exits non-zero on failure:

```python
import sys, json, os
from slack_sdk import WebClient

args = json.load(sys.stdin)
client = WebClient(token=os.environ["SLACK_TOKEN"])
client.chat_postMessage(channel=args["channel"], text=args["message"])
print(json.dumps({"ok": True}))
```

**Tool failure contract:** exit non-zero to signal failure. Always write JSON
to stdout — on failure, include an `error` field explaining what went wrong.
Anything written to stderr goes to the run log.

```python
# on failure:
print(json.dumps({"error": "Slack API returned 403 — check SLACK_TOKEN"}))
sys.exit(1)
```

Any language works — runner detects `run.py`, `run.sh`, or `run.js` and executes appropriately.

### Writing good tool descriptions

The description in `tool.json` is what the model reads to decide whether to use the tool.
Write it for the model — when to use it, and equally important, when not to.

**Too vague:**
```json
"description": "Sends a Slack message."
```

**Good:**
```json
"description": "Post a message to a Slack channel. Use when the pipeline needs a human in the loop — approvals, important failures, or results requiring a decision. Not for routine logging; use write_file for that."
```

---

## Filesystem sandbox

Every step runs inside a filesystem sandbox. The model can only read files that are
within the pipeline directory. Reads outside that boundary are denied at the tool level
with a clear error — the model sees the denial and can adapt without any runner crash.

### What is blocked

- **Any path outside the pipeline directory** — absolute or relative, regardless of
  how the model constructs it. `../../etc/passwd`, `C:\Users\...\secrets`, all denied.
- **Secret-named files** — `.env`, `*.env`, `.env.*`, `secrets.*`, `*.key`, `*.pem`,
  `*.p12`, `*.pfx`, `*.crt`. Blocked even if they live inside the pipeline directory.
  The model never sees API keys or credentials, even if it tries.
- **`run_script` with a working directory outside the pipeline** — the command itself
  is not restricted, but it always starts from inside the pipeline boundary.

### What is allowed

- **Everything inside the pipeline directory** — `input/`, `output/`, step folders,
  `SKILL.md` files, `pipeline.yaml`, any file the author put there.
- **Symlinks inside the pipeline directory** — a symlink placed inside the pipeline
  acts as a user-granted shortcut to whatever it points to, including external paths.
  This is the intended mechanism for giving a step access to data that lives elsewhere:
  drop a symlink into `input/` and the model can read through it.

```
input/
└── dataset -> /mnt/shared/datasets/q3-2026/   ← model can read through this
```

No configuration needed. The symlink itself is the access grant.

### Runtime environment block

Before each step's first LLM call, the runner injects a `## Runtime Environment`
section into the system prompt:

```
## Runtime Environment

- Pipeline root: `/path/to/my-pipeline`
- Your output folder: `output/step-02-process/`
- Shared state: `output/state.json`
- Input folder: `input/`
```

This gives the model the concrete paths it needs upfront, eliminating the need to
search for files via `run_script` or guess OS-specific conventions.

---

## Logging and debugging

The runner writes a log to `output/run.log` for every execution. It captures:

- Step transitions — when each step started and finished
- Tool calls — what was called, with what inputs, and what came back
- Model responses — the full response from each LLM call
- Context snapshots — what was injected before each call
- Errors — full detail including the state at the moment of failure
- Cost summary — token counts and cost at pipeline completion

`--watch` during a run shows a live view of step transitions and tool calls
in flight. Think of it as a progress display — not the full log, but enough
to see what the pipeline is doing right now.

For deeper debugging after a failed run, `output/errors/` has everything:
the error report, the state at failure, and the model's last response.
Together with `output/run.log`, these give a complete picture of what happened.

### Cost tracking

At the end of every run the runner prints a cost summary and writes it to `output/cost_summary.json`:

```
Pipeline complete.  Tokens: 73,962 (66,235 in / 7,727 out)  Cost: 0.026383 USD
```

```json
{
  "prompt_tokens": 66235,
  "completion_tokens": 7727,
  "total_tokens": 73962,
  "cost": 0.026383,
  "currency": "USD"
}
```

Cost is calculated by LiteLLM when the provider is in its pricing database.
For providers it doesn't know, add a `pricing` block to the model config in `pipeline.yaml`:

```yaml
model:
  provider: deepseek
  name: deepseek-chat
  api_key: ${DEEPSEEK_API_KEY}
  pricing:
    input_per_million: 0.27
    output_per_million: 1.10
    currency: USD
```

View the cost from the last run at any time:

```bash
folpipe log ./my-pipeline --cost
```

---

## Provider configuration

### Supported providers (via LiteLLM)

Any provider LiteLLM supports. Common ones:

```yaml
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

# Ollama (local, no key needed)
model:
  provider: ollama
  name: llama3.1

# Groq
model:
  provider: groq
  name: llama-3.1-70b-versatile
  api_key: ${GROQ_API_KEY}

# Any OpenAI-compatible endpoint
model:
  provider: openai
  name: my-model
  base_url: https://my-endpoint.com/v1
  api_key: ${MY_KEY}
```

### Hard requirement

Runner checks tool-calling support at startup:

```
ERROR: model "llama2" does not support tool calling.
       Tool calling is required. Use llama3.1 or later.
```

Hard stop. Clear message. No partial execution.

### Per-step override

```yaml
steps:
  - id: step-01-ingest
    # uses global model

  - id: step-02-process
    model:
      provider: ollama
      name: llama3.1     # cheap local model for heavy batch work

  - id: step-03-validate
    model:
      provider: anthropic
      name: claude-opus-4  # stronger model only where it matters
```

---

## CLI reference

```bash
# Run a pipeline
folpipe run ./my-pipeline

# Pass input directly (available to step-01)
folpipe run ./my-pipeline --input "quarterly report Q3"
folpipe run ./my-pipeline --input report.pdf

# Resume from a specific step (after a failure)
folpipe run ./my-pipeline --from step-03-validate

# Dry run — validate config, check tool deps, check env vars, don't execute
folpipe run ./my-pipeline --dry-run

# Watch step transitions and tool calls live during execution
folpipe run ./my-pipeline --watch

# Run with a different model (override pipeline.yaml)
folpipe run ./my-pipeline --model ollama/llama3.1

# Scaffold a new pipeline
folpipe new my-pipeline

# Scaffold a new step
folpipe new step step-05-review --in ./my-pipeline

# Scaffold a new tool
folpipe new tool send_email --in ./my-pipeline/tools

# Validate pipeline config without running
folpipe validate ./my-pipeline

# List available built-in tools
folpipe tools list

# Install tool deps without running
folpipe tools install ./my-pipeline

# Show the run log for the last execution
folpipe log ./my-pipeline

# Show the error report from the last failed run
folpipe log ./my-pipeline --errors

# Show token and cost summary from the last run
folpipe log ./my-pipeline --cost
```

---

## Example: document processing pipeline

```
doc-pipeline/
├── pipeline.yaml
├── SKILL.md
├── .env
├── input/
├── output/
├── tools/
│   └── send_slack/
├── step-01-ingest/
│   └── SKILL.md
├── step-02-process/
│   ├── SKILL.md
│   ├── sub-01-chunk/
│   ├── sub-02-embed/
│   └── sub-03-index/
├── step-03-validate/
│   └── SKILL.md
├── step-04-output/
│   └── SKILL.md
└── step-05-partial-output/
    └── SKILL.md
```

**`pipeline.yaml`:**
```yaml
name: doc-pipeline
version: 1.0.0

model:
  provider: anthropic
  name: claude-sonnet-4-5
  api_key: ${ANTHROPIC_API_KEY}
  fallback:
    provider: openai
    name: gpt-4o

dispatch:
  max_parallel: 10
  max_depth: 3
  timeout_s: 300

steps:
  - id: step-01-ingest

  - id: step-02-process
    max_iterations: 500
    can_goto:
      - step-02-process
      - step-03-validate
      - step-05-partial-output

  - id: step-03-validate
    can_goto: [step-04-output, step-05-partial-output]

  - id: step-04-output
    terminal: true

  - id: step-05-partial-output
    terminal: true
```

**`SKILL.md` (global):**
```markdown
# Document processing pipeline

This pipeline ingests a set of documents, breaks them into searchable
chunks, embeds them, and produces an indexed output ready for search.

All output should be precise and well-structured. When in doubt about
a document's content, note the uncertainty rather than guessing.

The `send_slack` tool is available for notifying the team when something
needs attention — use it for failures that need human eyes, not for
routine progress updates.
```

**`step-01-ingest/SKILL.md`:**
```markdown
# Ingest documents

Read the documents from the input folder and prepare them for processing.
The next step will work through each document one at a time.

## Context

The input folder contains the files to process. There may be PDFs,
Word documents, plain text files, or a mix. Start fresh — there's
nothing in state yet.

## Task

Look at what's in the input folder. For each file, read it and pull
out the text content. Note the filename, the type, and any metadata
you can find (title, author, date if present).

Collect all the documents into a list, ready to be handed off.
If any file can't be read, note it and move on — don't let one
bad file block the rest.

## When things go wrong

If the input folder is empty, stop and leave a clear note explaining
that no input was found. Don't proceed to the next step.

If a file type is unreadable, note the filename and skip it.
If more than half the files are unreadable, stop and flag it
for human attention before continuing.

## Notes

Preserve the original filename — it's useful for attribution later.
Don't try to interpret or summarize the content yet. Just extract
the text cleanly and pass it on.
```

**`step-02-process/SKILL.md`:**
```markdown
# Process documents

Break each document into chunks and get them embedded and indexed.
The previous step collected the documents; the next step will validate
the results.

## Context

You're working on one document at a time from the list prepared in
step-01. The document has a filename, body text, and whatever metadata
was found. This is essential — read it in full.

You don't need the list of other documents or anything about failed
ingestions.

## Task

Break the document into pieces — chunks of around 500 words,
keeping paragraphs together. Then send all the chunks for embedding
at once rather than one at a time. Once you have the embeddings,
pass them along to be indexed.

The chunking, embedding, and indexing tools handle the technical
details. Your job is to coordinate them and make sure the pieces
flow through cleanly.

Before finishing, leave a note saying how many chunks were created
and whether indexing succeeded.

## When things go wrong

If embedding fails for a chunk, try once more with a shorter version.
If it fails again, skip that chunk — a few missing chunks are fine.

If more than a third of chunks fail, something is wrong with this
document or the embedding service. Stop processing it, note what
happened, and let the pipeline continue with other documents.

If the indexing step fails entirely, mark this document as partially
processed and move on. Don't let one bad document block the whole batch.

## Notes

Keep paragraphs with any heading that introduces them — don't split
at a heading boundary.

Attach the document's filename and metadata to each chunk before
embedding. It'll be needed later for search results.
```

---

## Self-reflection

A step can review its own execution after it finishes and append lessons to its SKILL.md.
This lets the pipeline improve its own instructions over time without any external tooling.

Enable it globally or per-step, choosing one of two modes:

```yaml
# pipeline.yaml
self_reflection: update      # rewrite SKILL.md in place with improved version (default when true)
self_reflection: report      # write proposed new SKILL.md to output/<step>/reflection.md only

steps:
  - id: step-02-process
    self_reflection: false   # disable for this step only
  - id: step-03-validate
    self_reflection: report  # per-step override
```

`true` is equivalent to `update`.

When enabled, after the step completes the runner makes an additional LLM call with:
- The step's SKILL.md as the system prompt
- The full step conversation as context
- A prompt asking the model to produce an improved version of the SKILL.md

**`update` mode**: the full rewritten SKILL.md replaces the original. `output/<step>/reflection.md` is also written as a record.
**`report` mode**: the improved version is written to `output/<step>/reflection.md` only; the original SKILL.md is untouched.

If the model finds nothing to improve, it outputs `NO_CHANGES` and no files are written.

### Writing self-reflection instructions

Add a `## Self-Reflection` section to the step's SKILL.md:

```markdown
## Self-Reflection

Review what happened. If the approach was inefficient or any instructions were
unclear, produce an improved version of this SKILL.md that fixes them.
```

The runner calls the model with the full step conversation and asks it to output
either the **complete improved SKILL.md** or the exact token `NO_CHANGES`.

The model rewrites the whole file — not a fragment or a diff. Instructions in the
`## Self-Reflection` section tell it what to focus on: cost, correctness, clarity,
missing edge-case handling, or anything else.

If the model outputs `NO_CHANGES` (or anything that doesn't look like a valid SKILL.md),
no files are touched and the step finishes silently.

### Step diagnostics

The runner automatically passes a diagnostics summary to every self-reflection call.
The model sees this before deciding whether to update the SKILL.md:

```
## Step Diagnostics

- LLM calls: 8
- Tools used: http_request ×3, run_script ×4, write_file ×1
- Tool errors (2):
  - read_file: "Access denied: '.env' is a protected file"
  - run_script: "Command 'ping -n 50 127.0.0.1' timed out after 30 seconds"

Pay attention to these observations when deciding whether to update the SKILL.md.
If the model used wrong tools, guessed paths, or looped unnecessarily, fix the instructions.
```

No configuration required. The diagnostics are always included when self-reflection is enabled.
If the run was clean (no errors, sensible tool usage), the model receives that signal too
and can correctly return `NO_CHANGES` without inventing improvements.

This is the primary mechanism for the pipeline to self-correct after sandbox denials,
tool misuse, or unnecessary looping — the reflection model sees the evidence and rewrites
the SKILL.md to prevent the same pattern next run.

### Accessing run usage during reflection

The `get_run_usage` tool is available exclusively during self-reflection.
Use it when the SKILL.md instructs the model to check cost or token efficiency:

```markdown
## Self-Reflection

Call get_run_usage. If total_tokens exceeded 5000, rewrite this SKILL.md
with a tighter context budget hint or a cheaper model suggestion added
to the instructions.
```

The tool returns cumulative totals for the entire run up to that point — not just this step.
The model calls it on demand; it is never injected automatically.

### Output

**`update` mode** (`self_reflection: true` or `self_reflection: update`):
- SKILL.md is replaced with the improved version
- `output/<step>/reflection.md` is written as a record of what changed

**`report` mode** (`self_reflection: report`):
- Original SKILL.md is untouched
- `output/<step>/reflection.md` contains the proposed new version for review

If the model returns `NO_CHANGES`, or its output doesn't begin with a markdown heading
(e.g. it responds with prose), nothing is written.

---

## Design decisions log

Recorded here so future contributors understand why things are the way they are.

**Why folder-per-step?**
Portability. A pipeline is a directory you can zip and share. No database dependencies, no cloud state. Git-native.

**Why input/ and output/ folders instead of only CLI args?**
CLI args are programmatic — you need a terminal and knowledge of the interface.
Dropping files into a folder works for anyone. Both are supported; the folder
convention is the primary mental model.

**Why `write_state` tool instead of parsing model output for JSON?**
Parsing model output for structured data is fragile — models add prose,
formatting varies, and silent failures are hard to debug. A tool call is
explicit, structured, and logged. The model writes to state the same way
it does anything else — by calling a tool.

**Why `.env` next to the pipeline?**
Keeps secrets with the thing that uses them. Easy to find, easy to exclude
from version control, follows convention that most developers already know.
A missing variable fails loudly at startup — never mid-run.

**Why model-driven loops instead of declarative loop config?**
A declarative loop splits the concept across two files — config in pipeline.yaml,
instructions in SKILL.md — and requires the runner to know what the model is
iterating. The model already knows. It reads the SKILL.md, sees a list of work,
and dispatches it. Looping is just self-branching via `can_goto`. No new concept,
no second place to maintain, no magic name matching.

**Why agent-decides routing instead of YAML conditionals?**
YAML conditionals are code in disguise. The model is better at reading
English conditions than YAML authors are at writing them. Keeps the
no-programming constraint intact.

**Why natural language error handling?**
Error modes are infinite. Enums cover three cases. English covers all cases.
The model is the error handler — the runner just packages failures and hands them back.

**Why `can_goto` whitelist?**
Unconstrained routing lets the model hallucinate step names. The whitelist
gives authors control over valid transitions without writing logic. Model
decides which valid transition to take — runner just enforces the boundaries.

**Why parallel dispatch via multiple tool calls?**
Both Anthropic and OpenAI APIs support multiple tool calls in a single model
response natively. No special syntax needed — model fires multiple `dispatch_task`
calls, runner detects the batch. Users express parallelism in plain English in SKILL.md.
Zero framework complexity.

**Why natural language context management instead of token budgets?**
Token budgets are invisible to non-technical users and break the no-programming
constraint. The model already knows how to summarize and compress — it just needs
to be told to. The handoff note convention and tiered Context section solve most
context problems without any framework machinery.

**Why tool calling as the hard requirement?**
It's the only structural requirement. Without it, the runner can't execute tools
or receive structured routing decisions. Every serious model supports it.
Not a meaningful constraint in 2025.

**Why non-zero exit = tool failure?**
Unix convention. Every language and shell script already knows it. Consistent,
debuggable, and keeps the tool contract simple enough to explain in one sentence.

**Why lexical (pre-symlink) path check for the sandbox?**
Resolving symlinks before checking containment would make symlinks useless as
shortcuts — a link inside the pipeline pointing outside would be denied. The author
placing a symlink inside the pipeline is an explicit access grant; the check honours
that intent. Secret-named files (`.env`, `*.key`, etc.) are still blocked by filename
regardless of where they physically live, so the shortcut mechanism cannot be used
to expose credentials.

**Why inject runtime environment into every step's system prompt?**
Without knowing where files live, models guess — often using Linux paths on Windows,
triggering filesystem reconnaissance via `run_script`. Injecting the concrete paths
upfront eliminates the need to search and removes the primary trigger for sandbox
escape attempts. The information is cheap to inject and prevents a class of failure
entirely.

**Why pass diagnostics to self-reflection instead of just the conversation?**
The conversation shows what happened but not how unusual it was. A model that called
`run_script` five times to find a file might not flag that as a problem from the
conversation alone — it succeeded eventually. The diagnostics make the pattern visible:
five `run_script` calls, three timeouts, one sandbox denial. The reflection model can
then update the SKILL.md to route the next run differently, without the author having
to read the log themselves.
