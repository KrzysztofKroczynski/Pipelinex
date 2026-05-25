# Check fit before proceeding

Assess how well the applicant's profile matches the job, and decide whether
to proceed, gather more context, or cancel.

## Context

Read from state: job_title, company, requirements (must_have, nice_to_have),
tech_stack, profile, experience, skills, projects.

All of these are essential — read them in full.

## Task

### 1. Score the fit

Go through requirements.must_have one by one. For each, judge whether the
applicant's experience, skills, or projects clearly cover it. Produce:

- `matched`: list of must-haves the applicant covers
- `missing`: list of must-haves they don't cover
- `fit_level`: "strong" / "partial" / "poor"
  - strong: covers ≥ 75% of must-haves
  - partial: covers 40–74%
  - poor: covers < 40%

Save to state:
- write_state key "fit_assessment": { fit_level, matched, missing, match_pct }

### 2. If fit is strong

Save a one-line handoff and proceed directly — no human check needed:
- write_state key "handoff": "Fit is strong (X/Y must-haves matched). Proceeding to tailor."
- Route to step-03-tailor.

### 3. If fit is partial or poor

Call ask_human with a clear, concise summary. Example prompt:

```
Role: <job_title> at <company>
Fit: <fit_level> (<match_pct>% of must-haves matched)

Matched: <matched list>
Missing: <missing list>

Options:
  [C] Continue anyway — proceed with the CV as-is
  [A] Add context — type extra background below (e.g. unreported experience,
      relevant projects not in profile files). It will be included in tailoring.
  [Q] Quit — cancel the pipeline run

Your choice (C / A / Q), or type additional context directly:
```

### 4. Act on the human's response

**If the response is "Q" or any clear cancellation** (quit / cancel / stop / no):
- Call cancel_pipeline with reason: "User cancelled. Fit was <fit_level> (<match_pct>% of must-haves). Missing: <missing list>."

**If the response is "C" or any clear "proceed"** (continue / yes / go / ok):
- write_state key "handoff": "User chose to proceed despite <fit_level> fit."
- Route to step-03-tailor.

**If the response contains additional context** (anything other than a single letter):
- write_state key "extra_context": the full text of what the user typed
- write_state key "handoff": "User provided extra context. Proceeding to tailor."
- Route to step-03-tailor.

## Notes

Be direct in the ask_human prompt — the user is making a real decision.
Show the actual gaps, not a softened summary.
If ask_human is not available (dry-run or non-console mode), proceed as if the
user chose "C" and add a note to the handoff.
