# A metodologia: você especifica conversando, os agentes executam

Esta é uma forma de trabalhar completa e testada em produção onde o trabalho do humano é o
**julgamento** (decidir o quê e por quê, e especificar bem) e o dos agentes é a **implementação**
(branch, código, verificação, PR, merge, deploy). Hoje roda sobre vários projetos reais.

---

## 1. O ciclo

```
 ideia ──> backlog N1 ──> refinar por chat ──> tarefa com specs (N2) ──> agente executa ──> PR ──> CI
   ↑                                                                                          │
   └────────── rastreabilidade (log automático + digest diário) <── deploy <── auto-merge ────┘
```

Todo o resto deste playbook existe para que esse ciclo seja **barato** (tiers de custo, gates
determinísticos), **seguro** (gates de deploy) e **self-healing** (reconcile, quadros projetados,
marcadores de falha).

## 2. O backlog de dois níveis

Cada projeto tem seu backlog, ao lado do repo (não dentro):

- **Nível 1 — ideias**: um único arquivo. Capturar não tem fricção: título, data, notas. Sem
  compromisso. As ideias são refinadas *no chat* ("vamos pensar nisso") ou descartadas.
- **Nível 2 — tarefas**: um arquivo por tarefa, frontmatter YAML + corpo. Uma tarefa nasce quando uma
  ideia é *aprovada* — e só é executável quando está *especificada*.

Formato do arquivo de tarefa (ver [`reference/backlog/task-template.md`](../../reference/backlog/task-template.md)):

```markdown
---
title: Corrigir cálculo de ROI por moeda
status: specified      # pending_spec | specified | in_progress | done | blocked
priority: medium
specs: complete        # complete | not-needed | pending
auto: no               # yes = o agente agendado pode pegá-la
depends:               # opcional: slugs que precisam estar concluídos antes
repo: ~/Projects/meu-app
---
## O quê (objetivo)
## Por quê
## Specs / critérios de aceitação   ( - [ ] ... )
## Escopo / arquivos prováveis
## Verificação   (como se prova: testes/build/manual)
## Notas de execução   (o agente preenche ao executar)
```

**O quadro é uma projeção.** A vista kanban/quadro é *gerada* a partir do frontmatter das tarefas por
um script determinístico — nunca editada à mão. Fonte de verdade = os arquivos de tarefa. Se um chat
esquecer de regenerar, um job agendado regenera mesmo assim (self-healing).

