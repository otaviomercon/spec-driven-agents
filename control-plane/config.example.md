# AI control plane — configuration

> Single source of truth for your AI-powered processes. The menu-bar plugin reads AND writes this
> file (every click rewrites a key here). You can also edit it by hand — it's just markdown.
>
> Copy to `~/.config/spec-driven-agents/config.md` (or set `CP_CONFIG` to another path).

## How it works
- **`llm_local`** — `on`: cheap tasks (classify/summarize/route) run on local **Ollama**;
  `off`: they run on your cloud provider. If Ollama is down, processes fall back to cloud anyway.
- **`accounts`** — comma-separated names of your cloud accounts/profiles (e.g. `personal,work`).
  How each name maps to credentials is up to your runner scripts (env var, config dir, token file).
- **`account_default`** — which account processes use when they don't have an override.
- **`[task:<name>]`** — one section per AI-powered process. Each becomes a menu in the plugin where
  you pick its engine: local / a specific account / default. Keys: `llm_local`, `account`,
  `local_model` (all optional — missing keys inherit the global).
- **`[action:<Name>]`** — one section per on-demand action shown in the "Actions" menu.
  Key: `cmd = <shell command>` (runs in background; make it notify on completion).
- **`logs_dir`** — where your processes write logs and leave `<name>.FAILED` markers on failure.
  Any marker shows as a red badge in the menu until the file is removed (self-healing: your process
  should remove its own marker when it recovers).
- **`backlogs`** — comma-separated directories containing your task files (the format in
  `reference/backlog/task-template.md`), one directory per project. The 📦 box plugin scans them
  recursively and shows blocked / PR-to-review / auto-queue / delivered.

## Config

```config
# --- global defaults ---
llm_local       = on
account_default = main
accounts        = main,work
local_model     = gemma3:4b
logs_dir        = ~/.local/state/spec-driven-agents/logs
backlogs        = ~/backlogs/my-app,~/backlogs/other-app

# --- per-process overrides (the plugin writes these; you can too) ---

[task:daily-digest]
llm_local = off
account = main

[task:inbox-classifier]
llm_local = on

# --- on-demand actions ---

[action:Consolidate-today-digest]
cmd = ~/.local/share/spec-driven-agents/consolidate.sh $(date +%F)
```
