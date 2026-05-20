# Context Management

## What gets injected

At the start of each step, the runner builds a context prompt from:

1. **Handoff note** — the one or two sentences the previous step left
2. **Pipeline state** — keys from `state.json`, filtered by relevance

This is prepended to the merged SKILL.md and passed as the system prompt.

---

## Telling the runner what matters

The `## Context` section of a step's SKILL.md is both the human briefing and the runner's instructions. The model reads it and classifies each state key as `essential`, `include`, or `skip`.

```markdown
## Context

The "documents" list from step-01 is essential — read it in full.
The validation notes from step-02 are important; a summary is fine.
You don't need the raw API response or the chunk index.
```

Any natural phrasing works. The model understands signals like:
- "essential", "in full", "read the whole thing", "critical", "must have"
- "important", "useful", "summary is fine", "the gist is enough"
- "don't need", "ignore", "not relevant", "skip", "leave out"

---

## How classification works

Before injecting state, the runner makes a single LLM call:

```
Given this context guidance:
  [context section text]

State keys available: [key1, key2, key3, ...]

Classify each as 'essential', 'include', or 'skip'.
```

Keys classified `skip` are excluded from the context prompt entirely. Keys classified `essential` are tagged `[ESSENTIAL]` for visibility. Everything else is injected normally.

If the step has no `## Context` section, or state is empty, the classification call is skipped and all keys are included.

---

## Two ways to bring content in

### From state (small, structured data)

Good for summaries, decisions, counts, short results that travel naturally between steps.

```markdown
## Context

The summary of ingested documents is in state — essential.
The list of failed files is in state — include it.
You don't need the raw configuration values.
```

The runner injects the filtered slice automatically.

### From files (large or raw content)

Good for full documents, transcripts, or anything too large for state. The file stays on disk; the model fetches what it needs via `read_file`.

```markdown
## Context

The full transcript is saved in output/step-01/. Don't load it all —
search for sections relevant to the current validation task, then read
those sections in full. You don't need anything from state.
```

The model calls `read_file` only for the sections it needs. A 200k-token document never enters context if the model only asks for three paragraphs.

### Combining both

```markdown
## Context

The document metadata and previous handoff are in state — both essential.
The full document text is in output/step-01/. Don't load it all —
search for the sections relevant to this step.
```

---

## Handoff notes

The handoff note from the previous step is always injected at the top of context, before any state. It orients the model without requiring it to read everything that came before.

Every step should write one:

```
write_state(key="handoff", value="Processed 47 documents. 45 indexed, 2 failed (doc-12, doc-31). Output ready for validation.")
```

One or two sentences. What was done. What matters right now.

---

## Loop iterations

When a step loops back to itself, each pass starts fresh — new messages, current state, previous handoff note. The model doesn't carry the full conversation history from prior passes.

Design loop step SKILL.md to work on one pass at a time:

```markdown
## Task

Work through the next batch of documents. When done with this batch,
leave a note summarising what was processed and what's still remaining.
Move to validation when everything is done.
```

The model carries what it wrote in the handoff. State accumulates across passes (this is how progress is tracked).

---

## Good practice: writing effective context sections

### Name keys explicitly and pair them with a signal word

The classifier is a model reading plain English. Name the key in quotes, then state its tier and why. Vague guidance produces inconsistent classification — especially when state has many keys.

**Weak — model guesses what matters:**

```markdown
## Context

Use whatever is relevant from the previous steps.
```

**Strong — model knows exactly what to load:**

```markdown
## Context

"documents" is essential — you'll process every entry in that list.
"config" is essential — it sets the chunk size and target language.
"raw_api_responses" and "debug_log" are not needed, skip them.
```

---

### Signal vocabulary

The tier system maps to natural English. Pick the phrase that fits — any of these work:

| Tier | Signals that work well |
|---|---|
| **essential** | essential, critical, must have, read in full, read every word, you need the full value, do not summarise |
| **include** | useful, important, include it, worth having, summary is fine, the gist is enough, you'll want this |
| **skip** | not needed, skip, ignore, irrelevant, don't load, leave out, already captured elsewhere |

Mixing them in a single section is fine and often clearer than listing keys in isolation.

---

### Tell the model why — it improves classification under pressure

When context budget is tight, the classifier must make trade-offs. Knowing the reason lets it make the right call instead of guessing.

**Without why:**

```markdown
## Context

"contract_text" is essential.
"party_names" is essential.
"jurisdiction" is useful.
"upload_metadata" is not needed.
```

**With why:**

```markdown
## Context

"contract_text" is essential — you'll extract specific clauses from it,
so you need the full text, not a summary.

"party_names" is essential — every clause you draft must name the
correct parties, and there must be no ambiguity.

"jurisdiction" is useful — it tells you which boilerplate to apply,
but a one-word value is enough.

"upload_metadata" and "file_hash" are not needed, skip them.
```

---

### Match signal strength to what the step actually does

Only mark something essential if the step genuinely cannot do its job without the full value. Over-using "essential" inflates context on every step and dilutes the signal.

```markdown
## Context

# Validation step — needs every record to check completeness
"processed" is essential — read every item, including failed ones.
You need the count, filenames, and status for each entry.

# Only needs orientation, not every field
"handoff" is useful — the gist of what the previous step did is enough.

# Pure noise for this step
"raw_api_responses", "temp_buffer", and "chunk_index" are not needed.
```

---

### Guide file loading when content is in files, not state

When the real content is on disk, use the context section to tell the model how to load it selectively rather than loading everything at once.

```markdown
## Context

"index" is essential — it lists the file paths you'll need to read.
Don't preload all output files. Use read_file on specific paths
from the index, only for entries that need validation.

"raw_chunks" in state is a skip — read the chunk files directly
from output/ if you need the content, don't use the state copy.
```

---

### Keep it short — one line per key is usually enough

The context section goes into the classification call on every step run. Long paragraphs per key burn tokens on every execution. Aim for one tight line per key, three to eight keys total.

```markdown
## Context

"job_requirements" — essential, you'll match every must-have against the profile.
"profile_summary" — essential, the anchor for all tailoring decisions.
"tailoring_plan" — essential, drives which sections to emphasise.
"experience" and "skills" — useful, pull from them as needed.
"raw_job_html" — skip, already parsed into job_requirements.
"file_hash" and "upload_time" — skip.
```
