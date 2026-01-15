# 🪵 nflog 

`nflog` is a small CLI and Python library that inspects recent Nextflow runs in a project directory. It reads `.nextflow/history`, `.nextflow.log`, and `work/**/.command.*` files to summarize runs and surface failing tasks quickly.

## Install

Clone the repo and install with pip:

```bash
pip install -e .
```

## CLI usage

- Quick summary: `nflog` (shows status + failures for the most recent run)
- List runs: `nflog runs --limit 5`
- Run status: `nflog status` or `nflog status --run <session-id>`
- Show failing tasks: `nflog failed --show 3` (alias `nflog f`)
- Show a specific failure: `nflog f 3` (prints the error/log content)

Use `--json` on any command for machine-readable output and `--debug` to see which artifacts were used.
Use `--tsv` for tab-separated tables.

### Examples

Overall summary (default invocation):

```
$ nflog
🪵 Overall summary
🪵 Run sess-123
 Metric        Value
 Overall       fail
 succeeded     5
 failed        1
 running       0
 cached        0
 Derived from  work/.exitcode files

🪵 Failed tasks for sess-123
 #   Process        Exit   .command.err / .log tail
 1   align_reads    1      Traceback (most recent call last)...
 2   variant_call   1      java.lang.RuntimeException: ...
Inspect .command.sh or rerun with -resume for reproduction guidance.
Pass --open to view .command.err in $PAGER.
```

List runs:

```
$ nflog runs --limit 3
🪵 Recent Nextflow runs
 Run ID     Name           Started              Duration   Status   Work dir
 sess-789   great_wave     2024-02-14T10:01:00  0:01:30    success  /data/work
 sess-456   calm_breeze    2024-02-13T18:22:00  0:00:45    fail     /data/work
 sess-123   frosty_meadow  2024-02-12T09:10:00  0:02:10    success  /data/work
```

Status for a specific run:

```
$ nflog status --run sess-789
🪵 Run sess-789
 Metric        Value
 Overall       success
 succeeded     10
 failed        0
 running       0
 cached        0
 Derived from  work/.exitcode files
```

Failed tasks (table view) `nflog f` for shorthand:

```
$ nflog failed --show 2
🪵 Failed tasks for sess-456
 #   Process        Exit   .command.err / .log tail
 1   qc_reads       1      fastqc: command not found
 2   align_reads    1      BWA exited with non-zero status
Inspect .command.sh or rerun with -resume for reproduction guidance.
Pass --open to view .command.err in $PAGER.
```

Inspect a single failure (falls back to `.command.log` when `.command.err` is empty):

```
$ nflog f 2
🪵 Failure #2 for sess-456 (.command.log)
Path: /data/work/xx/yy/.command.log
<contents of the .command.log file>
```

JSON output (any command):

```
$ nflog runs --json --limit 1
[
  {
    "run_id": "sess-789",
    "run_name": "great_wave",
    "started": "2024-02-14 10:01:00",
    "duration": "0:01:30",
    "status": "success",
    "work_dir": "/data/work",
    "log_path": "/data/.nextflow.log",
    "source": "history",
    "command": "nextflow run ."
  }
]
```
