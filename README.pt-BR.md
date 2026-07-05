# spec-driven-agents

**🌎 [English](README.md) · [Español](README.es.md) · [Português](README.pt-BR.md)**

> **Você especifica conversando. Os agentes executam.**
> Uma metodologia de trabalho — mais um plano de controle instalável — para tocar seus projetos com
> agentes de IA que implementam tarefas de forma autônoma, enquanto você mantém o julgamento.

## A ideia central

A maioria usa o chat de IA para *escrever código junto*. Esta metodologia inverte isso:

1. **Você usa o chat para pensar e produzir specs** — as ideias são capturadas num backlog leve e
   refinadas até virarem tarefas tão bem especificadas que *um agente consegue executá-las sem te
   perguntar nada*.
2. **Os agentes executam as tarefas** — sob demanda ou agendados (cron). Para cada tarefa: branch →
   implementar → verificar (lint/tipos/testes/build) → PR → CI → auto-merge → deploy com gate. Um
   *reconcile* determinístico fecha o ciclo: quando o PR é mergeado, a tarefa é marcada como concluída
   e arquivada, sozinha.
3. **Um plano de controle opera tudo** — uma UI na barra de menu onde você vê a saúde, escolhe qual
   motor de IA (LLM local / provedor de nuvem / qual conta) roda cada processo, e dispara ações.
   Sem terminal.

O humano decide e especifica. A máquina implementa. Quem protege a produção são **os gates, não a
revisão humana**: CI em cada PR, deploy com gate de build/testes, migrações seguras. Por isso mergear
é livre.

## O que tem neste repo

| Diretório | O que é |
|---|---|
| [`docs/`](docs/pt-BR/metodologia.md) | **O playbook** — a metodologia completa, em 3 idiomas |
| [`control-plane/`](control-plane/README.md) | **Instalável** — dois plugins de barra de menu (macOS/SwiftBar): 🧠 controle de motores (motor de IA por processo, saúde, ações) e 📦 **o box**, monitor vivo do backlog (bloqueadas / PRs para revisar / fila auto / entregues) |
| [`reference/`](reference/) | **Scripts adaptáveis** — hook de rastreabilidade, digestor determinístico de logs, templates de CI/auto-merge, templates de tarefa. Código de referência, não plug-and-play |

## Os pilares (versão curta)

- **Backlog de dois níveis** — Nível 1: ideias cruas (um arquivo). Nível 2: um arquivo por tarefa com
  frontmatter YAML + critérios de aceitação. O quadro é *projetado* a partir das tarefas (nunca o
  contrário).
- **A qualidade do spec é o contrato** — uma tarefa só é executável quando os specs estão completos.
  O agente implementa *exatamente* o que eles dizem; o que for ambíguo → tarefa bloqueada, não chutada.
- **Tiers de custo, forçados por design** — antes de qualquer LLM: (1) um script determinístico
  resolve? 0 tokens. (2) É baixo julgamento e alto volume? → LLM local (Ollama). (3) Só o julgamento
  alto → modelo de fronteira.
- **Gates determinísticos antes de qualquer LLM** — os schedulers primeiro fazem `grep` de trabalho
  elegível; uma hora ociosa custa um grep, zero tokens. O script faz git/PR de forma determinística;
  o agente só escreve código.
- **Rastreabilidade de graça** — um hook registra cada pedido e cada ação que muta; um job noturno
  produz um digest diário limpo (determinístico) + resumo em prosa opcional (LLM). Você sempre consegue
  responder "o que aconteceu no dia X?".
- **Self-healing** — o reconcile fecha as tarefas concluídas; os quadros se regeneram a partir dos
  arquivos fonte; falhas deixam um marcador `*.FAILED` que aparece como badge vermelho no plano de
  controle até ser resolvido.

## Requisitos e escopo honesto

- A metodologia é agnóstica de ferramenta (qualquer CLI agêntico que rode headless — nós usamos
  Claude Code).
- O plano de controle é **só macOS** (SwiftBar + launchd). Os padrões portam para qualquer lugar;
  esse código não.
- Os scripts de `reference/` assumem Git + GitHub CLI (`gh`) e saíram de um setup real funcionando —
  adapte caminhos e nomes aos seus.

## Começo rápido

1. Leia a [metodologia](docs/pt-BR/metodologia.md) (15 min).
2. Instale o [plano de controle](control-plane/README.md) e conecte seu primeiro processo.
3. Copie o [template de tarefa](reference/backlog/task-template.md) e escreva seu primeiro spec
   conversando com seu agente: *"me ajude a especificar esta ideia até um agente conseguir executá-la
   sem me perguntar nada"*.

## Licença

MIT — ver [LICENSE](LICENSE).
