---
title: "Short imperative title of the change"
status: pending_spec   # pending_spec | specified | in_progress | done | blocked
priority: medium       # high | medium | low
specs: pending         # complete | not-needed | pending
auto: no               # yes = the scheduled agent may pick this up on its own
depends:               # optional: slug(s) of tasks that must be done first (comma-separated)
model:                 # optional: model override for autonomous execution
repo: ~/Projects/your-app
approved_on: YYYY-MM-DD
executed_by:           # stamped on execution: cron | manual (empty = not executed yet)
---

## What (goal)
One or two sentences. What exists after this task that didn't before?

## Why
The reason this matters — enough context that the agent makes the right micro-decisions.

## Specs / acceptance criteria
The contract. When every box is checked, the task is done. Written so precisely that an agent
can execute WITHOUT asking anything. Ambiguity found during execution → task goes `blocked`
with a note, never guessed.
- [ ] ...
- [ ] ...

## Scope / likely files
Where the change probably lives. Also state what is OUT of scope.

## Verification
How it's proven: which tests/build/lint to run, and what manual check (if any) closes it.

## Execution notes
(the agent fills this while executing: branch, PR URL, what was done, verification output)
