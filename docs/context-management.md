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
