# Examples

## doc-pipeline — Document processing

Located at `doc-pipeline/`. Ingests documents, chunks them, embeds them (or stubs embedding), and produces a searchable index.

### What it does

```
input/*.txt  →  chunks  →  embeddings  →  index.jsonl  →  index.md
```

### Pipeline structure

```
doc-pipeline/
├── pipeline.yaml
├── SKILL.md
├── .env                          # DEEPSEEK_API_KEY
├── input/
│   ├── intro-to-ml.txt
│   ├── software-design-principles.txt
│   └── distributed-systems.txt
├── tools/
│   └── send_slack/               # stub notifier
├── step-01-ingest/SKILL.md
├── step-02-process/
│   ├── SKILL.md                  # orchestrates sub-steps
│   ├── sub-01-chunk/SKILL.md     # splits one doc into chunks
│   ├── sub-02-embed/SKILL.md     # embeds chunks (stubs without real API)
│   └── sub-03-index/SKILL.md     # writes to index.jsonl
├── step-03-validate/SKILL.md
├── step-04-output/SKILL.md       # terminal: writes index.md + index.json
└── step-05-partial-output/SKILL.md  # terminal: handles partial failures
```

### Step flow

```
step-01-ingest
  ↓ (always)
step-02-process  ←──┐
  ↓ (model chooses)  │
  ├──────────────────┘  (loop if needed)
  ↓
step-03-validate
  ↓ (model chooses)
  ├── step-04-output       (all passed)
  └── step-05-partial-output  (too many failures)
```

### Key design points

**step-01-ingest** reads all files in `input/` and writes a `documents` list to state. Each entry has `filename`, `type`, `content`.

**step-02-process** orchestrates sub-steps via `dispatch_task`:
- `sub-01-chunk`: splits a document into ~500-word chunks, writes to `output/step-02-process/<filename>-chunk-N.txt`
- `sub-02-embed`: produces embedding records (empty embedding vectors if no embedding API configured), writes `<filename>-embeddings.json`
- `sub-03-index`: appends records to `output/step-02-process/index.jsonl`

Multiple documents can be dispatched in parallel: all `sub-01-chunk` calls at once, then all `sub-02-embed`, then all `sub-03-index`.

**step-03-validate** reads all chunk files and the index. Checks completeness. Routes to `step-04-output` or `step-05-partial-output`.

**step-04-output** writes the final `output/index.md` and `output/index.json`.

### Run it

```bash
folpipe run ./doc-pipeline --watch
```

Add or replace files in `doc-pipeline/input/` to process different documents.

---

## cv-pipeline — CV tailoring

Located at `cv-pipeline/`. Fetches a job posting from a URL, reads a developer profile from `input/`, writes a tailored CV, and renders it to PDF. The included profile (Alex Rivera) is a fictional example — replace the `input/*.md` files with your own details before running.

### What it does

```
job URL  +  profile files  →  tailored CV (Markdown)  →  styled PDF
```

### Pipeline structure

```
cv-pipeline/
├── pipeline.yaml
├── SKILL.md
├── .env                       # DEEPSEEK_API_KEY
├── input/
│   ├── profile.md             # contact info, summary
│   ├── experience.md          # work history
│   ├── skills.md              # technical skills
│   ├── projects.md            # notable projects
│   └── education.md           # degrees, certs
├── tools/
│   ├── fetch_page/            # HTTP page fetcher (deps: httpx)
│   └── render_pdf/            # HTML→PDF via Edge headless
├── step-01-fetch-job/SKILL.md
├── step-02-load-profile/SKILL.md
├── step-03-tailor/SKILL.md
├── step-04-write-cv/SKILL.md
└── step-05-render-pdf/SKILL.md  # terminal
```

### Step flow

```
step-01-fetch-job
  ↓
step-02-load-profile
  ↓
step-03-tailor
  ↓
step-04-write-cv
  ↓
step-05-render-pdf  (terminal)
```

### Key design points

**step-01-fetch-job** calls `fetch_page` with the job URL. Extracts `job_title`, `company`, `requirements` (split into `must_have` and `nice_to_have`), `responsibilities`, `tech_stack`. Handles JS-rendered pages gracefully (infers role from URL if page returns no content).

**step-02-load-profile** reads all five `input/*.md` files. Stores `profile`, `experience`, `skills`, `projects`, `education` in state. Does not summarise — preserves exact details (company names, dates, numbers) for accurate tailoring.

**step-03-tailor** cross-references requirements against the profile. Decides what to emphasise, de-emphasise, or omit. Writes a `tailoring_plan` to state.

**step-04-write-cv** produces `output/cv.md` — a tailored CV in Markdown. Also produces `output/cover-note.md`. Does not invent experience.

**step-05-render-pdf** designs a two-column HTML/CSS layout (dark sidebar, light main), imports Google Fonts, uses flexbox. Calls `render_pdf` which runs Edge headless to produce `output/cv.pdf`. Also saves `output/cv.html`.

### Custom tools

**fetch_page** (`tools/fetch_page/run.py`):
- HTTP GET with httpx
- Strips HTML tags, script, style, nav, footer
- Returns `{text, url, status}`
- Dep: `httpx`

**render_pdf** (`tools/render_pdf/run.py`):
- Finds `msedge.exe` or `chrome.exe` on the system
- Writes HTML to a temp file, passes `file://` URL to `--headless=new --print-to-pdf`
- Falls back to Playwright if no browser found
- Full modern CSS: flexbox, grid, Google Fonts, CSS variables, `print_background: true`

### Run it

```bash
# Fill in your real profile data first:
# edit cv-pipeline/input/profile.md, experience.md, skills.md, projects.md, education.md

folpipe run ./cv-pipeline --input "https://example.com/jobs/backend-engineer" --watch
```

Output:
- `cv-pipeline/output/cv.md` — tailored CV in Markdown
- `cv-pipeline/output/cover-note.md` — cover letter
- `cv-pipeline/output/cv.html` — styled HTML (open in browser)
- `cv-pipeline/output/cv.pdf` — print-ready PDF

### Notes

- JS-rendered job boards (Ashby, Lever, Greenhouse) often return empty HTML. The model handles this by inferring the role from the URL and producing a best-effort CV. For accurate tailoring, paste the job description as `--input` instead:
  ```bash
  folpipe run ./cv-pipeline --input "job-description.txt" --watch
  ```
- PDF requires Edge or Chrome to be installed. If neither is found, `cv.html` is still written and can be printed to PDF from the browser.
