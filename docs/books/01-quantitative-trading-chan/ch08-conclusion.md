# Livro 1 · Capítulo 8 — Conclusão: traders independentes podem ter sucesso?

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **análise + plano de implementação detalhado (2026-11-01); nada foi implementado**. Este capítulo não traz método novo; o plano do §8 reúne as travas de disciplina dos Caps. 1, 6 e 8 numa especificação só. As páginas restantes (Apêndice A, uma pesquisa sobre MATLAB, a bibliografia e o índice) não foram analisadas.

## 1. Resumo do capítulo (pp. 157–160)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Traders independentes podem ir bem onde grandes fundos falham por causa da **capacidade**: contas pequenas podem usar estratégias que agem como provedores de liquidez de curto prazo e não conseguem absorver bilhões. Grandes fundos precisam de períodos de posse longos, assumem risco de regime, enfrentam concorrência intensa, são empurrados para alavancagem e complexidade (→ snooping) e acabam com posições parecidas (risco de debandada). | 157–159 |
| C2 | Instituições impõem restrições e interferência gerencial (escalonamento forçado após ganhos, liquidação forçada após perdas); cada restrição reduz o ótimo. Um trader independente está livre delas **se for emocionalmente disciplinado**. | 159 |
| C3 | Problema de agência: com dinheiro de terceiros o ganho é grande e a perda é ser demitido, o que estimula a tomada de risco; controles internos podem ser contornados (Kerviel e um segundo exemplo). | 160 |

O capítulo é opinião e anedota; não acrescenta método. É o argumento do autor, não evidência.

## 2. Diagnóstico
* **C1 capacidade:** as contas são pequenas por desenho; o sistema não tem modelo de capacidade, e nenhum é necessário agora. Se os tamanhos das ordens crescerem, o controle é o capítulo 5 O3 (limite de volume).
* **C2 disciplina:** o sistema codifica disciplina por meio de controles auditados, limites no live, aprovação digitando o nome, kill switch e período obrigatório em paper. Falta o material dos Capítulos 1/6 (registrar motivos das intervenções).
* **C3 controles internos:** o operador também é o único usuário, mas o sistema já tem papéis (admin/viewer), log de auditoria e reconciliação. A separação de funções entre "quem altera os limites de risco" e "quem roda os bots" existe apenas como admin vs. viewer.

### 2.1 O que mudou desde a versão anterior deste relatório (verificado no código em 2026-11-01)
* **Capacidade (C1):** o controle que o relatório apontava (limite de ordem pelo volume) **existe**: `RiskLimits.max_order_pct_of_volume` (Cap. 5).
* **Alertas (Cap. 1 O1):** ✅ implementados (alertas no app).
* **Motivo das intervenções (Cap. 1 O3) e trava de edição (Cap. 6 O6): continuam ausentes.** Detalhes verificados:
  * `BotService._command` grava `bot.start_requested`, `bot.pause_requested` e `bot.stop_requested` com payload **`{}`**, e `reset_portfolio` grava `bot.portfolio_reset` também com `{}` (`bots/application/service.py`).
  * `BotService._event` fixa `actor="api"`: **todo comando aparece como feito por "api"**, não pelo usuário. Só `start` recebe o ator (`actor=principal.username`) e o usa na aprovação live.
  * `BotService.update` grava `bot.config_updated` com `{fields, version}`: diz **quais** campos mudaram, não **de quê para quê**, nem por quê.
  * `PATCH /bots/{id}` só aceita editar com o bot **parado** (`Bot.ensure_editable()`); uma edição invalida a aprovação live (`set_live_approval(None)`).
  * O kill switch **já** guarda o motivo (`system.kill_switch_activated/released` e o campo `reason` do estado).
  * No app, só "parar", "resetar" e o fluxo live têm diálogo de confirmação (`components/bots/bot-controls.tsx`); "pausar" e "iniciar" são botões diretos. `ConfirmDialog` (`components/shared/feedback/confirm-dialog.tsx`) **já** suporta motivo (`reasonLabel`, `reasonRequired`, `onConfirm(reason)`), usado pelo kill switch.
