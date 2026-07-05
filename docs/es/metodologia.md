# La metodología: tú especificas conversando, los agentes ejecutan

Esta es una forma de trabajar completa y probada en producción donde el trabajo del humano es el
**juicio** (decidir qué y por qué, y especificarlo bien) y el de los agentes es la **implementación**
(rama, código, verificación, PR, merge, deploy). Hoy corre sobre varios proyectos reales.

---

## 1. El ciclo

```
 idea ──> backlog N1 ──> refinar por chat ──> tarea con specs (N2) ──> agente ejecuta ──> PR ──> CI
  ↑                                                                                          │
  └────────────── trazabilidad (log automático + digest diario) <── deploy <── auto-merge ───┘
```

Todo lo demás de este playbook existe para que ese ciclo sea **barato** (tiers de costo, gates
deterministas), **seguro** (gates de deploy) y **self-healing** (reconcile, tableros proyectados,
marcadores de fallo).

## 2. El backlog de dos niveles

Cada proyecto tiene su backlog, junto al repo (no adentro):

- **Nivel 1 — ideas**: un solo archivo. Capturar no tiene fricción: título, fecha, notas. Sin
  compromiso. Las ideas se refinan *en el chat* ("pensemos esto") o se descartan.
- **Nivel 2 — tareas**: un archivo por tarea, frontmatter YAML + cuerpo. Una tarea nace cuando una
  idea se *aprueba* — y es ejecutable solo cuando está *especificada*.

Forma del archivo de tarea (ver [`reference/backlog/task-template.md`](../../reference/backlog/task-template.md)):

```markdown
---
title: Corregir cálculo de ROI por moneda
status: specified      # pending_spec | specified | in_progress | done | blocked
priority: medium
specs: complete        # complete | not-needed | pending
auto: no               # yes = el agente agendado puede tomarla
depends:               # opcional: slugs que deben estar terminados antes
repo: ~/Projects/mi-app
---
## Qué (objetivo)
## Por qué
## Specs / criterios de aceptación   ( - [ ] ... )
## Alcance / archivos probables
## Verificación   (cómo se prueba: tests/build/manual)
## Notas de ejecución   (las completa el agente al ejecutar)
```

**El tablero es una proyección.** La vista kanban/tablero se *genera* desde el frontmatter de las
tareas con un script determinista — nunca se edita a mano. Fuente de verdad = los archivos de tarea.
Si un chat olvida regenerarlo, un job agendado lo regenera igual (self-healing).

**¿Dónde vive el backlog?** En cualquier carpeta de archivos markdown planos bajo git. El autor lo
lleva en un vault de [Obsidian](https://obsidian.md) (cómodo para navegar, enlazar y capturar desde el
móvil), pero nada de esta metodología depende de Obsidian — es markdown + git de punta a punta, y los
agentes lo leen/escriben con herramientas de archivos comunes.

## 3. Especificar conversando (el oficio del humano)

La vara de calidad: **una tarea está lista cuando un agente podría ejecutarla sin preguntarte nada.**

En la práctica conversas con tu agente: *"ayúdame a especificar esta idea hasta que sea ejecutable"*.
El agente hace las preguntas que haría un buen ingeniero y escribe el spec en el archivo de la tarea.
Tú revisas los criterios de aceptación — ese es tu contrato. Ambigüedad descubierta durante la
ejecución → la tarea queda **bloqueada con una nota**, nunca se adivina.

Regla dura que mantiene el sistema honesto: **antes de implementar cualquier cambio (de cualquier
tamaño), su tarea debe existir**. Al implementar, se marca `in_progress` + se pega la URL del PR. Esa
URL es lo que permite que la maquinaria te cierre el ciclo sola.

## 4. Los agentes ejecutan

Dos modos, mismas garantías:

- **Bajo demanda**: dices "ejecuta la tarea X". El agente lee las specs, va al repo, parte de un main
  fresco, crea rama, implementa *exactamente* las specs, verifica (lint/tipos/tests/build), abre un PR
  y mergea con el CI en verde.
- **Continuo (agendado)**: un cron horario por proyecto drena la cola de tareas `specified` +
  `auto: yes` — sin que des comandos.

**La decisión de diseño crítica:** el *script* hace git/PR de forma determinista (rama, commit, push,
`gh pr create`); el *agente solo escribe código*. El PR siempre se abre — no depende de que el LLM se
acuerde. Si algo falla (CI rojo, ambigüedad), la tarea se marca `blocked` y la corrida sigue con la
siguiente; nada reintenta en loop.

**Cerrar el ciclo es automático:** un job de *reconcile* (cada ~15 min, cero tokens — solo llama a
`gh`) encuentra tareas `in_progress` cuyo PR mergeó, las marca `done`, las archiva y regenera el
tablero. Si un PR entra en conflicto con main, la tarea pasa a `blocked` + te llega un aviso — un
conflicto necesita tu decisión, nunca se auto-resuelve.

## 5. Mergear es libre porque los gates protegen producción

La red de seguridad **no** es la revisión humana:

