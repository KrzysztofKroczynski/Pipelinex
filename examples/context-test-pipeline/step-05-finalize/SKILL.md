# Step 5: Finalize and Write Output

Review the memo draft and write the final polished version to the output folder. Only the draft and the original research question are needed — all intermediate state can be ignored.

## Context

At this stage everything has been condensed into memo_draft. Loading key_findings, memo_outline, or the raw sources would add noise without value.

State key guidance:
- `memo_draft`: ESSENTIAL — the document to review and finalize
- `research_question`: ESSENTIAL — verify the final memo answers it
- `key_findings`: SKIP — already incorporated into the draft
- `memo_outline`: SKIP — already used to structure the draft
- `source_a`: SKIP — fully processed, not needed
- `source_b`: SKIP — fully processed, not needed
- `source_c`: SKIP — fully processed, not needed

## Task

1. Review memo_draft for:
   - Does the introduction clearly state the research question?
   - Does each section have a clear point?
   - Does the conclusion answer the research question directly?
   - Fix any awkward phrasing or structural issues.

2. Write the polished final memo to the output folder:
   ```
   write_file(path="memo.md", content="<polished memo>")
   ```

3. Write a brief summary file:
   ```
   write_file(path="summary.md", content="# Run Summary\n\n**Research question:** <question>\n\n**Word count:** ~N words\n\n**Sections:** <list section titles>\n\n**Context tiers used:** source_a/b/c=skip in steps 3-5; key_findings=essential in steps 3-4; memo_draft=essential in step 5.")
   ```

4. Final handoff (pipeline ends here — no next step):
   ```
   write_state(key="handoff", value="Pipeline complete. Final memo written to output/step-05-finalize/memo.md")
   ```