* **C3 (separação de funções):** continua só `admin` × `viewer`; os tetos live ficam no ambiente e não são editáveis pela API. Nada a fazer (ver "Fora do escopo").

## 3. Oportunidades
Nenhuma oportunidade **nova** surge deste capítulo. Ele reforça itens anteriores, que o §8 especifica juntos:
* Capítulo 1 O3 (motivos das intervenções) e Capítulo 6 O6 (trava de disciplina em edições de parâmetros).
* Capítulo 6 O7 (visibilidade de exposição), com plano no Cap. 6, Fase B.
* Capítulo 5 O3/O5 (limite de volume) como controle de capacidade: já feito.

## 4–7. Prioridade, arquivos, plano, aceite
Substituídos pelo §8.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01 **sem alterar código**. Tema: **disciplina do operador**. O livro (pp. 108–111, 159) diz que a interferência manual costuma piorar o resultado e que reagir a perdas mudando parâmetros é uma armadilha; o sistema não pode impedir o operador, mas pode **registrar por quê**, **mostrar o que mudou** e **contar quantas vezes ele interveio**. Nada aqui bloqueia uma ação. Convenções do projeto: `Decimal` como string, texto de tela em português do Brasil, sem `__init__.py` vazio, migrações só se necessário (**este plano não precisa de migração**: tudo usa `audit_events`, que já guarda `payload` em JSONB).

### Fase 1 — Motivo e autor nos comandos e nas edições (back-end) · Cap. 1 O3 + Cap. 6 O6

* **1.1 Contrato.** `bots/presentation/router.py`: `ReasonIn(BaseModel)` com `reason: str | None = Field(default=None, max_length=200)`. `pause`, `stop` e `reset-portfolio` passam a aceitar `body: ReasonIn | None = None` e `principal: Principal = Depends(require_auth)`, o mesmo padrão que `start_bot` já usa (`StartIn | None`); chamadas **sem corpo continuam funcionando**. `BotUpdate` ganha `change_reason: str | None = Field(default=None, max_length=200)`, **excluído** do dicionário de mudanças (`model_dump(exclude={"risk", "change_reason"})`).
* **1.2 Autor.** `BotService._event(...)` ganha `actor: str = "api"`; `pause`, `stop`, `reset_portfolio` e `update` recebem `actor` e `reason` e os repassam; o ator passa a ser `principal.username`. Efeito colateral útil: a trilha de auditoria deixa de mostrar "api" para tudo.
* **1.3 Payload.** `_command(bot_id, name, transition, *, reason, actor)` grava `{"reason": reason}` **só quando houver texto** (senão `{}` como hoje). `bot.portfolio_reset` igual. `bot.config_updated` passa a gravar `{"fields": [...], "version": n, "reason": "...", "changes": {campo: {"from": x, "to": y}}}`.
* **1.4 Diferenças da configuração.** Função pura nova `api/src/modules/bots/domain/changes.py`: `config_changes(old: BotConfig, new: BotConfig) -> dict[str, dict[str, Any]]` para `name`, `exchange`, `symbol`, `timeframe`, `strategy_type`, `strategy_params`, `initial_capital`, `fee_rate`, `slippage_bps`, `mode`, `connection_id` e cada chave de `limits_to_dict(risk)` (como `risk.max_position_fraction`); `Decimal` como string; só os campos que mudaram; **nunca** credenciais (a `connection_id` é só um identificador). `strategy_params` entra inteiro (é pequeno).
* **1.5 Testes.** `tests/unit/test_bot_changes.py`: configs iguais → `{}`; só o campo mudado aparece; `Decimal` vira string; chave de risco; parâmetro de estratégia. `tests/integration/test_phase8_discipline.py`: `pause`/`stop`/`reset-portfolio` com e sem motivo (payload `{}` sem motivo, `{"reason": ...}` com motivo); autor igual ao usuário autenticado; `PATCH` grava `changes` e o motivo; motivo com mais de 200 caracteres → 422; os testes antigos continuam passando sem alteração.

### Fase 2 — Contagem de intervenções por bot (back-end)

