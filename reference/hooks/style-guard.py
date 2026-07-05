#!/usr/bin/env python3
"""Stop hook — blocks the agent's reply if it matches forbidden style patterns, and asks it to rewrite.

Generalized from a production hook that enforces a Spanish dialect (blocks Argentinian "voseo" forms
and demands neutral Latin American Spanish). Yours can enforce anything expressible as words/regexes:
a dialect, banned filler words, placeholder text ("lorem ipsum", "TODO: fill in"), leaked internal
codenames, etc.

Configuration (a plain text file, one entry per line):
  - path from $STYLE_GUARD_WORDS (default ~/.config/spec-driven-agents/style-guard.txt)
  - lines starting with `re:` are treated as regexes; anything else as a literal word
    (matched with word boundaries, case-insensitive)
  - a line starting with `msg:` sets the rewrite instruction shown to the model
  - `#` comments and blank lines are ignored

Defensive design (same rules as every hook here):
  - FAIL-OPEN: any error → exit 0 (never bricks the session)
  - anti-loop: if the turn was already blocked once (stop_hook_active), don't block again
  - anti-false-positives: code blocks (``` ```), inline code (`...`) and quoted text ("..." '...'
    «...») are stripped before scanning — that's where forbidden forms get legitimately *mentioned*.
"""
import sys, json, re, os

CFG = os.path.expanduser(os.environ.get(
    "STYLE_GUARD_WORDS", "~/.config/spec-driven-agents/style-guard.txt"))


def load_config():
    words, regexes, msg = [], [], None
    try:
        with open(CFG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("msg:"):
                    msg = line[4:].strip()
                elif line.startswith("re:"):
                    regexes.append(line[3:].strip())
                else:
                    words.append(line)
    except Exception:
        pass
    return words, regexes, msg


def last_assistant_text(transcript_path):
    text = ""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                msg = ev.get("message") if isinstance(ev, dict) else None
                role = (msg or {}).get("role") or ev.get("role")
                if role != "assistant":
                    continue
                content = (msg or {}).get("content", ev.get("content"))
                parts = []
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "text":
                            parts.append(b.get("text", ""))
                if parts:
                    text = "\n".join(parts)   # keep the LAST assistant message
    except Exception:
        return ""
    return text


def strip_exempt(s):
    s = re.sub(r"```.*?```", " ", s, flags=re.S)      # code blocks
    s = re.sub(r"`[^`]*`", " ", s)                     # inline code
    s = re.sub(r"\"[^\"]*\"", " ", s)                  # double quotes
    s = re.sub(r"«[^»]*»", " ", s)                     # angle quotes
    s = re.sub(r"'[^']*'", " ", s)                     # single quotes
    return s


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("stop_hook_active"):     # anti-loop: already blocked this turn
        return 0
    tp = data.get("transcript_path")
    if not tp:
        return 0
    words, regexes, msg = load_config()
    if not words and not regexes:
        return 0
    txt = strip_exempt(last_assistant_text(tp))
    if not txt:
        return 0
    found = []
    if words:
        rx = re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in words) + r")(?![\w])",
                        re.IGNORECASE)
        found += rx.findall(txt)
    for pat in regexes:
        try:
            found += [m if isinstance(m, str) else m[0] for m in re.findall(pat, txt, re.IGNORECASE)]
        except re.error:
            continue
    if not found:
        return 0
    uniq = sorted(set(str(m).lower() for m in found))
    reason = ("Forbidden style detected in the reply: " + ", ".join(uniq) + ". "
              + (msg or "Rewrite the reply avoiding these forms."))
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
