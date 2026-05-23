# Step 3: Build Memo Outline

Design a structured 4-section outline for the research memo. All necessary information has already been extracted into key_findings — the raw source documents are not needed here.

## Context

All relevant content from the sources has been distilled into key_findings. Loading the raw source text again would waste context window space without adding value.

State key guidance:
- `key_findings`: ESSENTIAL — the only content needed to build the outline
- `research_question`: ESSENTIAL — the outline must answer this question
- `source_a`: SKIP — raw text already processed, do not load
- `source_b`: SKIP — raw text already processed, do not load
- `source_c`: SKIP — raw text already processed, do not load

## Task

Using key_findings and research_question from pipeline state:

1. Design a 4-section outline where each section groups related findings thematically. Each section should have:
   - A title
   - 2–3 bullet points summarising the key points that will appear in that section
   - Which finding(s) from key_findings map to it

2. Save to state:
   ```
   write_state(key="memo_outline", value={
     "sections": [
       {"title": "...", "points": ["...", "..."], "sources": ["finding ref"]},
       ...
     ]
   })
   ```

3. Write a handoff note:
   write_state(key="handoff", value="Built 4-section outline in memo_outline. Next step: write the full memo draft section by section, using memo_outline as the structure and key_findings for the detail.")
