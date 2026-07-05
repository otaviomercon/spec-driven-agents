#!/bin/zsh
# <xbar.title>Box — backlog monitor</xbar.title>
# <xbar.desc>Monitors your spec-driven backlog(s): blocked tasks, PRs to review, auto queue and recent deliveries — straight from task files.</xbar.desc>
#
# The 📦 in the menu bar. Reads every task file (the format in reference/backlog/task-template.md)
# under the directories listed in the config key `backlogs` (comma-separated; scanned recursively),
# groups them by status and shows:
#   🔴 Blocked          → needs YOUR decision
#   🟢 PR to review     → in_progress with a PR attached
#   🔵 Auto queue       → specified + auto: yes (what the scheduled agent will pick up)
#   ✅ Delivered        → done, newest first (delivery time = file mtime)
# Each item opens the task file; tasks with a PR URL get an "Open PR" entry.
#
# Zero tokens, zero LLM — it's a pure projection of your task files. The board never lies because
# it is generated, not maintained.
DIR="${0:A:h}"; LIB="$DIR/lib"
source "$LIB/config.sh"
S=$'\x1f'

typeset -a ROOTS
for r in ${(s:,:)$(cfg_get backlogs)}; do
  r="${r/#\~/$HOME}"; [[ -d "$r" ]] && ROOTS+=("$r")
done
if (( ${#ROOTS} == 0 )); then
  echo "📦"
  echo "---"
  echo "No backlog dirs configured | color=gray"
  echo "Add to your config:  backlogs = ~/backlogs/project-a,~/backlogs/project-b | size=11 color=gray"
  echo "Open config ↗ | bash=/usr/bin/open param1=-e param2=$CFG_FILE terminal=false"
  exit 0
fi

typeset -a B R Q D
for root in "${ROOTS[@]}"; do
  for f in "$root"/**/*.md(N); do
    base="$(basename "$f")"; [[ "$base" == (_index.md|README.md) ]] && continue
    head -20 "$f" | grep -q '^status:' || continue
    fld(){ head -20 "$f" | grep -iE "^$1:" | head -1 | sed -E 's/^[^:]*:[[:space:]]*//;s/[[:space:]]*#.*//;s/^"//;s/"$//'; }
    st="$(fld status)"; auto="$(fld auto)"; prio="$(fld priority)"
    tit="$(fld title)"; [[ -z "$tit" ]] && tit="${base%.md}"
    proj="$(basename "$root")"
    pr="$(grep -oE 'https://github.com/[^ )]*/pull/[0-9]+' "$f" | head -1)"
    mt="$(date -r "$f" '+%s' 2>/dev/null)"
    case "$st" in
      blocked)     B+=("$mt$S🔴$S$proj$S$tit$S$pr$S$f") ;;
      in_progress) R+=("$mt$S🟢$S$proj$S$tit$S$pr$S$f") ;;
      specified)   if [[ "$auto" == (yes|si|sim|true) ]]; then
                     case "$prio" in high|alta) pk=0 ;; medium|media) pk=1 ;; low|baja|baixa) pk=2 ;; *) pk=3 ;; esac
                     Q+=("$pk$S🔵$S$proj$S$tit$S$pr$S$f")
                   fi ;;
      done)        D+=("$mt$S✅$S$proj$S$tit$S$pr$S$f") ;;
    esac
  done
done

# --- menu-bar item: attention items first (blocked + PRs to review) ---
title="📦"
(( ${#B} > 0 )) && title+=" ${#B}🔴"
(( ${#R} > 0 )) && title+=" ${#R}🟢"
(( ${#Q} > 0 )) && title+=" ${#Q}🔵"
echo "$title"
echo "---"

emit(){ # header  mode(r=desc|q=asc)  records...
  local hdr="$1" mode="$2"; shift 2
  local recs=("$@"); (( ${#recs} == 0 )) && return
  if [[ "$mode" == q ]]; then recs=("${(@f)$(printf '%s\n' "${recs[@]}" | sort)}")
  else recs=("${(@f)$(printf '%s\n' "${recs[@]}" | sort -r)}"); fi
  echo "$hdr (${#recs}) | size=11 color=gray"
  local i=0 rec key emoji proj tit pr f
  for rec in "${recs[@]}"; do
    i=$((i+1)); (( i > 6 )) && { echo "… and $(( ${#recs} - 6 )) more | size=11 color=gray"; break; }
    IFS=$S read -r key emoji proj tit pr f <<< "$rec"
    echo "$emoji $proj · $tit | bash=/usr/bin/open param1=$f terminal=false"
    [[ -n "$pr" ]] && echo "-- Open PR ↗ | href=$pr"
  done
  echo "---"
}
emit "🔴 Blocked — needs your decision" r "${B[@]}"
emit "🟢 PR to review" r "${R[@]}"
emit "🔵 Auto queue (agent will pick up)" q "${Q[@]}"
emit "✅ Delivered" r "${D[@]}"

if (( ${#B} + ${#R} + ${#Q} + ${#D} == 0 )); then
  echo "No tasks yet | color=gray"
  echo "Copy reference/backlog/task-template.md into a backlog dir and start specifying by chat | size=11 color=gray"
  echo "---"
fi
echo "Open config ↗ | bash=/usr/bin/open param1=-e param2=$CFG_FILE terminal=false"
echo "Refresh | refresh=true"
