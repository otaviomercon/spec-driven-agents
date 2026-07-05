#!/usr/bin/env python3
"""digest.py — deterministic daily digest: raw trace logs → grouped SIGNAL (0 tokens, no LLM).

Toma todos los `$TRACE_DIR/<día>_*.md` y produce un digest de SEÑAL agrupado por
proyecto/sesión: pedidos + mutaciones (Write/Edit, git commit/push, gh pr, mv…), colapsando Edits
repetidos al mismo archivo y descartando el ruido de exploración (Read/grep/cat/Monitor/preview…).

Es la "fuente de hechos" de la consolidación: el LLM (local o Claude) solo escribe prosa encima; si
falla, se pierde la prosa, no el registro. Robusto al raw viejo (ruidoso) y al nuevo (ya limpio).

Usage:  digest.py <YYYY-MM-DD> [--raw-dir DIR]   (default dir: $TRACE_DIR)
Salida: el digest en markdown por stdout; estadística de reducción por stderr.
"""
import sys, os, re, glob

_RO_TOOLS = {"Read", "Grep", "Glob", "LS", "NotebookRead", "Monitor", "WebFetch", "WebSearch",
             "TodoWrite", "TaskCreate", "TaskUpdate", "TaskGet", "TaskList", "TaskOutput", "ToolSearch"}
_RO_SUBSTR = ("preview_", "read_", "_read", "list_", "_list", "get_", "_get", "search")
# Clasificación de Bash por VERBO al inicio de cada sub-comando (NO por substring: evita que
# 'supabase'/'migrate' en una RUTA marquen un grep como mutación).
_MUT_VERB = re.compile(
    r"^(?:git\s+(?:commit|push|merge|add|rm|mv|stash|checkout\s+-b|reset|revert|tag|init|clone)\b|"
    r"gh\s+pr\s+(?:create|merge|close|edit)\b|gh\s+release\b|"
    r"npm\s+(?:run\s+)?(?:build|test)\b|npm\s+(?:ci|install|i|publish)\b|yarn\b|pnpm\b|"
    r"mv\b|mkdir\b|rm\b|cp\b|chmod\b|chown\b|touch\b|tee\b|ln\b|sed\s+-i\b|db:apply\b|npx\s+prisma\b)")
_RO_VERB = re.compile(
    r"^(?:cat|ls|grep|rg|egrep|fgrep|find|head|tail|less|more|tree|stat|wc|jq|yq|echo|printf|"
    r"which|type|sed\s+-n|awk|env|date|pwd|whoami|sleep|open|"
    r"git\s+(?:status|log|diff|show|branch|remote|rev-parse|ls-remote|config\s+--get|describe)|"
    r"gh\s+(?:pr\s+(?:view|checks|list|status|diff)|run\s+(?:view|list|watch)|api|auth\s+status|repo\s+view)|"
    r"npm\s+(?:ls|list|view|run\s+lint)|node\s+--check)\b")
_EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _segments(c):
    # Split SOLO por && (raro dentro de comillas; el `|` y `;` aparecen en patrones grep/regex → no dividir).
    out = []
    for p in c.split("&&"):
        p = p.strip()
        p = re.sub(r"^(?:\w+=\S+\s+)+", "", p)                       # env leading VAR=val
        p = re.sub(r"^cd\s+(?:'[^']*'|\"[^\"]*\"|\S+)\s*$", "", p)    # `cd x` solo → vacío
        if p:
            out.append(p)
    return out

# --- REAL project per item: the raw header carries the session's cwd basename (e.g. "Projects"),
# which lumps everything together → a stage-2 LLM would get one mega-chunk and lose coverage. So the
# project is inferred from the PATHS each item touches; items without a path (requests) attach to the
# NEXT item that has one (a request precedes the work it triggers).
# PROJECTS_ROOT (env) = the directory whose immediate children are your repos. Add your own extra
# patterns here if you keep work outside a single root.
_PROJECTS_ROOT = os.path.basename(
    os.path.expanduser(os.environ.get("PROJECTS_ROOT", "~/Projects")).rstrip("/")) or "Projects"
_P_REPO = re.compile(r"/" + re.escape(_PROJECTS_ROOT) + r"/([A-Za-z0-9._-]+)/")


def detect_proj(text):
    m = _P_REPO.search(text)
    if m:
        return m.group(1)
    return None


def assign_projects(items, default_proj):
    """proyecto por ítem: detectado por path; sin path → el del próximo con path (backfill);
    cola sin path → el del anterior; nada detectado en toda la sesión → default del header."""
    projs = [detect_proj(f"{it[1]} {it[2]}") for it in items]
    nxt = None
    for i in range(len(projs) - 1, -1, -1):          # backfill: pedido hereda el proyecto que sigue
        if projs[i] is None:
            projs[i] = nxt
        else:
            nxt = projs[i]
    prev = None
    for i in range(len(projs)):                       # forward-fill para la cola
        if projs[i] is None:
            projs[i] = prev
        else:
            prev = projs[i]
    return [p if p else default_proj for p in projs]


# líneas del raw
_HDR = re.compile(r"^#\s*Trace\s*—\s*(.+?)\s*—\s*session\s*(\S+)")
_INICIO = re.compile(r"^###\s*start\s+(\d\d:\d\d(?::\d\d)?)\s*—\s*(.+?)\s*\(")
_PEDIDO = re.compile(r"^-\s*(\d\d:\d\d(?::\d\d)?)\s*🗣️\s*request:\s*(.*)$")
_TOOL = re.compile(r"^-\s*(\d\d:\d\d(?::\d\d)?)\s*🔧\s*([^:]+):\s*(.*)$")


