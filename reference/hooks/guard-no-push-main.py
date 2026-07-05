#!/usr/bin/env python3
"""PreToolUse hook — blocks direct pushes to main/master ("always branch + PR", made mechanical).

The methodology says: every change goes through branch + PR (so CI runs and there is a trace); never
push straight to main. This rule is MECHANICAL (a script can detect it), so it is enforced by a hook
instead of relying on the model remembering it.

Defensive design:
- FAIL-OPEN: any error → exit 0 without blocking (a hook bug must never brick work).
- Bash-only. Only blocks EXPLICIT pushes whose target is main/master (`origin main`,
  `-u origin master`, `origin HEAD:main`, `origin main:main`, `:main`).
- No false positives: main/master must be a COMPLETE ref (never matches `feature/main-menu`).
- Fresh-repo exception: if the repo does not know origin/main|master yet, the FIRST push (which
  creates main) is allowed. When in doubt → treat as established (block).
"""
import sys, json, re, os, subprocess

# git push … origin main|master   (optional flags between 'push' and 'origin')
RX_ORIGIN = re.compile(
    r"\bgit\s+push\b[^|&;\n]*\borigin\s+(?:HEAD:)?(?:main|master)(?![\w./-])", re.IGNORECASE)
# refspec with ':' → HEAD:main, origin main:main, :main …
RX_REFSPEC = re.compile(
    r"\bgit\s+push\b[^|&;\n]*:(?:main|master)(?![\w./-])", re.IGNORECASE)


def repo_dir(cmd, cwd):
    """Repo dir: honors a leading `cd <path> &&`; otherwise the hook's cwd."""
    m = re.match(r"\s*cd\s+(?:'([^']+)'|\"([^\"]+)\"|([^\s&;|]+))\s*&&", cmd)
    if m:
        return os.path.expanduser(m.group(1) or m.group(2) or m.group(3))
    return cwd or "."


def is_fresh_repo(d):
    """True ONLY if the repo is confirmed not to know origin/main|master (first push of a fresh repo).
    Any doubt/error → False (treat as established → block, the common case)."""
    try:
        for ref in ("refs/remotes/origin/main", "refs/remotes/origin/master"):
            r = subprocess.run(["git", "-C", d, "rev-parse", "--verify", "--quiet", ref],
                               capture_output=True, timeout=3)
            if r.returncode == 0:
                return False
        return True
    except Exception:
        return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not isinstance(cmd, str) or "push" not in cmd:
        return 0
    if not (RX_ORIGIN.search(cmd) or RX_REFSPEC.search(cmd)):
        return 0
    if is_fresh_repo(repo_dir(cmd, data.get("cwd"))):
        return 0   # first push of a fresh repo (creates main) → allowed
    reason = (
        "Direct push to main/master blocked by methodology. Every change goes through **branch + PR** "
        "(so CI runs and there is a trace). Create a branch (`git checkout -b <name>`), push it and "
        "open a PR (`gh pr create`); merge on green CI (auto-merge where available). If you truly need "
        "a direct push (exceptional), do it yourself outside the agent."
    )
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
