# Tailor profile to job

Decide exactly what goes in the CV and how to frame it for this
specific role. This step produces a tailoring plan — not the CV
itself, but the precise decisions that drive it.

## Context

The job requirements, responsibilities, and tech_stack are essential — read them in full.
The profile, experience, skills, projects, and education are essential — read them in full.
If `extra_context` is present in state, treat it as additional applicant background that
overrides or supplements the profile files. It came directly from the user.

## Task

Produce a tailoring plan and save it to state:

**Summary line** — write_state key "cv_summary": one punchy paragraph
(3-4 sentences) positioning the developer for this exact role.
Lead with their strongest match. Don't be generic.

**Experience to include** — write_state key "cv_experience": for each
role, decide: include in full / include abbreviated / omit. For included
roles, rewrite the achievement bullets to emphasise what's relevant to
this job. Drop bullets that have no bearing on the role. Add framing
that connects their work to what the employer cares about. Preserve
dates, titles, company names exactly.

**Skills to highlight** — write_state key "cv_skills": organise into
categories relevant to this role. Put the skills that match the job's
tech_stack first. Omit skills with no connection to the role unless
the list is thin.

**Projects to include** — write_state key "cv_projects": pick 2-3
projects most relevant to the role. For each, write one sentence on
what it is and one sentence on why it's relevant to this job.

**Education** — write_state key "cv_education": include as-is unless
something is particularly irrelevant.

**Gaps and honest notes** — write_state key "cv_gaps": list any
must-have requirements the developer doesn't have. Be honest —
the CV must not claim things that aren't in the source files.

**Handoff** — write_state key "handoff": two sentences — the developer's
strongest angle for this role, and the one biggest gap.

## Notes

The goal is relevance, not completeness. A shorter CV with strong
signal beats a long CV with noise. Every line should earn its place.

Never invent experience. If the developer doesn't have something, note
it in cv_gaps. Don't hide gaps — they'll come up in the interview anyway.
