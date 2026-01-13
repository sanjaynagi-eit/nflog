# nextlog (Nextflow log inspector)

`nextlog` is a small CLI and Python library that inspects recent Nextflow runs in a project directory. It reads `.nextflow/history`, `.nextflow.log`, and `work/**/.command.*` files to summarize runs and surface failing tasks quickly.

## Install

```bash
pip install -e .
```

### One-liner installer

```bash
REPO_URL=https://github.com/your-org/nextlog.git bash -c "$(curl -fsSL https://raw.githubusercontent.com/your-org/nextlog/main/nextlog/install.sh)"
```

You can also run the script locally after cloning: `REPO_URL=<repo> bash nextlog/install.sh`. Override `TARGET_DIR` or `BRANCH` as needed.

## CLI usage

- List runs: `nextlog runs --limit 5`
- Run status: `nextlog status` or `nextlog status --run <session-id>`
- Show failing tasks: `nextlog errors --show 3`
- Print a specific error file: `nextlog errfile --index 1`

Use `--json` on any command for machine-readable output and `--debug` to see which artifacts were used.
