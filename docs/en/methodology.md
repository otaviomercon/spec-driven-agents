# The methodology: you specify by chatting, agents execute

This is a complete, battle-tested way of working where the human's job is **judgment** (deciding what
and why, and specifying it well) and the agents' job is **implementation** (branch, code, verify, PR,
merge, deploy). It runs today across multiple real production projects.

---

## 1. The loop

```
 idea ──> backlog L1 ──> refine by chat ──> task w/ specs (L2) ──> agent executes ──> PR ──> CI
  ↑                                                                                        │
  └──────────────── traceability (automatic log + daily digest) <── deploy <── auto-merge ─┘
```

Everything else in this playbook exists to make that loop **cheap** (cost tiers, deterministic gates),
**safe** (deployment gates) and **self-healing** (reconcile, projected boards, failure markers).

## 2. The two-level backlog

Each project has its own backlog, next to (not inside) the repo:

- **Level 1 — ideas**: a single file. Capturing is frictionless: a title, a date, some notes. No
  commitment. Ideas are refined *in chat* ("let's think this through") or discarded.
- **Level 2 — tasks**: one file per task, YAML frontmatter + body. A task is born when an idea is
  *approved* — and becomes executable only when it is *specified*.

Task file shape (see [`reference/backlog/task-template.md`](../../reference/backlog/task-template.md)):

```markdown
---
title: Fix ROI calculation per currency
status: specified      # pending_spec | specified | in_progress | done | blocked
priority: medium
specs: complete        # complete | not-needed | pending
auto: no               # yes = the scheduled agent may pick it up
depends:               # optional: slugs that must be done first
repo: ~/Projects/my-app
---
## What (goal)
## Why
## Specs / acceptance criteria   ( - [ ] ... )
## Scope / likely files
## Verification   (how it's proven: tests/build/manual)
## Execution notes   (the agent fills this when executing)
```

**The board is a projection.** The kanban/board view is *generated* from task frontmatter by a
deterministic script — never edited by hand. Source of truth = task files. If a chat forgets to
regenerate, a scheduled job regenerates it anyway (self-healing).

## 3. Specifying by chat (the human's craft)

The quality bar: **a task is ready when an agent could execute it without asking you anything.**

In practice you chat with your agent: *"help me specify this idea until it's executable"*. The agent
asks the clarifying questions a good engineer would, and writes the spec into the task file. You review
acceptance criteria — that's your contract. Ambiguity discovered during execution → the task gets
**blocked with a note**, never guessed.

Hard rule that keeps the system honest: **before implementing any change (any size), its task must
exist**. When implementing, mark it `in_progress` + paste the PR URL. That URL is what lets the
machinery close the cycle for you.

## 4. Agents execute

Two modes, same guarantees:

- **On-demand**: you say "execute task X". The agent reads the specs, goes to the repo, starts from a
  fresh main, creates a branch, implements *exactly* the specs, verifies (lint/types/tests/build),
  opens a PR, merges when CI is green.
- **Continuous (scheduled)**: an hourly cron per project drains the queue of tasks marked
  `specified` + `auto: yes` — without you issuing commands.

**The critical design decision:** the *script* does git/PR deterministically (branch, commit, push,
`gh pr create`); the *agent only writes code*. The PR always gets opened — it doesn't depend on the
LLM remembering. If anything fails (CI red, ambiguity), the task is marked `blocked` and the run moves
on to the next task; nothing retries in a loop.

**Closing the cycle is automatic:** a *reconcile* job (every ~15 min, zero tokens — it only calls
`gh`) finds tasks `in_progress` whose PR merged, marks them `done`, archives them and regenerates the
board. If a PR conflicts with main, the task goes `blocked` + you get notified — a conflict needs your
decision, it's never auto-resolved.

## 5. Merging is free because gates protect production

The safety net is **not** human review:

1. **Gated deploy** (the non-negotiable minimum): the deploy runs build/tests — if it fails, production
   stays on the last good version (e.g. Vercel `buildCommand` running your tests).
