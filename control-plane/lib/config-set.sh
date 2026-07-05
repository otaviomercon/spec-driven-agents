#!/bin/zsh
# config-set.sh — writes a key into the ```config block of the control-plane config file.
# Usage: config-set.sh <key> <value> [task]
#   without [task] → writes the GLOBAL key (before the first [task:...] section).
#   with    [task] → writes the key inside [task:<task>] (creates the section if missing).
#                    special value `global` → REMOVES the task override (inherits global again).
set -e
CFG_FILE="${CP_CONFIG:-$HOME/.config/spec-driven-agents/config.md}"
key="$1"; val="$2"; task="$3"
[[ -z "$key" || -z "$val" ]] && { print -u2 "usage: config-set.sh <key> <value> [task]"; exit 2 }
[[ -f "$CFG_FILE" ]] || { print -u2 "config file not found: $CFG_FILE"; exit 1 }

# --- per-TASK branch: edit/create/delete the key inside [task:<task>] (python: safer) ---
if [[ -n "$task" ]]; then
  CFG_FILE="$CFG_FILE" KEY="$key" VAL="$val" TASK="$task" python3 - <<'PY' || { rc=$?; [[ $rc == 4 ]] && print -u2 "no \`\`\`config block found"; exit $rc }
import os, re, sys, collections
f=os.environ["CFG_FILE"]; key=os.environ["KEY"]; val=os.environ["VAL"]; task=os.environ["TASK"]
lines=open(f).read().split("\n")
b0=b1=None
for i,l in enumerate(lines):
    if re.match(r'^```config\s*$', l): b0=i
    elif b0 is not None and l.startswith('```'): b1=i; break
if b0 is None or b1 is None: sys.exit(4)
sec=f"[task:{task}]"; unset=(val=="global")
inner=lines[b0+1:b1]
pre=[]; sections=collections.OrderedDict(); cur=None
for l in inner:
    if re.match(r'^\s*\[[a-z]+:[^\]]+\]\s*$', l):
        cur=l.strip(); sections.setdefault(cur, [])
    elif cur is None:
        pre.append(l)
    else:
        sections[cur].append(l)
klines=sections.get(sec, [])
def is_key(x):
    t=re.sub(r'\s*#.*$','',x).strip(); return '=' in t and t.split('=',1)[0].strip()==key
klines=[x for x in klines if not is_key(x)]
if not unset: klines.append(f"{key} = {val}")
def has_active(ls): return any(re.sub(r'\s*#.*$','',x).strip() for x in ls)
if has_active(klines): sections[sec]=klines
else: sections.pop(sec, None)
while pre and pre[-1].strip()=="": pre.pop()
out=list(pre)
for name,ls in sections.items():
    out.append(""); out.append(name); out.extend(ls)
lines[b0+1:b1]=out
open(f,"w").write("\n".join(lines))
print(f"[task:{task}] {key} = {val}")
PY
  exit 0
fi

# --- GLOBAL branch ---
tmp="$(mktemp)"
awk -v key="$key" -v val="$val" '
  BEGIN { inblk=0; inglobal=0; done=0 }
  /^```config[[:space:]]*$/ { inblk=1; inglobal=1; print; next }
  /^```/ { if (inblk) { inblk=0; inglobal=0 } print; next }
  {
    if (inblk && $0 ~ /^[[:space:]]*\[.*\]/) inglobal=0
    if (inblk && inglobal && !done) {
      line=$0; t=line; sub(/[[:space:]]*#.*$/,"",t); gsub(/^[[:space:]]+|[[:space:]]+$/,"",t)
      eq=index(t,"=")
      if (eq>0) {
        k=substr(t,1,eq-1); gsub(/^[[:space:]]+|[[:space:]]+$/,"",k)
        if (k==key) {
          cmt=""; if (match($0,/#.*/)) cmt=" " substr($0,RSTART,RLENGTH)
          printf "%-15s = %s%s\n", key, val, cmt
          done=1; next
        }
      }
    }
    print
  }
  END { if (!done) exit 3 }
' "$CFG_FILE" > "$tmp" || { rc=$?; rm -f "$tmp"; [[ $rc == 3 ]] && print -u2 "key $key not found in the global block"; exit $rc }
mv "$tmp" "$CFG_FILE"
print -r -- "$key = $val"
