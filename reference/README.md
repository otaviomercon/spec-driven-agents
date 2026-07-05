# reference/ — adaptable scripts

Extracted from a real production setup and **scrubbed to be generic**. These are *reference
implementations* of the patterns in the [methodology](../docs/en/methodology.md) — adapt paths,
naming and stack to yours. They are not an installable package (the installable part is
[`control-plane/`](../control-plane/README.md)).

| File | Pattern it implements |
|---|---|
| [`backlog/task-template.md`](backlog/task-template.md) | Level-2 task file: YAML frontmatter + spec body ("executable without asking") |
| [`backlog/ideas-template.md`](backlog/ideas-template.md) | Level-1 ideas file: frictionless capture |
| [`ci/ci.yml`](ci/ci.yml) | CI on every PR — build is the gate, lint informative |
| [`ci/auto-merge.yml`](ci/auto-merge.yml) | Squash-merge automatically when CI goes green |
| [`traceability/log-hook.py`](traceability/log-hook.py) | Agent-runtime hook: one clean line per request / mutating action (read-only noise filtered at the source) |
| [`traceability/digest.py`](traceability/digest.py) | Deterministic daily digest: raw logs → grouped signal (requests, edits, PRs), ~50% noise removed, 0 tokens |

Assumptions: Git + [GitHub CLI](https://cli.github.com) (`gh`), zsh/python3 (macOS defaults).