2. **CI on every PR**: lint/types/tests/build. Auto-merge only on green.
3. **Safe migrations**: idempotent, validated from scratch in CI (disposable database), destructive
   changes gated.
4. **Verification in the change**: the agent runs what applies before closing and reports real output.

If a project lacks these gates, *that* is the risk to fix — not merging speed. Templates in
[`reference/ci/`](../../reference/ci/).

## 6. Cost tiers: don't spend frontier tokens on cheap work

Before sending anything to a frontier model, place it in the cheapest tier that solves it well:

1. **No-LLM (deterministic)**: regex / file extension / domain lookup → pure script. 0 tokens.
2. **Local LLM (Ollama)**: low-judgment, high-volume — classify, tag, route, short summaries. A single
   shared helper (`llm.sh --task <x>`) routes each named task to local or cloud based on config; if
   the local daemon is down it falls back to cloud automatically. Consumers never decide the route.
3. **Frontier model**: high judgment only — writing code, decisions, fine-grained content.

And the pattern that keeps schedulers free: **a deterministic gate before any LLM**. The hourly cron
first greps for eligible tasks; if there are none, it exits. An idle hour costs one grep.

Two honest lessons from production about local models:
- Small local models (~4B) follow instructions well **on small inputs and collapse on large ones**
  (wrong language, explaining line-by-line). Chunk per project/section, or keep them out of long jobs.
- Let the **deterministic layer own the facts** (digests, boards, logs) and the LLM only write prose on
  top. If the model writes something poor, you lose polish — never data.

## 7. Traceability for free

- A **hook** on the agent runtime appends one line per user request and per *mutating* action
  (writes, commits, PRs — read-only exploration is filtered out at the source) to a raw per-session log.
- A nightly job consolidates the day: a **deterministic digest** (group by project/session, keep
  requests + mutations + PRs, collapse repeated edits — ~50% noise removed, 0 tokens) and optionally a
  **prose executive summary** by the engine you configured (local or cloud, per config).
- Errors never overwrite the daily file (a guard detects auth/limit errors in place of a summary).
- Failed runs leave a `*.FAILED` marker → red badge in the control plane until resolved; a catch-up
  pass re-consolidates any previous day that was left incomplete.

You can always answer *"what happened on day X, in which project, and why?"* — without having written
a single note.

## 8. The control plane (operating all of this without a terminal)

One menu-bar item (macOS/SwiftBar) backed by one config file:

- **Health first**: any process that fails leaves `<name>.FAILED` → the icon becomes 🔴N; each problem
  shows its message, a link to its log, and "mark resolved". Self-healing: markers are removed by the
  process itself on recovery.
- **Engine per process**: every AI-powered process (daily digest, inbox classifier, …) can run on
  the local LLM, or cloud provider account A/B, or follow the system default — switched by click,
  written to the config file (single source of truth, also hand-editable).
- **Local model management**: see installed Ollama models, which are loaded in RAM, who consumes
  which, turn models on/off as menu options.
- **Actions**: on-demand triggers ("consolidate today's digest now", "renew auth token") that run in
  the background and notify on completion.

Install and wire your own processes: [`control-plane/README.md`](../../control-plane/README.md).

## 9. Adopting this (a realistic path)

1. **Week 1 — backlog + specs**: create the two-level backlog for one project. Force the habit: no
   change without a task; specify by chatting.
2. **Week 2 — agent executes on-demand**: let the agent execute specified tasks; add CI + auto-merge +
   gated deploy to that repo (templates in `reference/ci/`).
3. **Week 3 — automate**: add the scheduled runner + reconcile; install the control plane; add the
   traceability hook.
4. **Then**: add the local-LLM tier when you have a real high-volume, low-judgment workload (an inbox
   classifier is the classic first consumer).

Skip stages and it breaks: agents executing without spec discipline just produces fast garbage.
