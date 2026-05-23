# step-01-analyse

Read three engineering notes from the input/ directory and produce a short
synthesis report highlighting the most actionable advice across all three topics.

## Task

1. Read input/note-a.txt, input/note-b.txt, and input/note-c.txt.
2. Write a synthesis report to report.md (write_file resolves this to your step's
   output folder automatically) that:
   - Groups insights by theme (e.g. "design for scale", "avoid premature optimisation")
   - Calls out the single most important tip from each note
   - Aims for around 250 words
   Trust the write_file response — do not attempt to read back or verify files you just wrote.
3. Save a one-line summary to state key `report_summary`.

## When things go wrong

If a file is missing, note it in the report and continue with the remaining files.

## Self-Reflection

Call `get_run_usage` for actual token and cost totals.
Use `read_docs` to look up relevant framework features before giving advice
(e.g. `read_docs("model")` for pricing/override options,
`read_docs("context budget")` for token reduction, `read_docs("tools")` for
tool efficiency). Then append a `## Run notes` section to this SKILL.md with:

- Total tokens and cost from `get_run_usage`
- One or two concrete, framework-specific suggestions to make this step cheaper
  or faster — reference actual config keys or SKILL.md patterns from the docs
- Whether the output quality justified the spend

Under 120 words. Be specific — no generic advice.

## Run notes

- **Usage**: 8,686 prompt + 927 completion tokens = 9,613 total; $0.00 cost (likely local/test pricing). Output quality justified the spend for this small task.
- **Speed-up**: Reduce prompt tokens by tightening the system prompt — this step reads only three small files, so a trimmed instruction set would help. Alternatively, use `model.name: claude-haiku-3-5` for shorter tasks like this; it's cheaper and fast enough for light synthesis.
- **Cost cut**: If pricing were active, switching from sonnet to haiku would cut cost ~5× with negligible quality loss for a 250-word report.