* **2.1 Eventos que contam:** constante `INTERVENTION_EVENTS = ("bot.pause_requested", "bot.stop_requested", "bot.portfolio_reset", "bot.config_updated")` em `bots/domain/models.py`. "Iniciar" não é interferência. Os eventos do kill switch não têm `bot_id` (são do sistema): voltam num bloco `system` à parte (`system.kill_switch_activated`, `system.kill_switch_released`).
* **2.2 Repositórios.** `AuditRepository` (`audit/models.py`, `audit/repository.py`): novo `list_events_since(bot_id, event_types, since, limit)` (aproveita os índices `ix_audit_events_bot_id_occurred_at` e `ix_audit_events_event_type_occurred_at`) e `count_events(..., since=None)` com parâmetro opcional (o uso atual em `bots/application/live.py` não muda). `PortfolioRepository` (`portfolio/application/ports.py` e a implementação SQL): `equity_context_at(bot_id, at) -> tuple[Decimal, Decimal] | None` devolvendo o patrimônio do último snapshot até `at` e o **pico** de patrimônio até `at`.
* **2.3 Regra pura.** `bots/domain/interventions.py`: `summarize(events, contexts, drawdown_threshold)` devolve contagem total, por tipo, quantas vieram **depois de uma queda** (drawdown no instante ≥ `AFTER_DRAWDOWN_PCT = 5`, valor de partida nosso) e a lista com o drawdown de cada uma (`None` sem snapshot).
* **2.4 Endpoint.** `GET /api/v1/bots/{bot_id}/interventions?days=30` (`1..365`) em `bots/presentation/router.py`:
```
{
  "days": 30, "total": n, "after_drawdown": k, "drawdown_threshold_pct": "5",
  "by_type": {"bot.pause_requested": n, ...},
  "items": [{"at", "type", "actor", "reason", "drawdown_pct"}],   // até 100, mais novas primeiro
  "system": {"kill_switch_activated": n, "kill_switch_released": n}
}
```
  Leitura para qualquer papel. `BotOverviewOut` ganha `interventions_30d: int` (só a contagem, via `count_events(..., since=...)`); fica no painel e na lista.
* **2.5 Testes.** `tests/integration/test_phase8_discipline.py`: criar bot, executar uma sequência de comandos e uma edição, conferir contagens, ordem, motivos, autor e `drawdown_pct = null` sem snapshots; com snapshots semeados, `after_drawdown` correto. Unitário de `summarize` (limiar exato, evento sem contexto).

### Fase 3 — Front-end: motivo nos comandos

* `lib/bots/bots.api.ts`: `pauseBot(id, reason?)`, `stopBot(id, reason?)`, `resetPortfolio(id, reason?)` enviam `{ reason }` **só se houver texto** (o helper `command(id, name, body?)` já aceita corpo). `hooks/bots/use-bots.ts`: `useBotCommand` passa a receber `reason?` nas variáveis da mutação.
* `components/bots/bot-controls.tsx`: novo `DialogKind.Pause`; "Pausar" abre `ConfirmDialog` ("Pausar o bot?", motivo **opcional**, texto de apoio: "interferir costuma piorar o resultado; anote por quê"); "Parar" e "Resetar" ganham `reasonLabel="Motivo (opcional)"` (`reasonRequired` falso). "Iniciar" e o fluxo live não mudam. Aviso no campo: "não escreva senhas nem chaves".
* Testes: `vitest` do corpo enviado (com e sem motivo); conferir o diálogo a 360 px.

### Fase 4 — Front-end: confirmação de edição com diferenças e motivo

