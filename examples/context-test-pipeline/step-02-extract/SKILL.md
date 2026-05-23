# Step 2: Extract Key Findings

Read all three source documents and extract the most important findings relevant to the research question.

## Context

This step needs the raw source text in full — every source document is essential for accurate extraction. The research question is essential to guide what counts as a finding.

State key guidance:
- `research_question`: ESSENTIAL — must be read verbatim to frame the extraction
- `source_a`: ESSENTIAL — full text needed, do not summarise before reading
- `source_b`: ESSENTIAL — full text needed, do not summarise before reading
- `source_c`: ESSENTIAL — full text needed, do not summarise before reading

## Task

Using the research_question and the three sources from pipeline state:

1. For each source (source_a, source_b, source_c), identify the 3 most important findings that address the research question. A finding is a concrete, actionable design insight — not a restatement of general principles.

2. Write all findings to state as a structured object:
   ```
   write_state(key="key_findings", value={
     "source_a": ["finding 1", "finding 2", "finding 3"],
     "source_b": ["finding 1", "finding 2", "finding 3"],
     "source_c": ["finding 1", "finding 2", "finding 3"]
   })
   ```

3. Write a handoff note:
   write_state(key="handoff", value="Extracted 3 findings per source (9 total) into key_findings. Next step: build a 4-section outline for the research memo using only key_findings — do NOT re-read the raw sources.")