**Onde mora o backlog?** Em qualquer pasta de arquivos markdown puros sob git. O autor mantém o dele
num vault do [Obsidian](https://obsidian.md) (agradável para navegar, linkar e capturar do celular),
mas nada nesta metodologia depende do Obsidian — é markdown + git de ponta a ponta, e os agentes
leem/escrevem com ferramentas de arquivo comuns.

## 3. Especificar conversando (o ofício do humano)

A régua de qualidade: **uma tarefa está pronta quando um agente conseguiria executá-la sem te
perguntar nada.**

Na prática você conversa com seu agente: *"me ajude a especificar esta ideia até ela ser executável"*.
O agente faz as perguntas que um bom engenheiro faria e escreve o spec no arquivo da tarefa. Você
revisa os critérios de aceitação — esse é o seu contrato. Ambiguidade descoberta durante a execução →
a tarefa fica **bloqueada com uma nota**, nunca é chutada.

Regra dura que mantém o sistema honesto: **antes de implementar qualquer mudança (de qualquer
tamanho), a tarefa dela precisa existir**. Ao implementar, marca-se `in_progress` + cola-se a URL do
PR. Essa URL é o que permite que a maquinaria feche o ciclo sozinha.

## 4. Os agentes executam

Dois modos, mesmas garantias:

- **Sob demanda**: você diz "execute a tarefa X". O agente lê os specs, vai ao repo, parte de um main
  fresco, cria branch, implementa *exatamente* os specs, verifica (lint/tipos/testes/build), abre um
  PR e mergeia com o CI verde.
- **Contínuo (agendado)**: um cron horário por projeto drena a fila de tarefas `specified` +
  `auto: yes` — sem você dar comandos.

**A decisão de design crítica:** o *script* faz git/PR de forma determinística (branch, commit, push,
`gh pr create`); o *agente só escreve código*. O PR sempre é aberto — não depende de o LLM lembrar.
Se algo falha (CI vermelho, ambiguidade), a tarefa é marcada `blocked` e a rodada segue para a
próxima; nada fica reintentando em loop.

**Fechar o ciclo é automático:** um job de *reconcile* (a cada ~15 min, zero tokens — só chama `gh`)
encontra tarefas `in_progress` cujo PR foi mergeado, marca `done`, arquiva e regenera o quadro. Se um
PR conflita com o main, a tarefa vai para `blocked` + você é notificado — conflito precisa da sua
decisão, nunca é auto-resolvido.

## 5. Mergear é livre porque os gates protegem a produção

A rede de segurança **não** é a revisão humana:

1. **Deploy com gate** (o mínimo inegociável): o deploy roda build/testes — se falhar, a produção
   fica na última versão boa (ex.: `buildCommand` do Vercel rodando seus testes).
2. **CI em cada PR**: lint/tipos/testes/build. Auto-merge só no verde.
3. **Migrações seguras**: idempotentes, validadas do zero no CI (banco descartável), mudanças
   destrutivas com gate.
4. **Verificação na mudança**: o agente roda o que se aplica antes de fechar e reporta a saída real.

Se um projeto não tem esses gates, *esse* é o risco a corrigir — não a velocidade do merge.
Templates em [`reference/ci/`](../../reference/ci/).

## 6. Tiers de custo: não gaste tokens de fronteira em trabalho barato

Antes de mandar algo para um modelo de fronteira, coloque-o no tier mais barato que resolva bem:

1. **Sem-LLM (determinístico)**: regex / extensão / lookup de domínio → script puro. 0 tokens.
2. **LLM local (Ollama)**: baixo julgamento e alto volume — classificar, taggear, rotear, resumos
   curtos. Um helper compartilhado (`llm.sh --task <x>`) roteia cada tarefa nomeada para local ou
   nuvem conforme a config; se o daemon local cair, cai para a nuvem sozinho. Os consumidores nunca
   decidem a via.
3. **Modelo de fronteira**: só o julgamento alto — escrever código, decisões, conteúdo fino.

E o padrão que mantém os schedulers de graça: **um gate determinístico antes de qualquer LLM**. O
cron horário primeiro faz grep de tarefas elegíveis; se não há nenhuma, sai. Uma hora ociosa custa um
grep.

Duas lições honestas de produção sobre modelos locais:
- Modelos locais pequenos (~4B) seguem instruções bem **em entradas pequenas e colapsam nas grandes**
  (idioma errado, explicando linha por linha). Divida por projeto/seção, ou deixe-os fora de
  trabalhos longos.
- Deixe a **camada determinística ser dona dos fatos** (digests, quadros, logs) e o LLM só escrever
  prosa por cima. Se o modelo escrever algo fraco, você perde polimento — nunca dados.

## 7. Rastreabilidade de graça

- Um **hook** no runtime do agente anexa uma linha por pedido do usuário e por ação *que muta*
  (escritas, commits, PRs — a exploração somente-leitura é filtrada na origem) a um log cru por
  sessão.
- Um job noturno consolida o dia: um **digest determinístico** (agrupa por projeto/sessão, mantém
  pedidos + mutações + PRs, colapsa edições repetidas — ~50% do ruído removido, 0 tokens) e
  opcionalmente um **resumo executivo em prosa** com o motor que você configurar (local ou nuvem).
- Erros nunca sobrescrevem o arquivo diário (um guard detecta erros de auth/limite no lugar do
  resumo).
- Rodadas com falha deixam um marcador `*.FAILED` → badge vermelho no plano de controle até ser
  resolvido; um catch-up re-consolida qualquer dia anterior que ficou incompleto.

Você sempre consegue responder *"o que aconteceu no dia X, em qual projeto e por quê?"* — sem ter
escrito uma única nota.

## 8. O plano de controle (operar tudo isso sem terminal)

Um item na barra de menu (macOS/SwiftBar) apoiado num arquivo de config:

- **A saúde primeiro**: qualquer processo que falha deixa `<nome>.FAILED` → o ícone vira 🔴N; cada
  problema mostra sua mensagem, link para o log e "marcar resolvido". Self-healing: os marcadores são
  removidos pelo próprio processo ao se recuperar.
- **Motor por processo**: cada processo com IA (digest diário, classificador de inbox, …) pode rodar
  no LLM local, ou na conta A/B do provedor de nuvem, ou seguir o default do sistema — troca-se com
  um clique, escrito no arquivo de config (fonte de verdade única, também editável à mão).
- **Gestão de modelos locais**: ver os modelos do Ollama instalados, quais estão carregados na RAM,
  quem consome qual, ligar/desligar modelos como opções do menu.
- **Ações**: gatilhos sob demanda ("consolidar o digest de hoje agora", "renovar o token") que rodam
  em segundo plano e avisam ao terminar.

Instalação e como conectar seus processos: [`control-plane/README.md`](../../control-plane/README.md).

## 9. Adotando (um caminho realista)

1. **Semana 1 — backlog + specs**: crie o backlog de dois níveis para um projeto. Force o hábito:
   nenhuma mudança sem tarefa; especifique conversando.
2. **Semana 2 — o agente executa sob demanda**: deixe o agente executar tarefas especificadas;
   adicione CI + auto-merge + deploy com gate a esse repo (templates em `reference/ci/`).
3. **Semana 3 — automatize**: adicione o runner agendado + reconcile; instale o plano de controle;
   adicione o hook de rastreabilidade.
4. **Depois**: adicione o tier de LLM local quando tiver uma carga real de alto volume e baixo
   julgamento (um classificador de inbox é o primeiro consumidor clássico).

Pular etapas quebra tudo: agentes executando sem disciplina de specs só produzem lixo rápido.
