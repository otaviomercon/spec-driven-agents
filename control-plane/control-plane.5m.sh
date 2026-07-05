#!/bin/zsh
# <xbar.title>AI control plane</xbar.title>
# <xbar.desc>Health, per-process AI engine selection, local model management and on-demand actions — driven by one config file.</xbar.desc>
#
# A generic SwiftBar plugin for operating AI-powered processes without a terminal.
# Everything it renders is DATA-DRIVEN from the config file (CP_CONFIG, default
# ~/.config/spec-driven-agents/config.md):
#   - health:   any file <name>.FAILED in logs_dir shows as a red badge until removed
#   - engines:  every [task:x] section becomes a menu — pick local LLM / a cloud account / default
#   - models:   installed Ollama models, RAM state, unload
#   - actions:  every [action:Name] section (cmd = ...) becomes a clickable action
#
# Add a process = add a [task:x] section. Add an action = add an [action:Name] section. No code edits.
DIR="${0:A:h}"; LIB="$DIR/lib"
source "$LIB/config.sh"
SET="$LIB/config-set.sh"; TGT="$LIB/set-target.sh"
enc(){ python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$1" 2>/dev/null }
# read an EXPLICIT task override (empty if not set in its [task:...])
task_val(){ awk -v k="$1" -v t="$2" 'index($0,"[task:"t"]")==1{f=1;next} f&&/^\[/{f=0}
  f && $0 ~ ("^[[:space:]]*" k "[[:space:]]*=") {v=$0;sub(/.*=[[:space:]]*/,"",v);sub(/[[:space:]]*#.*/,"",v);gsub(/[[:space:]]/,"",v);print v;exit}' "$CFG_FILE"; }
action_val(){ awk -v k="$1" -v t="$2" 'index($0,"[action:"t"]")==1{f=1;next} f&&/^\[/{f=0}
  f && $0 ~ ("^[[:space:]]*" k "[[:space:]]*=") {v=$0;sub(/^[^=]*=[[:space:]]*/,"",v);print v;exit}' "$CFG_FILE"; }

ll="$(cfg_get llm_local)"
acct="$(cfg_get account_default)"
ACCOUNTS=(${(s:,:)$(cfg_get accounts)})
ml="$(cfg_get local_model)"
LOGD="$(cfg_get logs_dir)"; LOGD="${LOGD/#\~/$HOME}"
oll="down"; curl -s --max-time 2 localhost:11434/api/tags >/dev/null 2>&1 && oll="ok"

# --- HEALTH: active problems = <name>.FAILED markers (+ Ollama down while local is on).
typeset -a ERRS
for f in "$LOGD"/*.FAILED(N); do
  bn="$(basename "$f")"; base="${bn:r}"
  ERRS+=("$base"$'\t'"$LOGD/$base.log"$'\t'"$(tail -1 "$f" 2>/dev/null)"$'\t'"$f")
done
[[ "$ll" == on && "$oll" != ok ]] && ERRS+=("ollama"$'\t'""$'\t'"Ollama is down (local LLM is ON) → falls back to cloud"$'\t')
NERR=${#ERRS}

# --- menu-bar item: problems REPLACE the icon ---
if (( NERR > 0 )); then echo "🔴$NERR | color=#cf222e"
else icon="🧠"; [[ "$ll" != on ]] && icon="☁️"; echo "$icon"; fi
echo "---"

# --- health first ---
if (( NERR > 0 )); then
  for e in "${ERRS[@]}"; do
    t="${e%%$'\t'*}"; r="${e#*$'\t'}"; logf="${r%%$'\t'*}"; r="${r#*$'\t'}"; msg="${r%%$'\t'*}"; mark="${r#*$'\t'}"
    echo "🔴 $t: $msg | color=#cf222e"
    [[ -f "$logf" ]] && echo "-- Open log ↗ | bash=/usr/bin/open param1=-e param2=$logf terminal=false"
    [[ -n "$mark" ]] && echo "-- Mark resolved (remove marker) | bash=/bin/rm param1=$mark terminal=false refresh=true"
  done
  echo "---"
else
  echo "✓ All systems healthy | size=11 color=#1a7f37"
  echo "---"
fi

# --- status line ---
if [[ "$ll" == on ]]; then
  [[ "$oll" == ok ]] && echo "🧠 Ollama: ok · system default model: $ml | size=12" \
                     || echo "⚠️ Ollama down → falls back to cloud ($acct) | size=12 color=#cf222e"
else
  echo "☁️ Local LLM: OFF → cloud ($acct) | size=12"
fi
echo "---"

# --- ENGINE PER PROCESS: one menu per [task:x] section in the config ---
echo "AI engine per process | size=11 color=gray"
# system default (global)
geff=local; [[ "$ll" != on ]] && geff="$acct"
echo "System default: $geff"
ck=""; [[ "$geff" == local ]] && ck=" ✓"; echo "-- Local LLM$ck | bash=$TGT param1=global param2=local terminal=false refresh=true"
for a in "${ACCOUNTS[@]}"; do
  ck=""; [[ "$geff" == "$a" ]] && ck=" ✓"
  echo "-- Cloud: $a$ck | bash=$TGT param1=global param2=$a terminal=false refresh=true"
done
# each declared process
for tk in $(cfg_sections task); do
  exl="$(task_val llm_local "$tk")"; exc="$(task_val account "$tk")"
  if [[ "$exl" == on ]]; then eff=local; elif [[ -n "$exc" ]]; then eff="$exc"; else eff=default; fi
  echo "$tk: $eff"
  ck=""; [[ "$eff" == default ]] && ck=" ✓"; echo "-- default (follow system)$ck | bash=$TGT param1=$tk param2=default terminal=false refresh=true"
  ck=""; [[ "$eff" == local ]]   && ck=" ✓"; echo "-- Local LLM$ck | bash=$TGT param1=$tk param2=local terminal=false refresh=true"
  for a in "${ACCOUNTS[@]}"; do
    ck=""; [[ "$eff" == "$a" ]] && ck=" ✓"
    echo "-- Cloud: $a$ck | bash=$TGT param1=$tk param2=$a terminal=false refresh=true"
  done
done
echo "---"

# --- LOCAL MODELS (Ollama): installed, RAM state, unload ---
if [[ "$oll" == ok ]]; then
  echo "Local models (Ollama) | size=11 color=gray"
  typeset -A LOADED
  while IFS=$'\t' read -r nm info; do [[ -n "$nm" ]] && LOADED[$nm]="$info"; done < <(
    curl -s --max-time 2 localhost:11434/api/ps | python3 -c '
import json,sys
for m in json.load(sys.stdin).get("models",[]):
    gb=(m.get("size_vram") or m.get("size") or 0)/1073741824
    until=(m.get("expires_at") or "")[11:16]
    print("%s\t%.1f GB in RAM - unloads ~%s" % (m.get("name",""), gb, until))' 2>/dev/null)
  while IFS=$'\t' read -r nm sz; do
    [[ -n "$nm" ]] || continue
    mark="💤"; [[ -n "${LOADED[$nm]}" ]] && mark="⚡"
    echo "$mark $nm · $sz"
    if [[ -n "${LOADED[$nm]}" ]]; then
      echo "-- ${LOADED[$nm]} | size=10 color=#9a6700"
      echo "-- Unload from RAM now | bash=/usr/bin/curl param1=-s param2=-o param3=/dev/null param4=-d param5={\"model\":\"$nm\",\"keep_alive\":0} param6=http://localhost:11434/api/generate terminal=false refresh=true"
    fi
  done < <(curl -s --max-time 2 localhost:11434/api/tags | python3 -c '
import json,sys
for m in json.load(sys.stdin).get("models",[]):
    print("%s\t%.1f GB" % (m.get("name",""), m.get("size",0)/1073741824))' 2>/dev/null)
  echo "---"
fi

# --- ACTIONS: one entry per [action:Name] section (cmd = ...) ---
ACTIONS=($(cfg_sections action))
if (( ${#ACTIONS} > 0 )); then
  echo "Actions | size=11 color=gray"
  for an in "${ACTIONS[@]}"; do
    cmd="$(action_val cmd "$an")"
    [[ -n "$cmd" ]] || continue
    echo "▶️ ${an//-/ } | bash=/bin/zsh param1=-c param2=\"${cmd//\"/\\\"}\" terminal=false refresh=true"
  done
  echo "---"
fi

# --- shortcuts ---
echo "Open config ↗ | bash=/usr/bin/open param1=-e param2=$CFG_FILE terminal=false"
echo "Refresh | refresh=true"