* `lib/bots/form.ts`: função pura `describeChanges(bot, values, strategy): FieldChange[]` (`{ field, label, from, to }`, rótulos em português) reaproveitando o mapeamento que o envio já usa; testes em `lib/bots/form.test.ts` (sem mudança → `[]`; parâmetro de estratégia; campos de risco; comparação por texto decimal).
* `components/bots/bot-form-page.tsx` (modo edição, `botId !== null`): ao enviar, abrir `ConfirmDialog` "Confirmar alterações" com a lista de diferenças e: (a) o retorno e o drawdown atuais do bot (os hooks `useOverview`/desempenho já existem); (b) o aviso "alterar parâmetros depois de perdas é a armadilha de representatividade (Cap. 6): teste a mudança num período longo antes"; (c) o link "Rodar backtest com esta configuração" (já existe em `components/bots/bot-execution.tsx`; reaproveitar o pré-preenchimento); (d) se o bot for live, que a aprovação será invalidada; (e) o motivo, **obrigatório na tela** quando o bot já tem ordens (`reasonRequired`), mas **não** obrigatório na API. Envia `change_reason` no `PATCH` (`updateBot` em `lib/bots/bots.api.ts`).
* Testes: `describeChanges` e o corpo do `PATCH`; conferir o diálogo longo a 360 px (a lista de diferenças rola dentro do diálogo).

### Fase 5 — Front-end: onde o operador vê as intervenções

* `lib/bots/bots.api.ts`: `getInterventions(id, days)` e schema; `QueryKey.Bots.interventions(id, days)`; `useInterventions` em `hooks/bots/use-bots.ts` (`Poll.Slow`).
* `components/bots/bot-interventions.tsx` (novo), no resumo do bot: "Intervenções nos últimos 30 dias": total, por tipo (rótulos em `lib/shared/labels.ts`, função `interventionLabel`), "depois de uma queda de pelo menos 5%", e a lista com horário, autor, motivo e drawdown no instante. Estado vazio positivo: "Nenhuma intervenção: o plano está sendo seguido." Esqueleto, erro com nova tentativa.
* Painel: `BotCard` (`components/bots/dashboard.tsx`) ganha uma linha "Intervenções (30 d)" com `interventions_30d`.
* Tipos e rótulos: `check:consistency` continua verde (nenhum enum novo na API; os tipos de evento são strings livres da auditoria).

### Documentos a atualizar na mesma mudança
`api/README.md` (corpo opcional dos comandos, `change_reason`, o endpoint novo), `api/docs/openapi.json` e os tipos do app (`npm run api:types`), `app/docs/06-screens.md` (diálogos e o bloco de intervenções), `docs/books/00-system-baseline.md`, e os §8 dos Caps. 1 e 6 (virarem "Implementação").

### Ordem, dependências e estimativa
Fase 1 → Fase 2 → (Fases 3 e 4 em paralelo) → Fase 5. Estimativa grosseira: back-end 1,5 dia (Fases 1 e 2), front-end 2 dias (Fases 3 a 5). Sem migração.

### Fora do escopo (decidido)
* **Separação de funções (C3):** o operador é o único usuário; `admin` × `viewer` e os tetos live no ambiente já cobrem o que faz sentido. Aprovação por duas pessoas não está planejada.
* **Modelo de capacidade (C1):** só faz sentido se as ordens crescerem; o limite de volume já é o controle.
* **Bloquear** edição ou comando por falta de motivo: o objetivo é dado sobre o próprio comportamento, não atrito. Rever depois de alguns meses de dados.

### Decisões pendentes (para o operador)
* Limiar de "depois de uma queda" (proposta: 5% de drawdown no instante).
* Motivo obrigatório só na tela (proposta) ou também na API.
* Se "iniciar" também deve pedir motivo (proposta: não).
* Quem lê as intervenções (proposta: qualquer papel, como a auditoria).

### Critérios de aceite
Chamadas sem corpo continuam idênticas; a auditoria passa a mostrar o autor real, o motivo e o "de → para" das edições; o endpoint conta e ordena certo e marca drawdown nulo sem snapshot; os diálogos pedem o motivo sem bloquear; nenhuma salvaguarda live enfraquecida; o motivo é texto livre limitado a 200 caracteres e a tela avisa para não escrever segredos; `make check` e integração verdes; `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas conferidas em 1366 px e 360 px.

## Ressalva
A afirmação de que traders independentes têm vantagem sobre instituições é a tese do autor. Não deve ser lida como declaração de que o Lost Crypto será lucrativo.
