# hooks/ — guardrails as code for your agent

Hooks are the layer that makes rules **mechanical instead of hopeful**. A rule that lives only in a
prompt ("never push to main", "always answer in neutral Spanish") depends on the model remembering
it; a rule enforced by a hook fires on every event, deterministically, even if the model forgets.

These are written for [Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks) but the
pattern (small fail-open scripts on runtime events) ports to any agent runtime that exposes events.

| Hook | Event | What it enforces |
|---|---|---|
| [`guard-no-push-main.py`](guard-no-push-main.py) | `PreToolUse` (Bash) | **Branch + PR discipline**: blocks `git push` to main/master on established repos (allows the very first push of a fresh repo). The methodology's "always via branch + PR" made mechanical. |
| [`style-guard.py`](style-guard.py) | `Stop` | **Response style**: blocks the agent's reply if it matches forbidden patterns you define (wrong dialect, banned words, placeholder text…) and asks it to rewrite. Configurable wordlist, ignores code blocks and quotes. |
| [`../traceability/log-hook.py`](../traceability/log-hook.py) | `UserPromptSubmit` + `PostToolUse` + `Stop` | **Traceability**: one clean line per request / mutating action. |

## Design rules every hook here follows

1. **Fail-open** — any internal error → exit 0 without blocking. A buggy hook must never brick a session.
2. **Anti-loop** — a Stop hook that already blocked once this turn doesn't block again.
3. **No false positives over correctness** — e.g. the style guard skips code blocks and quoted text;
   the push guard matches full refs (never `feature/main-menu`), decides by leading verb, and allows
   a repo's first push.
4. **Zero personal state** — everything configurable lives in files you own (env vars / wordlists),
   nothing hardcoded.

## Wiring (Claude Code)

Merge [`settings.example.json`](settings.example.json) into your `~/.claude/settings.json`. Summary:

```json
{
  "hooks": {
    "PreToolUse":       [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "python3 /path/to/guard-no-push-main.py" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 /path/to/log-hook.py" }] }],
    "PostToolUse":      [{ "hooks": [{ "type": "command", "command": "python3 /path/to/log-hook.py", "async": true }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "python3 /path/to/log-hook.py" }] },
                         { "hooks": [{ "type": "command", "command": "python3 /path/to/style-guard.py" }] }]
  }
}
```