1. **Deploy con gate** (el mínimo no negociable): el deploy corre build/tests — si falla, producción
   queda en la última versión buena (ej. `buildCommand` de Vercel corriendo tus tests).
2. **CI en cada PR**: lint/tipos/tests/build. Auto-merge solo en verde.
3. **Migraciones seguras**: idempotentes, validadas desde cero en CI (base de datos descartable),
   cambios destructivos con gate.
4. **Verificación en el cambio**: el agente corre lo que aplique antes de cerrar y reporta la salida
   real.

Si a un proyecto le faltan estos gates, *ese* es el riesgo a arreglar — no la velocidad de merge.
Templates en [`reference/ci/`](../../reference/ci/).

## 6. Tiers de costo: no gastes tokens de frontera en trabajo barato

Antes de mandar algo a un modelo de frontera, ubícalo en el tier más barato que lo resuelva bien:

1. **Sin-LLM (determinista)**: regex / extensión / lookup de dominio → script puro. 0 tokens.
2. **LLM local (Ollama)**: bajo juicio y alto volumen — clasificar, taggear, rutear, resúmenes cortos.
   Un helper compartido (`llm.sh --task <x>`) rutea cada tarea nombrada a local o nube según config;
   si el daemon local está caído, cae a la nube solo. Los consumidores nunca deciden la vía.
3. **Modelo de frontera**: solo el juicio alto — escribir código, decisiones, contenido fino.

Y el patrón que mantiene gratis a los schedulers: **un gate determinista antes de cualquier LLM**. El
cron horario primero hace grep de tareas elegibles; si no hay, sale. Una hora ociosa cuesta un grep.

Dos lecciones honestas de producción sobre modelos locales:
- Los modelos locales chicos (~4B) siguen instrucciones bien **en entradas chicas y colapsan en las
  grandes** (idioma equivocado, explican línea por línea). Trocea por proyecto/sección, o déjalos
  fuera de los trabajos largos.
- Deja que la **capa determinista sea dueña de los hechos** (digests, tableros, logs) y que el LLM
  solo escriba prosa encima. Si el modelo escribe algo flojo, pierdes pulido — nunca datos.

## 7. Trazabilidad gratis

- Un **hook** en el runtime del agente anexa una línea por pedido del usuario y por acción *que muta*
  (escrituras, commits, PRs — la exploración de solo lectura se filtra en el origen) a un log crudo
  por sesión.
- Un job nocturno consolida el día: un **digest determinista** (agrupa por proyecto/sesión, conserva
  pedidos + mutaciones + PRs, colapsa ediciones repetidas — ~50% de ruido eliminado, 0 tokens) y
  opcionalmente un **resumen ejecutivo en prosa** con el motor que configures (local o nube).
- Los errores nunca sobrescriben el archivo diario (un guard detecta errores de auth/límite en lugar
  del resumen).
- Las corridas fallidas dejan un marcador `*.FAILED` → badge rojo en el plano de control hasta
  resolverse; un catch-up re-consolida cualquier día previo que quedó incompleto.

Siempre puedes responder *"¿qué pasó el día X, en qué proyecto y por qué?"* — sin haber escrito una
sola nota.

## 8. El plano de control (operar todo esto sin terminal)

Un ítem en la barra de menú (macOS/SwiftBar) respaldado por un archivo de config:

- **La salud primero**: cualquier proceso que falla deja `<nombre>.FAILED` → el ícono se vuelve 🔴N;
  cada problema muestra su mensaje, link a su log y "marcar resuelto". Self-healing: los marcadores
  los borra el propio proceso al recuperarse.
- **Motor por proceso**: cada proceso con IA (digest diario, clasificador de inbox, …) puede correr
  en el LLM local, o en la cuenta A/B del proveedor de nube, o seguir el default del sistema — se
  cambia con un clic, se escribe en el archivo de config (fuente de verdad única, también editable a
  mano).
- **Gestión de modelos locales**: ver los modelos de Ollama instalados, cuáles están cargados en RAM,
  quién consume cuál, prender/apagar modelos como opciones del menú.
- **Acciones**: disparadores bajo demanda ("consolidar el digest de hoy ahora", "renovar el token")
  que corren en segundo plano y avisan al terminar.

Instalación y cómo conectar tus procesos: [`control-plane/README.md`](../../control-plane/README.md).

## 9. Adoptarlo (un camino realista)

1. **Semana 1 — backlog + specs**: crea el backlog de dos niveles para un proyecto. Fuerza el hábito:
   ningún cambio sin tarea; especifica conversando.
2. **Semana 2 — el agente ejecuta bajo demanda**: deja que el agente ejecute tareas especificadas;
   agrega CI + auto-merge + deploy con gate a ese repo (templates en `reference/ci/`).
3. **Semana 3 — automatiza**: agrega el runner agendado + reconcile; instala el plano de control;
   agrega el hook de trazabilidad.
4. **Después**: agrega el tier de LLM local cuando tengas una carga real de alto volumen y bajo juicio
   (un clasificador de inbox es el primer consumidor clásico).

Si te saltas etapas, se rompe: agentes ejecutando sin disciplina de specs solo producen basura rápida.
