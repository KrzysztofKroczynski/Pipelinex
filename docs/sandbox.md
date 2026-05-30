# Filesystem Sandbox

Every step runs inside a filesystem sandbox. The model can only read files within
the pipeline directory. Attempts to read outside it are rejected at the tool level —
the model receives a clear error and can adapt without any runner crash or exception.

---

## What is blocked

**Paths outside the pipeline directory**

Absolute or relative — it doesn't matter how the model constructs the path.
`../../etc/passwd`, `C:\Users\someone\secrets`, `../sibling-pipeline/.env` — all denied.

**Secret-named files**

The following filename patterns are blocked regardless of where they live,
including inside the pipeline directory:

| Pattern | Examples |
|---|---|
| `.env`, `*.env`, `.env.*` | `.env`, `prod.env`, `.env.local` |
| `secrets.*`, `*.secret` | `secrets.json`, `db.secret` |
| `*.key` | `api.key`, `id_rsa.key` |
| `*.pem`, `*.p12`, `*.pfx`, `*.crt` | TLS/certificate files |

The model never sees API keys or credentials even if it explicitly tries to read them.

**`run_script` outside the pipeline**

The `working_dir` parameter must be inside the pipeline directory. Commands that
would start from an external path are rejected before execution.

---

## What is allowed

**Everything inside the pipeline directory**

`input/`, `output/`, step folders, `SKILL.md` files, `pipeline.yaml`, any file
the author placed there.

**Symlinks inside the pipeline directory**

A symlink placed inside the pipeline acts as a user-granted shortcut to whatever
it points to — including external paths. The symlink itself lives within the
boundary, which is sufficient authorization.

This is the intended mechanism for giving a step access to data that lives outside
the pipeline:

```bash
# Grant access to an external dataset
ln -s /mnt/shared/datasets/q3-2026 my-pipeline/input/dataset
```

The model can now read through `input/dataset/` as if the files were local.
No configuration needed — the symlink is the access grant.

---

## Runtime environment

Before each step's first LLM call, the runner injects a `## Runtime Environment`
block into the system prompt:

```
## Runtime Environment

- Pipeline root: `/path/to/my-pipeline`
- Your output folder: `output/step-02-process/`
- Shared state: `output/state.json`
- Input folder: `input/`
```

This gives the model the concrete paths it needs upfront. Without this, models
sometimes guess OS-specific paths or use `run_script` to search for files —
the environment block eliminates that need entirely.

---

## Self-correction via reflection

When self-reflection is enabled, the runner passes a diagnostics summary to
every reflection call. If a step triggered sandbox denials or used the wrong
tools to find files, the reflection model sees this explicitly:

```
## Step Diagnostics

- LLM calls: 8
- Tools used: run_script ×5, read_file ×2, write_file ×1
- Tool errors (3):
  - read_file: "Access denied: '.env' is a protected file"
  - run_script: "Command timed out after 60 seconds"
  - read_file: "Access denied: path is outside the pipeline directory"
```

The reflection model uses this to update the step's SKILL.md and prevent the
same pattern on the next run. See [Self-reflection](pipeline-structure.md#self-reflection).
