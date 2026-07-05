#!/usr/bin/env python3
"""Agent-runtime traceability hook (tested with Claude Code hooks; adapt the event names to yours).

Appends ONE clean line per user request and per MUTATING action to a raw per-session log at
$TRACE_DIR/<date>_<session>.md. Never fails loudly (always exit 0).

Clean at the source (so the nightly digest has signal, not keystrokes):
 a) does NOT log read-only tools (file reads, greps, searches, monitors...)
 b) does NOT create a file on session start — only on the first real event (request or mutation),
    so empty sessions leave no stubs
 c) keeps the request nearly whole (~500 chars) — the "why" is the most valuable signal
 d) marks the line with ✗ if the tool response carried an error (best effort)

Wire it (Claude Code): settings.json → hooks → UserPromptSubmit + PostToolUse + Stop → this script.
Set TRACE_DIR (default ~/.local/state/spec-driven-agents/trace). Set CP_NO_TRACE=1 in scheduled
runs that shouldn't log themselves.
"""
import sys, json, os, datetime, re

_RO_TOOLS = {
    "Read", "Grep", "Glob", "LS", "NotebookRead", "Monitor",
    "WebFetch", "WebSearch", "TodoWrite",
    "TaskCreate", "TaskUpdate", "TaskGet", "TaskList", "TaskOutput",
    "ToolSearch",
}
_RO_SUBSTR = ("preview_", "read_", "_read", "list_", "_list", "get_", "_get", "search")

# Bash classification by the LEADING VERB of each sub-command (split on &&) — NOT by substring,
# so a path like .../migrations/... never marks a grep as a mutation.
_MUT_VERB = re.compile(
    r"^(?:git\s+(?:commit|push|merge|add|rm|mv|stash|checkout\s+-b|reset|revert|tag|init|clone)\b|"
    r"gh\s+pr\s+(?:create|merge|close|edit)\b|gh\s+release\b|"
    r"npm\s+(?:run\s+)?(?:build|test)\b|npm\s+(?:ci|install|i|publish)\b|yarn\b|pnpm\b|"
    r"mv\b|mkdir\b|rm\b|cp\b|chmod\b|chown\b|touch\b|tee\b|ln\b|sed\s+-i\b)")
_RO_VERB = re.compile(
    r"^(?:cat|ls|grep|rg|egrep|fgrep|find|head|tail|less|more|tree|stat|wc|jq|yq|echo|printf|"
    r"which|type|sed\s+-n|awk|env|date|pwd|whoami|sleep|open|"
    r"git\s+(?:status|log|diff|show|branch|remote|rev-parse|ls-remote|config\s+--get|describe)|"
    r"gh\s+(?:pr\s+(?:view|checks|list|status|diff)|run\s+(?:view|list|watch)|api|auth\s+status|repo\s+view)|"
    r"npm\s+(?:ls|list|view|run\s+lint)|node\s+--check)\b")


def _bash_is_noise(cmd: str) -> bool:
    c = cmd.strip()
    c_nofd = re.sub(r"\d?>>?\s*/dev/null|\d?>&\d", "", c)   # ignore 2>/dev/null, 2>&1 etc.
    segs = []
    for p in c.split("&&"):                                  # only && (| and ; appear inside grep patterns)
        p = p.strip()
        p = re.sub(r"^(?:\w+=\S+\s+)+", "", p)
        p = re.sub(r"^cd\s+(?:'[^']*'|\"[^\"]*\"|\S+)\s*$", "", p)
        if p:
            segs.append(p)
    if not segs:
        return True
    if ">" in c_nofd:                                        # real redirect to a file → mutation
        return False
    if any(_MUT_VERB.match(s) for s in segs):
        return False
    if _RO_VERB.match(segs[0]):
        return True
    return False                                             # unknown verb → keep (don't lose signal)


def _is_noise(tool: str, target: str) -> bool:
    if tool in _RO_TOOLS:
        return True
    low = tool.lower()
    if any(s in low for s in _RO_SUBSTR):
        return True
    if tool == "Bash":
        return _bash_is_noise(target)
    return False


def _has_error(data) -> bool:
    tr = data.get("tool_response")
    try:
        if isinstance(tr, dict):
            if tr.get("is_error") or tr.get("error"):
                return True
            st = tr.get("status") or tr.get("returncode")
            if isinstance(st, int) and st != 0:
                return True
    except Exception:
        pass
    return bool(data.get("is_error"))


def main():
    if os.environ.get("CP_NO_TRACE"):
        return  # scheduled runs don't log themselves (avoids loops)
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    ev = data.get("hook_event_name", "?")
    sid = (data.get("session_id") or "no-session")[:8]
    cwd = data.get("cwd") or os.getcwd()
    proj = os.path.basename(cwd.rstrip("/")) or "global"
    now = datetime.datetime.now()
    day, ts = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
    raw_dir = os.path.expanduser(os.environ.get("TRACE_DIR", "~/.local/state/spec-driven-agents/trace"))
    path = os.path.join(raw_dir, f"{day}_{sid}.md")

    def short(s, n=140):
        s = " ".join(str(s).split())
        return s[:n] + ("…" if len(s) > n else "")

    creates = False
    if ev == "SessionStart":
        return
    elif ev == "UserPromptSubmit":
        line = f"- {ts} 🗣️ request: {short(data.get('prompt', ''), 500)}"
        creates = True
    elif ev == "PostToolUse":
        t = data.get("tool_name", "?")
        ti = data.get("tool_input", {}) or {}
        target = (ti.get("file_path") or ti.get("command") or ti.get("pattern")
                  or ti.get("path") or ti.get("description") or ti.get("url") or "")
        if _is_noise(t, str(target)):
            return
        mark = " ✗" if _has_error(data) else ""
        line = f"- {ts} 🔧 {t}: {short(target)}{mark}"
        creates = True
    elif ev == "Stop":
        if not os.path.exists(path):
            return
        line = f"- {ts} ⏹️ end of turn"
    else:
        return

    new = not os.path.exists(path)
    if new and not creates:
        return
    if new:
        os.makedirs(raw_dir, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(f"# Trace — {proj} — session {sid} — {day}\n")
        f.write(line + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
