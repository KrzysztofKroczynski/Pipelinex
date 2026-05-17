# Getting Started

## Install

```bash
pip install -e .
```

After that, `folpipe` is available globally.

---

## Create a pipeline

```bash
folpipe new my-pipeline
```

This scaffolds:

```
my-pipeline/
├── pipeline.yaml
├── SKILL.md
├── .env
├── .gitignore
├── input/
├── output/
└── step-01-start/
    └── SKILL.md
```

---

## Configure the model

Open `my-pipeline/.env` and add your API key:

```bash
DEEPSEEK_API_KEY=sk-...
```

Open `my-pipeline/pipeline.yaml`. The default uses DeepSeek:

```yaml
model:
  provider: deepseek
  name: deepseek-chat
  api_key: ${DEEPSEEK_API_KEY}
```

Change `provider` and `name` to use any other model. See [supported providers](pipeline-structure.md#model).

---

## Write your first step

Open `my-pipeline/step-01-start/SKILL.md` and describe what you want:

```markdown
# Summarise input

Read the file from the input folder and write a short summary.

## Task

Read the file in input/ using read_file. Write a 3-paragraph summary
to output/summary.md using write_file.
```

---

## Run it

```bash
# Drop a file into input/
cp myfile.txt my-pipeline/input/

# Run
folpipe run ./my-pipeline --watch
```

`--watch` shows live step and tool progress.

---

## Add more steps

```bash
folpipe new step step-02-review --in ./my-pipeline
```

Edit the new `step-02-review/SKILL.md`. Add the step to `pipeline.yaml`:

```yaml
steps:
  - id: step-01-start
  - id: step-02-review
    terminal: true
```

---

## What's next

- [Pipeline Structure](pipeline-structure.md) — full reference for `pipeline.yaml` and `SKILL.md`
- [Tools](tools.md) — what tools are available and how to add your own
- [Execution Patterns](execution-patterns.md) — branching, loops, parallel dispatch
