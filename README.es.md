# spec-driven-agents

**🌎 [English](README.md) · [Español](README.es.md) · [Português](README.pt-BR.md)**

> **Tú especificas conversando. Los agentes ejecutan.**
> Una metodología de trabajo — más un plano de control instalable — para llevar tus proyectos con
> agentes de IA que implementan tareas de forma autónoma, mientras tú conservas el juicio.

## La idea central

La mayoría usa el chat de IA para *escribir código junto a él*. Esta metodología lo invierte:

1. **Usas el chat para pensar y producir specs** — las ideas se capturan en un backlog liviano y se
   refinan hasta ser tareas tan bien especificadas que *un agente puede ejecutarlas sin preguntarte nada*.
2. **Los agentes ejecutan las tareas** — bajo demanda o agendados (cron). Por cada tarea: rama →
   implementar → verificar (lint/tipos/tests/build) → PR → CI → auto-merge → deploy con gate. Un
   *reconcile* determinista cierra el ciclo: cuando el PR mergea, la tarea se marca terminada y se
   archiva, sola.
3. **Un plano de control lo opera todo** — una UI en la barra de menú donde ves la salud, eliges qué
   motor de IA (LLM local / proveedor de nube / qué cuenta) corre cada proceso, y disparas acciones.
   Sin terminal.

El humano decide y especifica. La máquina implementa. A producción la protegen **los gates, no la
revisión humana**: CI en cada PR, deploy con gate de build/tests, migraciones seguras. Por eso mergear
es libre.

## Qué hay en este repo

| Directorio | Qué es |
|---|---|
| [`docs/`](docs/es/metodologia.md) | **El playbook** — la metodología completa, en 3 idiomas |
| [`control-plane/`](control-plane/README.md) | **Instalable** — dos plugins de barra de menú (macOS/SwiftBar): 🧠 control de motores (motor de IA por proceso, salud, acciones) y 📦 **el box**, monitor vivo del backlog (bloqueadas / PRs por revisar / cola auto / entregadas) |
| [`reference/`](reference/) | **Scripts adaptables** — hook de trazabilidad, digestor determinista de logs, templates de CI/auto-merge, plantillas de tarea. Código de referencia, no plug-and-play |

## Los pilares (versión corta)

- **Backlog de dos niveles** — Nivel 1: ideas crudas (un archivo). Nivel 2: un archivo por tarea con
  frontmatter YAML + criterios de aceptación. El tablero se *proyecta* desde las tareas (nunca al revés).
- **La calidad del spec es el contrato** — una tarea es ejecutable solo cuando sus specs están completas.
  El agente implementa *exactamente* lo que dicen; lo ambiguo → tarea bloqueada, no adivinada.
- **Tiers de costo, forzados por diseño** — antes de cualquier LLM: (1) ¿lo resuelve un script
  determinista? 0 tokens. (2) ¿Es bajo juicio y alto volumen? → LLM local (Ollama). (3) Solo el juicio
  alto → modelo de frontera.
- **Gates deterministas antes de cualquier LLM** — los schedulers primero hacen `grep` de trabajo
  elegible; una hora ociosa cuesta un grep, cero tokens. El script hace git/PR de forma determinista;
  el agente solo escribe código.
- **Trazabilidad gratis** — un hook registra cada pedido y cada acción que muta; un job nocturno produce
  un digest diario limpio (determinista) + resumen en prosa opcional (LLM). Siempre puedes responder
  "¿qué pasó el día X?".
- **Self-healing** — el reconcile cierra las tareas terminadas; los tableros se regeneran desde los
  archivos fuente; los fallos dejan un marcador `*.FAILED` que aparece como badge rojo en el plano de
  control hasta resolverse.

## Requisitos y alcance honesto

- La metodología es agnóstica de herramienta (cualquier CLI agéntico que corra headless — nosotros
  usamos Claude Code).
- El plano de control es **solo macOS** (SwiftBar + launchd). Los patrones portan a cualquier lado;
  ese código no.
- Los scripts de `reference/` asumen Git + GitHub CLI (`gh`) y salieron de un setup real funcionando —
  adapta rutas y nombres a los tuyos.

## Arranque rápido

1. Lee la [metodología](docs/es/metodologia.md) (15 min).
2. Instala el [plano de control](control-plane/README.md) y conecta tu primer proceso.
3. Copia la [plantilla de tarea](reference/backlog/task-template.md) y escribe tu primer spec
   conversando con tu agente: *"ayúdame a especificar esta idea hasta que un agente pueda ejecutarla
   sin preguntarme nada"*.

## Licencia

MIT — ver [LICENSE](LICENSE).
