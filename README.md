# spec-driven-agents

**🌎 [English](README.md) · [Español](README.es.md) · [Português](README.pt-BR.md)**

> **You specify by chatting. Agents execute.**
> A working methodology — plus an installable control plane — for running your projects with AI agents
> that implement tasks autonomously, while you keep the judgment.

## The core idea

Most people use AI chat to *write code with them*. This methodology inverts it:

1. **You use the chat to think and produce specs** — ideas get captured in a lightweight backlog, then
   refined into tasks so well-specified that *an agent can execute them without asking you anything*.
2. **Agents execute the tasks** — on demand or on a schedule (cron). For each task: branch → implement →
   verify (lint/types/tests/build) → PR → CI → auto-merge → gated deploy. A deterministic *reconcile*
   loop closes the cycle: when the PR merges, the task is marked done and archived, automatically.
3. **A control plane operates it all** — one menu-bar UI where you see health, pick which AI engine
   (local LLM / cloud provider / which account) runs each process, and trigger actions. No terminal.

The human decides and specifies. The machine implements. Production is protected by **gates, not by
human review**: CI on every PR, deploy gated on build/tests, safe migrations. That's why merging is free.

## What's in this repo

| Directory | What it is |
|---|---|
| [`docs/`](docs/en/methodology.md) | **The playbook** — the full methodology, in 3 languages |
| [`control-plane/`](control-plane/README.md) | **Installable** — two menu-bar plugins (macOS/SwiftBar): 🧠 engine control (per-process AI engine, health, actions) and 📦 **the box**, a live backlog monitor (blocked / PRs to review / auto queue / delivered) |
| [`reference/`](reference/) | **Adaptable scripts** — traceability hook, deterministic log digester, CI/auto-merge templates, task templates. Reference code, not plug-and-play |

## The pillars (short version)

- **Two-level backlog** — Level 1: raw ideas (one file). Level 2: one file per task with YAML frontmatter
  + acceptance criteria. A board is *projected* from task files (never the other way).
- **Spec quality is the contract** — a task is executable only when its specs are complete. The agent
  implements *exactly* what the specs say; anything ambiguous → task is blocked, not guessed.
- **Cost tiers, enforced by design** — before any LLM call: (1) can a deterministic script do it? 0 tokens.
  (2) Is it low-judgment, high-volume? → local LLM (Ollama). (3) High judgment only → frontier model.
- **Deterministic gates before any LLM** — schedulers first `grep` for eligible work; an idle hour costs
  one grep, zero tokens. The script does git/PR deterministically; the agent only writes code.
- **Traceability for free** — a hook logs every request and mutating action; a nightly job produces a
  clean daily digest (deterministic) + optional prose summary (LLM). You can always answer "what
  happened on day X".
- **Self-healing** — reconcile closes finished tasks; boards regenerate from source files; failures leave
  a `*.FAILED` marker that surfaces as a red badge in the control plane until resolved.

## Requirements & honest scope

- The methodology is tool-agnostic (any agentic CLI that can run headless — we use Claude Code).
- The control plane is **macOS-only** (SwiftBar + launchd). The patterns port anywhere; that code doesn't.
- `reference/` scripts assume Git + GitHub CLI (`gh`) and were extracted from a real working setup —
  adapt paths and naming to yours.

## Quick start

1. Read the [methodology](docs/en/methodology.md) (15 min).
2. Install the [control plane](control-plane/README.md) and wire your first process.
3. Copy the [task template](reference/backlog/task-template.md) and write your first spec by chatting
   with your agent: *"help me specify this idea until an agent could execute it without asking me"*.

## License

MIT — see [LICENSE](LICENSE).
