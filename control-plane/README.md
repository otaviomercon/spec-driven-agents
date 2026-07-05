# AI control plane (macOS / SwiftBar)

**🌎 EN** — *(the [methodology docs](../docs/en/methodology.md) are available in
[Español](../docs/es/metodologia.md) and [Português](../docs/pt-BR/metodologia.md))*

A generic menu-bar control plane for AI-powered processes — **two plugins, one config file**:

- **🧠 `control-plane.5m.sh`** — operates the *engines*: health, per-process AI engine, local models,
  on-demand actions.
- **📦 `box.1m.sh`** — monitors the *work*: your backlog(s) projected live in the menu bar — blocked
  tasks (need your decision), PRs to review, the auto queue the scheduled agent will drain, and recent
  deliveries. This is where you watch the "you specify, agents execute" loop actually running.

What the 🧠 gives you:

- **Health badges** — any process that fails leaves `<name>.FAILED` in your logs dir → the menu icon
  turns 🔴N with the message, a link to the log and a "mark resolved" button. Markers are removed by
  the process itself when it recovers (self-healing).
- **Engine per process** — every `[task:x]` in the config becomes a menu: run it on the local LLM
  (Ollama), on a specific cloud account, or follow the system default. One click = one config write.
- **Local model management** — installed Ollama models, which are loaded in RAM, unload on demand.
- **On-demand actions** — every `[action:Name]` becomes a clickable trigger that runs in background.

**Adding a process or an action never requires touching the plugin code — only the config file.**

## Install

1. Install [SwiftBar](https://swiftbar.app) (`brew install swiftbar`) and pick a plugins folder.
2. Copy this `control-plane/` directory somewhere stable, then link the plugins into your SwiftBar
   plugins folder:
   ```
   ln -s /path/to/control-plane/control-plane.5m.sh <swiftbar-plugins>/control-plane.5m.sh
   ln -s /path/to/control-plane/box.1m.sh           <swiftbar-plugins>/box.1m.sh
   ```
   (`5m`/`1m` in the filename = refresh interval; rename to taste.)
3. Create your config:
   ```
   mkdir -p ~/.config/spec-driven-agents ~/.local/state/spec-driven-agents/logs
   cp config.example.md ~/.config/spec-driven-agents/config.md
   ```
   Point the `backlogs` key at the folder(s) where your task files live.
4. (Optional, local tier) Install [Ollama](https://ollama.com) and pull a small model:
   `ollama pull gemma3:4b`.
5. Refresh SwiftBar. You should see 🧠 (or ☁️ if `llm_local = off`) and 📦.

## The 📦 box (backlog monitor)

The box is a **pure projection** of your task files — zero tokens, zero state of its own, so it can
never drift from reality. It scans every `.md` with a `status:` frontmatter under your `backlogs`
dirs and shows, in priority order of attention:

| Section | Meaning |
|---|---|
| 🔴 **Blocked** | tasks an agent stopped on — these need *your* decision |
| 🟢 **PR to review** | `in_progress` tasks with their PR attached (one click to open) |
| 🔵 **Auto queue** | `specified` + `auto: yes` — what the scheduled agent will pick up next |
| ✅ **Delivered** | `done`, newest first |

The menu-bar badge summarizes it (`📦 2🔴 1🟢 4🔵`) so you know at a glance whether anything needs
you. Clicking a task opens its file; specifying happens in chat, monitoring happens here.

## Wire your first process

A "process" is any script of yours that uses AI. To integrate it:

1. Declare it in the config: add a `[task:my-process]` section.
2. Make your script *ask the config* which engine to use:
   ```zsh
   source /path/to/control-plane/lib/config.sh
   engine_local="$(cfg_get llm_local my-process)"   # on|off
   account="$(cfg_get account my-process)"          # which cloud account
   model="$(cfg_get local_model my-process)"        # which local model
   ```
   Route accordingly (Ollama's API on `localhost:11434`, or your provider CLI with that account).
3. On failure, leave a marker: `echo "what failed" >> $logs_dir/my-process.FAILED` — and remove it
   when the run recovers. That's all the health system needs.
4. (Optional) add an `[action:Run-my-process-now]` with `cmd = /path/to/my-process.sh`.

## Design notes (why it's built this way)

- **The config file is the single source of truth** — the UI writes it, scripts read it, you can edit
  it by hand, and it diffs cleanly in git. No hidden state.
- **Health is pull-based and self-healing** — processes don't push notifications the UI must track;
  they leave/remove a marker file. The badge disappears exactly when the problem does.
- **Fallback is the default** — local-first processes fall back to cloud when Ollama is down. A dead
  daemon should never block your pipeline; the local tier is a cost optimization, not a dependency.
- **macOS-only, on purpose** — SwiftBar + launchd keep it to one file with zero services. The
  patterns (config-driven engines, FAILED markers, actions) port to any platform; this code doesn't.
