#!/bin/zsh
# config.sh — reader for the control-plane config (a markdown file with a ```config block).
# Usage:
#   source config.sh ; cfg_get <key> [task]
#   ./config.sh get <key> [task]
# Resolution: [task:<x>].<key>  ▸  global <key>  ▸  hardcoded default.
# Tolerates a missing file (falls back to defaults). No dependencies beyond awk.

CFG_FILE="${CP_CONFIG:-$HOME/.config/spec-driven-agents/config.md}"

# hardcoded defaults (safety net if the file or key is missing)
typeset -gA _CFG_DEFAULTS=(
  llm_local       off
  account_default main
  accounts        main
  local_model     gemma3:4b
  logs_dir        "$HOME/.local/state/spec-driven-agents/logs"
)

cfg_get() {
  local key="$1" task="$2" val=""
  if [[ -f "$CFG_FILE" ]]; then
    val="$(awk -v key="$key" -v task="$task" '
      BEGIN { inblk=0; sec="_global"; gval=""; tval=""; want="task:" task }
      /^```config[[:space:]]*$/ { inblk=1; next }
      /^```/ { if (inblk) inblk=0; next }
      inblk {
        line=$0
        sub(/[[:space:]]*#.*$/, "", line)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        if (line=="") next
        if (line ~ /^\[.*\]$/) { sec=line; sub(/^\[/,"",sec); sub(/\]$/,"",sec); next }
        eq=index(line,"="); if (eq==0) next
        k=substr(line,1,eq-1); v=substr(line,eq+1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
        if (k!=key) next
        if (sec=="_global") gval=v
        else if (task!="" && sec==want) tval=v
      }
      END { if (tval!="") print tval; else if (gval!="") print gval }
    ' "$CFG_FILE")"
  fi
  [[ -z "$val" ]] && val="${_CFG_DEFAULTS[$key]}"
  print -r -- "$val"
}

# list section names of a given kind, e.g. cfg_sections task → one name per line
cfg_sections() {
  local kind="$1"
  [[ -f "$CFG_FILE" ]] || return 0
  awk -v kind="$kind" '
    /^```config[[:space:]]*$/ { inblk=1; next }
    /^```/ { if (inblk) inblk=0; next }
    inblk && $0 ~ ("^\\[" kind ":") { s=$0; sub("^\\[" kind ":","",s); sub(/\]$/,"",s); print s }
  ' "$CFG_FILE"
}

# CLI only when executed directly (not when sourced).
if [[ "$ZSH_EVAL_CONTEXT" == toplevel ]]; then
  case "$1" in
    get) shift; cfg_get "$@" ;;
    sections) shift; cfg_sections "$@" ;;
    "") : ;;
    *) print -u2 "usage: config.sh get <key> [task] | config.sh sections <kind>"; exit 2 ;;
  esac
fi
