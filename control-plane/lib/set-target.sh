#!/bin/zsh
# set-target.sh — sets the ENGINE of a process consistently in one menu action.
# A target combines engine (local LLM vs cloud) + account, writing llm_local + account.
#
# Usage: set-target.sh <scope> <target>
#   <scope>   global | <task>          (a [task:x] section name from the config)
#   <target>  local | <account-name> | default
#
# Semantics (always leaves a clean state):
#   local      → llm_local=on  (account is preserved as the fallback if local goes down)
#   <account>  → llm_local=off + account=<account>   (engine = cloud, that account)
#   default    → removes BOTH task overrides (inherits global)  [task scope only]
set -e
DIR="${0:A:h}"
SET="$DIR/config-set.sh"
source "$DIR/config.sh"
scope="${1:?usage: set-target.sh <scope> <target>}"
target="${2:?missing target: local|<account>|default}"
task=""; [[ "$scope" != global ]] && task="$scope"

set_key() { if [[ -n "$task" ]]; then "$SET" "$1" "$2" "$task"; else "$SET" "$1" "$2"; fi }

ACCOUNTS="$(cfg_get accounts)"
case "$target" in
  local)
    set_key llm_local on ;;
  default)
    [[ -z "$task" ]] && { print -u2 "'default' does not apply to the global scope"; exit 2; }
    set_key llm_local global
    set_key account global ;;
  *)
    [[ ",$ACCOUNTS," == *",$target,"* ]] || { print -u2 "unknown account '$target' (accounts=$ACCOUNTS)"; exit 2; }
    set_key llm_local off
    set_key account "$target" ;;
esac
print -r -- "target[$scope] = $target"
