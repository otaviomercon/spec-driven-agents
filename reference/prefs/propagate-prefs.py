#!/usr/bin/env python3
"""propagate-prefs.py — seed/refresh a canonical preferences block in every repo's agent config file.

The problem it solves: you have cross-project working rules for your agent (language, workflow,
UI conventions…). Pasting them into each repo's CLAUDE.md / AGENTS.md works — until you improve
them and the copies drift. This script makes ONE file the source of truth and stamps it into every
repo, between markers, with a version tag:

    <!-- prefs:start v=2026-07-05.1 -->
    ...your canonical block...
    <!-- prefs:end -->

Per-repo lines are preserved: anything between `<!-- prefs:local -->` and the end marker is kept
across updates (put repo-specific values there, e.g. the project's language).

Usage:
    propagate-prefs.py <canonical-block.md> <repo1> [repo2 ...]
    propagate-prefs.py <canonical-block.md> --scan ~/Projects        # every git repo under a root

The canonical file's FIRST line must be the start marker (with the version). The target file is
CLAUDE.md at the repo root (created if missing; AGENTS.md is used if it exists and CLAUDE.md
doesn't). Repos already at the same version are skipped. Prints a per-repo summary; exits 0.
"""
import sys, os, re, glob

START = re.compile(r"<!--\s*prefs:start\s+v=([^\s>]+)\s*-->")
END = "<!-- prefs:end -->"
LOCAL = "<!-- prefs:local -->"


def load_canonical(path):
    text = open(path, encoding="utf-8").read().strip()
    m = START.search(text.splitlines()[0])
    if not m:
        sys.exit("canonical file must start with '<!-- prefs:start v=... -->'")
    if END not in text:
        text += "\n" + END
    return text, m.group(1)


def target_file(repo):
    cl = os.path.join(repo, "CLAUDE.md")
    ag = os.path.join(repo, "AGENTS.md")
    if os.path.exists(cl):
        return cl
    if os.path.exists(ag):
        return ag
    return cl  # create CLAUDE.md


def upsert(repo, canonical, version):
    tf = target_file(repo)
    existing = open(tf, encoding="utf-8").read() if os.path.exists(tf) else ""
    m = START.search(existing)
    if m and m.group(1) == version:
        return f"= {os.path.basename(repo)}: already at v{version}"
    # preserve per-repo local lines
    local = ""
    if m:
        block = existing[m.start():existing.index(END) + len(END)] if END in existing else ""
        if LOCAL in block:
            local = block[block.index(LOCAL):block.rindex(END)].rstrip()
    new_block = canonical
    if local:
        new_block = canonical.replace(END, local + "\n" + END)
    if m and END in existing:
        out = existing[:m.start()] + new_block + existing[existing.index(END) + len(END):]
        action = f"↑ {os.path.basename(repo)}: updated to v{version}"
    elif existing:
        out = existing.rstrip() + "\n\n" + new_block + "\n"
        action = f"+ {os.path.basename(repo)}: block appended (v{version})"
    else:
        out = new_block + "\n"
        action = f"+ {os.path.basename(repo)}: {os.path.basename(tf)} created (v{version})"
    open(tf, "w", encoding="utf-8").write(out)
    return action


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    canonical, version = load_canonical(sys.argv[1])
    repos = []
    if sys.argv[2] == "--scan":
        root = os.path.expanduser(sys.argv[3])
        repos = [os.path.dirname(g) for g in glob.glob(os.path.join(root, "*", ".git"))]
    else:
        repos = [os.path.expanduser(r) for r in sys.argv[2:]]
    for r in sorted(repos):
        if not os.path.isdir(r):
            print(f"✗ {r}: not a directory"); continue
        try:
            print(upsert(r, canonical, version))
        except Exception as e:
            print(f"✗ {os.path.basename(r)}: {e}")


if __name__ == "__main__":
    main()