def _bash_noise(cmd):
    c = cmd.strip()
    c_nofd = re.sub(r"\d?>>?\s*/dev/null|\d?>&\d", "", c)   # ignora 2>/dev/null, 2>&1, etc.
    segs = _segments(c)
    if not segs:                                 # solo cd/env → sin acción útil
        return True
    if ">" in c_nofd:                            # redirección real a archivo → mutación
        return False
    if any(_MUT_VERB.match(s) for s in segs):    # algún sub-comando (por &&) muta → conservar
        return False
    if _RO_VERB.match(segs[0]):                  # el pipeline ARRANCA con solo-lectura → ruido
        return True
    return False                                 # primer verbo desconocido → conservar


def _is_noise(tool, target):
    tool = tool.strip()
    if tool in _RO_TOOLS:
        return True
    low = tool.lower()
    if any(s in low for s in _RO_SUBSTR):
        return True
    if tool == "Bash":
        return _bash_noise(target)
    return False


def parse_session(path):
    proj, sid = "?", os.path.basename(path).split("_", 1)[-1].replace(".md", "")
    times, items = [], []           # items: (kind, tool, text, err)
    raw_lines = 0
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln.strip():
                continue
            h = _HDR.match(ln)
            if h:
                proj, sid = h.group(1), h.group(2)
                continue
            i = _INICIO.match(ln)
            if i:
                times.append(i.group(1)); proj = i.group(2) if proj == "?" else proj
                continue
            raw_lines += 1
            p = _PEDIDO.match(ln)
            if p:
                times.append(p.group(1))
                txt = p.group(2)
                if "<task-notification>" in txt or "<task-id>" in txt:
                    continue                          # notificación del harness, no un pedido humano
                if len(txt) > 300:                    # pedidos kilométricos (URLs, pegotes) → recorte
                    txt = txt[:300].rstrip() + " …"
                items.append(("pedido", "", txt, False)); continue
            t = _TOOL.match(ln)
            if t:
                times.append(t.group(1))
                tool, target = t.group(2).strip(), t.group(3).strip()
                err = target.endswith("✗")
                target = target[:-1].strip() if err else target
                if _is_noise(tool, target):
                    continue
                kind = "edit" if tool in _EDIT_TOOLS else ("bash" if tool == "Bash" else "tool")
                items.append((kind, tool, target, err))
            # 'fin de turno' y otras → se ignoran
    # colapsar edits consecutivos al mismo archivo
    collapsed = []
    for it in items:
        if collapsed and it[0] == "edit" and collapsed[-1][0] == "edit" and it[2] == collapsed[-1][2]:
            k, tool, text, err, n = (*collapsed[-1], 1) if len(collapsed[-1]) == 4 else collapsed[-1]
            collapsed[-1] = (k, tool, text, err or it[3], n + 1)
        else:
            collapsed.append((*it, 1))
    return proj, sid, times, collapsed, raw_lines


def render_item(it):
    kind, tool, text, err, n = it
    mark = " ⚠️" if err else ""
    mult = f" (×{n})" if n > 1 else ""
    if kind == "pedido":
        return f"- 🗣️ {text}"
    if kind == "edit":
        return f"- ✏️ {tool} `{text}`{mult}{mark}"
    if kind == "bash":
        return f"- ⚙️ `{text}`{mark}"
    return f"- 🔧 {tool}: {text}{mark}"


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: digest.py <YYYY-MM-DD> [--raw-dir DIR]\n"); return 2
    day = sys.argv[1]
    raw_dir = os.path.expanduser(os.environ.get("TRACE_DIR", "~/.local/state/spec-driven-agents/trace"))
    if "--raw-dir" in sys.argv:
        raw_dir = sys.argv[sys.argv.index("--raw-dir") + 1]
    files = sorted(glob.glob(os.path.join(raw_dir, f"{day}_*.md")))
    if not files:
        sys.stderr.write(f"digest: no raw logs for {day}\n"); return 1

    by_proj, raw_total, kept_total = {}, 0, 0
    for f in files:
        proj, sid, times, items, raw_lines = parse_session(f)
        raw_total += raw_lines
        if not items:            # sesión sin señal (stub / solo exploración) → se omite
            continue
        kept_total += len(items)
        rng = f"{times[0][:5]}–{times[-1][:5]}" if times else ""
        # proyecto REAL por ítem (una sesión puede tocar varios proyectos) → un bloque por proyecto
        projs = assign_projects(items, proj)
        per = {}
        for pr, it in zip(projs, items):
            per.setdefault(pr, []).append(it)
        for pr, its in per.items():
            by_proj.setdefault(pr, []).append((sid, rng, its))

    out = [f"# Daily digest (deterministic) — {day}", ""]
    if not by_proj:
        out.append("_(No signal-bearing activity this day.)_")
    for proj in sorted(by_proj):
        out.append(f"## {proj}")
        for sid, rng, items in by_proj[proj]:
            out.append(f"### session `{sid}` ({rng})")
            out += [render_item(it) for it in items]
            out.append("")
    sys.stdout.write("\n".join(out).rstrip() + "\n")
    sys.stderr.write(f"digest: {len(files)} files · {raw_total} raw lines → {kept_total} signal "
                     f"({100 - (kept_total * 100 // max(raw_total, 1))}% noise dropped)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
