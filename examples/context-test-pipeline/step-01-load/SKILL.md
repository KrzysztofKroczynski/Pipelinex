# Step 1: Load Sources

Read all input files and write their content into pipeline state. This step seeds the state that all later steps will work from.

## Task

1. Read the following files using read_file:
   - `input/research_question.txt`
   - `input/source_a.txt`
   - `input/source_b.txt`
   - `input/source_c.txt`

2. Save each to state with write_state:
   - key `research_question` → contents of research_question.txt
   - key `source_a` → full text of source_a.txt
   - key `source_b` → full text of source_b.txt
   - key `source_c` → full text of source_c.txt

3. Write a handoff note:
   write_state(key="handoff", value="Loaded research_question + 3 source documents into state. Next step: extract the 3 most important findings from each source relevant to the research question.")
