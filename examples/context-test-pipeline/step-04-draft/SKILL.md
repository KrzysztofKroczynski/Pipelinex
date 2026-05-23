# Step 4: Write Memo Draft

Write the full research memo following the outline. The outline provides the structure; key_findings provides the detail. Raw source documents are not needed.

## Context

The memo_outline defines exactly what to write. The key_findings supply the supporting detail. Raw source text has already been fully processed and must be excluded from context to keep the working window focused.

State key guidance:
- `memo_outline`: ESSENTIAL — the structure to follow section by section
- `key_findings`: ESSENTIAL — the factual content to fill each section
- `research_question`: ESSENTIAL — must be answered by the memo introduction and conclusion
- `source_a`: SKIP — already processed into key_findings, do not load
- `source_b`: SKIP — already processed into key_findings, do not load
- `source_c`: SKIP — already processed into key_findings, do not load

## Task

Write a well-structured research memo of approximately 400–600 words:

1. **Introduction** (2–3 sentences): state the research question and preview the answer
2. **Body** (4 sections from memo_outline): each section ~2–3 short paragraphs drawing on the mapped key_findings
3. **Conclusion** (2–3 sentences): direct answer to the research question, key takeaways

Save the complete memo text:
```
write_state(key="memo_draft", value="<full memo text>")
```

Write a handoff note:
```
write_state(key="handoff", value="Wrote full memo draft (~N words) in memo_draft. Next step: review the draft for clarity and completeness, then write the final file to output.")
```
