# 🪵 nextlog 

`nflog` is a small CLI and Python library that inspects recent Nextflow runs in a project directory. It reads `.nextflow/history`, `.nextflow.log`, and `work/**/.command.*` files to summarize runs and surface failing tasks quickly.

## Install

Clone the repo and install with pip:

```bash
pip install -e .
```

## CLI usage

- Quick summary: `nflog` (shows status + errors for the most recent run)
- List runs: `nflog runs --limit 5`
- Run status: `nflog status` or `nflog status --run <session-id>`
- Show failing tasks: `nflog errors --show 3`
- Print a specific error file: `nflog errfile --index 1`

Use `--json` on any command for machine-readable output and `--debug` to see which artifacts were used.
