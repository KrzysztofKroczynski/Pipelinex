# Human Input

Steps can pause for a human decision. Declare `human_input` in `pipeline.yaml`:

```yaml
- id: step-03-human-review
  human_input:
    mode: console
    prompt: "Review output/step-02/report.md and type your decision:"
  can_goto:
    - step-04-output
    - step-02-process
```

The runner collects the response and stores it in state as `"human_input"` before the step runs. The step's SKILL.md describes what to do with it.

---

## Mode: console

Runner pauses and prints a prompt to the terminal. User types a response.

```yaml
human_input:
  mode: console
  prompt: "Approve this output? (yes / no / revise):"
```

Good for simple approvals and quick decisions during local runs.

**SKILL.md guidance:**
```markdown
## Context

The human's response is in state under "human_input".

## Task

Read the human_input value. If "yes", route to step-04-output.
If "no" or "revise", route back to step-02-process and summarise
what needs changing in your handoff note.
```

---

## Mode: file

Runner writes the question to `output/step-name/waiting.md` and pauses. Human edits or replaces the file, then presses Enter in the terminal to continue.

```yaml
human_input:
  mode: file
  prompt: "Review output/step-02/report.md and write your decision in output/step-03-human-review/decision.md"
```

Good for decisions that need more context or time — the human can review output files before deciding.

The human's response is read from `output/step-name/decision.md`. If that file doesn't exist when Enter is pressed, `human_input` in state will be empty.

---

## Mode: tool

Runner calls a custom tool to collect the input. The tool handles the waiting (Slack message, email, form, webhook) and returns the human's response.

```yaml
human_input:
  mode: tool
  tool: request_slack_approval
```

The named tool must exist in the pipeline's tool resolution path. The runner calls it with `{"prompt": "..."}` and stores the response.

The tool is responsible for waiting — it can block until a human responds, poll an API, or anything else that fits the workflow.

**Example tool (Slack):**
```python
# tools/request_slack_approval/run.py
import sys, json, os, time
from slack_sdk import WebClient

args = json.load(sys.stdin)
client = WebClient(token=os.environ["SLACK_TOKEN"])

client.chat_postMessage(channel="#approvals", text=args["prompt"])

# Poll for a reply (simplified)
time.sleep(60)
# ... read the reply ...

print(json.dumps({"response": "approved"}))
```

Good for async workflows where the human isn't at the terminal.
