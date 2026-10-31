# Livro 1 · Capítulo 2 — À procura de ideias

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **apenas análise**; nada implementado. Diagnóstico revisado contra o código em 2026-10-31 (ver §2.1 para o que mudou em relação à versão anterior deste relatório).

## 1. Resumo do capítulo (pp. 9–29)

O capítulo é um conjunto de **triagens rápidas** a aplicar a uma estratégia candidata antes de fazer o backtest.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Ideias são abundantes (artigos, blogs, fóruns); a maioria das prontas não sobrevive a um backtest cuidadoso (pararam de funcionar, só funcionam em small caps, ignoram custos). Uma ideia básica muitas vezes pode ser modificada até ficar lucrativa; a parte proprietária é a variação. | Onde achar estratégias e quanto desconfiar. | 9–11 |
| C2 | Ajustar a estratégia a *você*: horário de trabalho, habilidade de programação, capital, objetivo (renda vs. ganho de longo prazo). O período de posse determina a regularidade da renda. | Estratégia que o próprio dono não consegue operar. | 12–17 |
| C3 | O crescimento máximo no longo prazo vem do **índice de Sharpe** máximo (com alavancagem suficiente), não do buy-and-hold; um Sharpe maior permite mais alavancagem (detalhes adiados para o Cap. 6). | Julgar estratégias pelo retorno bruto. | 17, 19 |
| C4 | Comparar com um **benchmark**: para long-only, o índice de mercado; para dollar-neutral, uma taxa livre de risco. `Information Ratio = média(retornos em excesso) / desvio-padrão(retornos em excesso)`, `Excesso = carteira − benchmark`. O Sharpe é o caso especial com a taxa livre de risco; usa-se Sharpe pela comparabilidade. | Retorno sem contexto e sem consistência. | 18–19 |
| C5 | Regras práticas: poucas operações por ano → Sharpe baixo; drawdown maior que ~10% ou mais longo que ~4 meses → improvável um Sharpe alto; **Sharpe < 1 não serve isoladamente**; lucrativa quase todo mês → Sharpe anualizado tipicamente > 2; quase todo dia → > 3. | Triagem rápida com informação limitada. | 20–21 |
| C6 | **Drawdown** = patrimônio atual − máximo acumulado (a *high watermark*); drawdown máximo = maior queda de pico a vale, em % da watermark; **duração máxima do drawdown** = maior tempo para se recuperar; os dois normalmente não coincidem. Comparar com a própria tolerância. | Estratégia que você não consegue segurar psicologicamente. | 21–22 |
| C7 | **Custos de transação** = comissões + spread compra-venda (custo de liquidez) + impacto de mercado + slippage (atraso entre o gatilho e a execução). Ordens limitadas evitam o spread, mas custam operações perdidas. Estimativa de custo ≈ metade do spread médio (+ comissão) se o tamanho da ordem for pequeno. Exemplo: uma reversão à média com Bollinger de 5 minutos no ES vai de Sharpe ≈ 3 para ≈ −3 após 1 bp de custo. | Vantagens de alta frequência que somem após os custos. | 22–23 |
| C8 | **Viés de sobrevivência**: dados sem os papéis deslistados/falidos inflam os resultados, especialmente para ideias de "comprar barato"; pedir dados point-in-time. | Backtests inflados. | 24 |
| C9 | **Desempenho ao longo do tempo**: períodos antigos parecem melhores (menos concorrência, spreads maiores, mais distorção de sobrevivência); julgar pelos anos mais recentes. **Mudanças de regime** quebram a estacionariedade, então mais dados não são automaticamente mais robustos. | Confiar em uma amostra longa e heterogênea. | 24–25 |
| C10 | **Viés de data-snooping**: muitos parâmetros/regras → ajuste a acidentes; difícil de evitar mesmo com um ou dois parâmetros. Modelos simples duram. O quadro lateral de IA lista as condições dele para confiar em modelos: lógica sólida, poucos parâmetros, linear, simples, toda a otimização numa **janela móvel de lookback** com demonstração fora da amostra contínua. Dados financeiros independentes são mais escassos do que parecem (dados tick têm correlação serial). | Overfitting. | 25–27 |
| C11 | **Capacidade/nicho**: preferir estratégias pequenas demais para instituições. | Concorrência de grandes players. | 27 |

Não está neste capítulo: como calcular na prática o Sharpe anualizado ou o drawdown (Cap. 3, Exemplos 3.4–3.7). Chan não dá orientação sobre cripto; os pontos de cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C4 benchmark | ⚠️ parcial | `buy_and_hold_return_pct` existe (`api/src/modules/analytics/domain/metrics.py`) e aparece como dica no card "Retorno" (`app/src/components/shared/metrics/metrics-grid.tsx`) e como coluna na varredura e na comparação. É só uma comparação de retorno final: sem série de retornos em excesso, sem information ratio. |
| C3/C4/C5 Sharpe | ❌ | Sem Sharpe/Sortino/volatilidade/retorno anualizado em `Metrics`. A convenção de anualização **já foi decidida** no [Cap. 3, O1](ch03-backtesting.md): `N_T = 365 × 24h / duração do candle` (8.760 para 1h, 365 para 1d), taxa livre de risco 0 por padrão. |
| C5 triagem | ❌ | Nenhuma regra prática é aplicada ou exibida; o usuário vê só números soltos. |
| C6 drawdown | ⚠️ | `max_drawdown_pct` existe (pico a vale, % da watermark, bate com a definição do livro). **A duração não é calculada**, nem se o drawdown ainda está aberto no fim, nem a série underwater. O gráfico de capital (`app/src/lib/shared/equity-chart-rows.ts`) faz *downsample* pegando 1 a cada N pontos acima de 1.000 pontos, o que **pode pular o vale** e mostrar uma queda menor que o `max_drawdown_pct` do card. |
| C7 custos | ⚠️ | `fee_rate` fixo + `slippage_bps` fixo, mesmo código no backtest e no paper (`api/src/modules/execution/domain/fills.py`). O stop-loss aplica slippage, o take-profit não (`backtesting/domain/engine.py`). **A varredura não varia custos**: `create_sweep` só substitui `strategy_params` (`replace(base, strategy_params=params)` em `backtesting/application/service.py`), então hoje não há como medir sensibilidade a custo sem criar backtests à mão. Sem custo de equilíbrio, sem impacto dependente do tamanho; só ordens a mercado no backtester. |
| C8 sobrevivência | ⚠️ | Pares cripto também podem ser deslistados; a lista de símbolos é escolhida à mão, então um universo de "sobreviventes" é provável. Sem tratamento de deslistagem. Não se aplica a backtest de um único par, mas é relevante ao comparar pares (`/backtests/compare`). |
| C9 ao longo do tempo | ⚠️ | Uma divisão cronológica treino/teste (`backtesting/domain/segments.py`, campo `segments` com `train`/`test`). Sem detalhamento por ano/trimestre, sem janelas móveis, sem rotulagem de regime. |
| C10 snooping | ⚠️ | As estratégias têm 2–4 parâmetros (bom). A varredura **já registra** `grid`, `run_count` e `skipped` e já ranqueia pelo retorno de teste quando `test_fraction` é informado, com um aviso (`backtesting/presentation/router.py`, `_sweep_out`). Os problemas reais são outros: (a) ranquear e escolher pelo retorno de teste transforma o teste em dado de seleção, ele deixa de ser fora da amostra; (b) a tela não mostra o número de tentativas junto do melhor resultado; (c) não há contagem de tentativas **entre** varreduras e backtests avulsos sobre os mesmos dados (backlog A1). |
| C2 ajuste ao operador | ✅ | Bots baseados em timeframe, automação, worker; documentado nos documentos de arquitetura. |
| C11 nicho | n/a | O capital é pequeno por desenho; nenhum modelo de capacidade é necessário agora. |

### 2.1 Correções em relação à versão anterior deste relatório

* **Contagem de tentativas:** a versão anterior dizia que os sweeps não tinham contagem. Têm (`run_count`, `skipped`); o que falta é exibi-la ao lado do vencedor e contar entre sweeps. O6 foi reescrito.
* **Convenção de anualização:** não está mais pendente; foi decidida no Cap. 3. O1 deixa de depender de decisão futura.
* **Sensibilidade a custos:** verificado que a varredura **não** permite variar `fee_rate`/`slippage_bps`. O4 precisa de código novo.
* **`Metrics` é compartilhado:** o mesmo `compute_metrics` alimenta `GET /bots/{id}/performance` (`bots/application/service.py`, a partir dos snapshots). Tudo que for adicionado em O1/O2 aparece também para bots, e os snapshots de bot podem ter buracos (bot pausado, worker parado), o que o cálculo precisa tratar.
* **Bug de rótulo encontrado no app:** a coluna "Retorno (treino)" da tela de varredura (`app/src/components/backtests/sweep-page.tsx`) mostra `total_return_pct`, que é o **período inteiro** (treino + teste), não o treino. A API não expõe o retorno de treino em `SweepRunOut`.

## 3. Oportunidades

Convenções que valem para todos os itens abaixo:

* **Compatibilidade:** `metrics` e `segments` são JSONB em `backtest_runs` (`backtesting/infrastructure/orm.py`) e execuções antigas não têm os campos novos. Todo campo novo em `MetricsOut` (`analytics/presentation/schemas.py`) deve ser `X | None = None`; no app, `metricsSchema` (`app/src/lib/shared/analytics.ts`) usa `.nullish()` para eles e a UI mostra "—" (n/a). Sem migração para recalcular execuções antigas.
* **Domínio em `Decimal`:** raízes com `Decimal.sqrt()` sob um `localcontext()` com precisão explícita; nada de `float` no domínio. No app, `Number.parseFloat` só para desenhar gráficos, como já é feito.
* **Contrato:** cada mudança de API atualiza `api/docs/openapi.json`, regenera `app/src/lib/shared/api/api.d.ts` (`npm run api:types`) e roda `npm run check:consistency`.
* **Linguagem na UI:** toda métrica nova mostra o tamanho da amostra e nunca aparece como promessa de resultado; o aviso "Histórico simulado — não garante resultado futuro." continua.

### O1 — Sharpe, Sortino, volatilidade, retorno anualizado e information ratio *(livro: C3–C5, pp. 17–21 · anualização: Cap. 3, O1 · cripto é adaptação nossa)*

* **Problema:** não dá para aplicar as próprias regras de triagem do livro (Sharpe < 1, comparação com benchmark) nem comparar estratégias em termos ajustados ao risco.
* **Back-end:**
  * Novo módulo puro `api/src/modules/analytics/domain/risk_ratios.py` com funções sobre a lista de retornos periódicos `r_i = E_i / E_{i-1} − 1` da curva de patrimônio:
    * `annualization_factor(bar: timedelta) -> Decimal` = `365 × 86400 / bar.total_seconds()`.
    * `sharpe(returns, n_t, risk_free=0)` = `√N_T × média / desvio-padrão amostral`; `None` se houver menos de `MIN_RETURNS` (sugestão: 30) ou desvio zero.
    * `sortino(returns, n_t)` com desvio só dos retornos abaixo de 0 (semidesvio sobre **todos** os períodos, não só os negativos); `None` se não houver retorno negativo.
    * `annualized_volatility_pct`, `annualized_return_pct` (geométrico: `(E_final/E_inicial)^(N_T/n) − 1`).
    * `information_ratio(returns, benchmark_returns, n_t)` com `benchmark_returns` = retorno close-a-close do próprio par (o buy-and-hold do livro para long-only).
  * `compute_metrics` ganha dois argumentos opcionais: `bar: timedelta | None` e `benchmark_prices: Sequence[Decimal] | None` (alinhado com `equity_curve`). O backtest passa `config.timeframe.delta` e os `close` dos candles; o bot passa `bot.config.timeframe.delta` e `snapshot.price`.
  * **Buracos:** se o intervalo entre dois pontos da curva for maior que `bar`, o retorno daquele intervalo é descartado e contado em `return_gaps` (acontece com bots pausados; nos backtests, só se houver buraco nos candles, ver Cap. 3).
  * **Tempo no mercado:** `exposure_pct` = % de barras com posição aberta. O motor (`backtesting/domain/engine.py`) já conhece `quantity` a cada candle; acrescentar `bars_in_market: int` a `BacktestOutcome`. Para bots, `snapshot.quantity > 0`. Sem isso, Sharpe de uma curva que fica parada em caixa engana (o Cap. 3 pede o mesmo).
  * Campos novos em `Metrics`/`MetricsOut`: `sharpe_ratio`, `sortino_ratio`, `information_ratio`, `annualized_return_pct`, `annualized_volatility_pct`, `exposure_pct`, `return_periods` (tamanho da amostra), `return_gaps`, `annualization_factor`.
  * `SweepRunOut` ganha `sharpe_ratio` e `test_sharpe_ratio`.
* **Front-end:**
  * `metricsSchema`: os campos novos com `nullableDecimalSchema.nullish()` / `z.number().nullish()`.
  * `MetricsGrid`: novos `StatTile` "Sharpe (anual.)" com dica "N retornos · exposição X%", "Sortino", "Volatilidade anual", "Information ratio vs. comprar e segurar". Em telas pequenas a grade já quebra em 2 colunas; manter a ordem: resultado → risco → operações.
  * `compare-page.tsx` e `sweep-page.tsx`: coluna "Sharpe" (ordenável com `compareDecimal`) e, na varredura com teste, "Sharpe (teste)".
  * Tooltip curto explicando o fator de anualização ("365 dias × 24h; cripto negocia todo dia").
* **Complexidade:** baixa–média. **Riscos:** Sharpe sobre poucos retornos, autocorrelacionados ou majoritariamente planos engana; um Sharpe alto numa amostra curta não é evidência. Por isso `return_periods` e `exposure_pct` sempre aparecem junto.
* **Validação:** testes em `api/tests/unit/test_risk_ratios.py`: série calculada à mão; reproduzir o Exemplo 3.4 do livro (Sharpe 0,7893 do buy-and-hold de IGE com N_T = 252) para provar a fórmula; multiplicar os retornos por k não muda o Sharpe; variância zero → `None`, nunca infinito; um buraco é descartado e contado. No app, teste de `metricsSchema` aceitando um payload antigo (sem os campos) e um novo.

### O2 — Duração do drawdown, drawdown em aberto e curva underwater *(livro: C6, p. 21)*

* **Problema:** só a profundidade é reportada; o livro trata a duração como igualmente importante para saber se o operador aguenta.
* **Back-end:**
  * Em `metrics.py`, trocar `max_drawdown_pct` por uma função `drawdown_stats(equity_curve)` que devolve, numa só passada: `max_drawdown_pct` (mesmo valor de hoje), `max_drawdown_duration_seconds` e `max_drawdown_duration_bars` (do pico até voltar à watermark), `max_drawdown_peak_at`, `max_drawdown_trough_at`, `current_drawdown_pct` e `drawdown_open: bool`.
  * Se a série termina abaixo da watermark, a duração em aberto conta até o último ponto e `drawdown_open = true` (não é "recuperado").
  * A curva underwater **não** precisa de endpoint novo: é derivável no app a partir de `GET /backtests/{id}/equity` e `GET /bots/{id}/equity`.
* **Front-end:**
  * `equity-chart-rows.ts`: nova função pura `underwaterRows(points)` = `(E − max_acumulado) / max_acumulado × 100`, calculada **antes** do downsample.
  * Corrigir o downsample para preservar extremos: em cada bloco de N pontos, manter o ponto de menor e o de maior capital (min/max por bucket) em vez de 1 a cada N. Assim o vale do gráfico bate com o card de drawdown.
  * Na página do backtest e na aba de desempenho do bot, um segundo gráfico pequeno "Abaixo do pico" (área negativa) sob a curva de capital, com o mesmo eixo X.
  * `MetricsGrid`: o tile "Drawdown máximo" ganha dica "durou X dias (de A a B)"; se `drawdown_open`, um selo "em aberto" e o texto "ainda não recuperado".
* **Complexidade:** baixa. **Risco:** a duração depende da resolução da curva (fechamento do candle); dizer isso na dica.
* **Validação:** testes unitários com: série sem queda (duração 0), uma queda recuperada, duas quedas em que a mais funda não é a mais longa (o livro diz que normalmente não coincidem), série que nunca se recupera. No app, `equity-chart-rows.test.ts` cobre `underwaterRows` e garante que o mínimo sobrevive ao downsample.

### O3 — Triagem rápida no estilo do livro *(livro: C5, pp. 20–21 · adaptação para funcionalidade de produto)*

* **Problema:** o livro dá regras simples para descartar ideias cedo; hoje o usuário precisa saber interpretá-las sozinho.
* **Front-end (sem mudança de API, depende de O1/O2):**
  * Função pura `screeningFlags(metrics, run)` em `app/src/lib/backtests/screening.ts` que devolve uma lista de avisos com nível (`info`/`warning`), por exemplo: Sharpe < 1; drawdown > 10%; drawdown mais longo que ~4 meses; poucas operações completas por ano (`round_trips` / anos do período); exposição baixa; retorno abaixo de comprar e segurar; retorno de teste muito pior que o de treino.
  * Limiares em constantes nomeadas no mesmo arquivo, com comentário citando Chan pp. 20–21 e dizendo que **não foram calibrados para cripto**.
  * Componente `ScreeningPanel` na página do backtest, logo abaixo do aviso de histórico: lista curta de alertas com o título "Triagem rápida (regras práticas de Chan, não leis)". Sem alertas, uma linha neutra "Nenhum sinal de alerta nas regras práticas", nunca "aprovado".
* **Complexidade:** baixa. **Risco:** ser lido como selo de qualidade; o texto deve deixar claro que é só uma peneira. **Validação:** testes de unidade de `screeningFlags` para cada regra e para métricas antigas (campos `null` não geram alerta nem erro).

### O4 — Sensibilidade a custos e custo de equilíbrio *(livro: C7, pp. 22–23 · backlog A8)*

* **Problema:** uma premissa fixa de custo pode esconder uma estratégia que morre com custos ligeiramente maiores, exatamente o exemplo do ES do livro.
* **Back-end:**
  * Campo opcional em `BacktestCreate`/`BacktestConfig`: `cost_ladder: bool = false`.
  * No worker (`BacktestExecutor._execute`), quando ligado, reexecutar `run_backtest` para multiplicadores fixos do custo configurado, por exemplo `0×, 0,5×, 1×, 1,5×, 2×, 3×` aplicados a `fee_rate` e `slippage_bps`. **Não** reaproveitar sinais: a estratégia recebe a quantidade em carteira e o tamanho da compra depende do caixa, então reexecutar o motor inteiro é o único jeito correto. O custo é ~6× o tempo de CPU; com o limite de 200.000 candles isso cabe, mas a validação deve recusar `cost_ladder` acima de um limite menor (ex.: 50.000 candles) para não travar o worker.
  * Resultado salvo numa nova coluna JSONB `cost_ladder` (migração Alembic `0008_backtest_cost_ladder.py`): por nível, `multiplier`, `fee_rate`, `slippage_bps`, `net_pnl`, `total_return_pct`, `sharpe_ratio`, `round_trips`.
  * `break_even_multiplier`: interpolação linear entre os dois níveis onde `net_pnl` troca de sinal; `null` se não trocar na grade (e dizer "acima de 3×" ou "lucro nem com custo zero").
  * `BacktestOut` ganha `cost_ladder: CostLadderOut | None`.
* **Front-end:**
  * No formulário (`backtest-form-page.tsx` e `lib/backtests/form.ts`), um switch "Testar sensibilidade a custos (mais lento)" na seção de taxas.
  * Na página do backtest, um card "Sensibilidade a custos": tabela por nível (custo total em bps por lado, retorno, Sharpe) com a linha atual destacada, e uma frase grande: "Deixa de dar lucro com custos ~1,8× maiores que os simulados (≈ 27 bps por lado)". Se o ponto de equilíbrio for menor que 1,5×, alerta amarelo.
* **Complexidade:** média. **Riscos:** só muda os custos, não o realismo do fill (impacto de mercado, fila de ordens limitadas). Dizer isso no card.
* **Validação:** teste com uma estratégia projetada para ser marginal que deve inverter o sinal num custo conhecido; teste de que o nível 1× é idêntico à execução principal; teste de API para o limite de candles.

### O5 — Desempenho por subperíodo *(livro: C9, pp. 24–25)*

* **Problema:** um resultado bom no total pode vir todo de um ano antigo; o livro manda julgar pelos anos recentes.
* **Back-end:**
  * `backtesting/domain/periods.py`, seguindo o padrão de `segments.py`: corta a curva e as operações por **ano civil** (e por trimestre se o período tiver menos de 2 anos) e chama `compute_metrics` em cada fatia, com `initial_capital` = patrimônio no fim da fatia anterior e buy-and-hold da própria fatia.
  * Nova coluna JSONB `periods` (mesma migração de O4) com a lista `{label, start, end, candles, metrics}`; `BacktestOut.periods: list[PeriodOut] | None`.
  * Fatias com menos de `MIN_SEGMENT_CANDLES` ou menos de `MIN_RETURNS` ficam com as razões `null`, mas aparecem.
* **Front-end:**
  * Card "Por período" na página do backtest: tabela compacta (período, retorno, comprar e segurar, Sharpe, drawdown, operações) com barra de retorno por linha; a última linha destacada como "mais recente".
  * Aviso automático quando o retorno do período mais recente for negativo e o total positivo: "O resultado total vem de períodos antigos".
* **Complexidade:** baixa–média. **Risco:** subamostras pequenas são ruidosas; mostrar o número de candles por linha. **Validação:** série sintética com uma quebra no meio (sobe e depois cai) deve mostrar sinais opostos; soma composta das fatias = retorno total.

### O6 — Tentativas visíveis e teste que não seja usado para escolher *(livro: C10, pp. 25–27 · backlog A1, A7)*

* **Problema:** escolher o melhor de N combinações superestima a qualidade dele. Hoje a varredura já conta as combinações e ranqueia pelo teste, mas: o número de tentativas não aparece junto do vencedor; ranquear pelo teste faz o teste virar dado de seleção; e testes repetidos em várias varreduras sobre os mesmos dados não são somados.
* **Back-end (mínimo, sem estatística nova):**
  * `SweepRunOut` ganha `train_return_pct` (de `segments.train`), além do `total_return_pct` atual.
  * `SweepOut` ganha `trials` (= `run_count + len(skipped)`, as combinações *tentadas*) e `ranked_by` passa a aceitar `train_return_pct` e `train_sharpe_ratio`. **Padrão novo:** quando houver `test_fraction`, ranquear pelo **treino** e mostrar o teste do vencedor como verificação, não como critério. Ranquear pelo teste continua possível por parâmetro de consulta (`?rank_by=test_return_pct`), com nota explicando que isso consome o teste.
  * `GET /backtests/sweeps/{id}` devolve `prior_trials`: quantos backtests concluídos já existem para o mesmo `strategy_type` + `symbol` + `timeframe` com intervalo sobreposto (consulta simples em `backtest_runs`; primeiro passo do registro de tentativas A1).
* **Front-end:**
  * `sweep-page.tsx`: corrigir a coluna "Retorno (treino)" para usar `train_return_pct`; renomear a atual para "Retorno (total)".
  * Cabeçalho da varredura: "Melhor de **N** tentativas (mais **M** anteriores sobre estes dados)". O alerta laranja atual passa a usar esse número.
  * Destacar o vencedor e mostrar, ao lado, se ele **também** foi positivo no teste e se ficou acima de comprar e segurar; se não, alerta "o vencedor do treino não se sustentou fora da amostra".
* **Complexidade:** baixa. **Riscos:** a contagem de `prior_trials` é aproximada (não detecta parâmetros mudados à mão fora de varreduras de forma completa); chamar de "aproximada" na UI. **Validação:** teste de API com `trials`, `prior_trials` e o novo `ranked_by`; teste da tela garantindo que a coluna de treino mostra o valor de treino.

### O7 — Tolerância do operador ligada ao bot *(livro: C6 p. 22 · adaptação)*

* **Proposta:** o operador informa, ao criar um backtest, o drawdown máximo aceitável (profundidade % e duração em dias).
* **Back-end:** campos opcionais `max_drawdown_tolerance_pct` e `max_drawdown_tolerance_days` em `BacktestCreate`/`BacktestConfig` (guardados na configuração da execução); `BacktestOut.tolerance = {exceeded_depth, exceeded_duration}` calculado na leitura a partir de `metrics` (sem coluna nova). Depende de O2.
* **Front-end:** dois campos opcionais no formulário; na página do resultado, alerta vermelho se excedido. Em `prefillFromRun` (`app/src/lib/shared/bot-prefill.ts`), levar a tolerância de profundidade para o `max_drawdown_pct` de risco do bot criado a partir do backtest, que já existe como pausa em tempo de execução (`risk_management/domain/models.py`). Assim a pesquisa e a operação usam o mesmo limite.
* **Complexidade:** baixa. **Risco:** falso conforto se o drawdown do backtest for subestimado (custos, fills); a dica do campo deve dizer que o drawdown real tende a ser maior. **Validação:** teste de API para o sinalizador; teste de `prefillFromRun`.

### O8 — Nota sobre sobrevivência/universo *(livro: C8, p. 24 · adaptação)*

* **Front-end:** em `compare-page.tsx`, quando os backtests comparados tiverem **símbolos diferentes**, mostrar o aviso: "Os pares foram escolhidos hoje; pares deslistados não entram na comparação, o que tende a favorecer o resultado."
* **Back-end:** nada agora. Quando houver importação de muitos pares, registrar data de listagem/deslistagem em `market_data` para permitir universos point-in-time.
* **Complexidade:** muito baixa. Baixa prioridade até existir pesquisa multi-par.

### Não recomendado agora
* **Otimização por janela de lookback (C10, p. 27)** é a disciplina recomendada pelo livro (walk-forward). É uma funcionalidade maior e é melhor planejá-la junto dos livros posteriores sobre validação cruzada; registrada como backlog **B-WALK-FORWARD** (A12 no backlog consolidado).
* **Alavancagem baseada em Sharpe (C3)**: não existe alavancagem.
* **Correções estatísticas formais (PSR/DSR, PBO)**: dependem do registro de tentativas completo; backlog A5/A6.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Esforço back | Esforço front | Depende de |
|---|---|---|---|---|---|---|
| 1 | O6 rótulo de treino + tentativas visíveis | alta | – | baixo | baixo | – |
| 2 | O1 Sharpe/Sortino/IR/exposição | alta | média | baixo–médio | baixo | – |
| 3 | O2 duração do DD + underwater + downsample | média | alta | baixo | baixo–médio | – |
| 4 | O3 triagem rápida | média | média | – | baixo | O1, O2 |
| 5 | O4 sensibilidade a custos | alta | média | médio | baixo–médio | O1 |
| 6 | O5 subperíodos | média | – | baixo–médio | baixo | O1 |
| 7 | O7 tolerância ligada ao bot | baixa | média | baixo | baixo | O2 |
| 8 | O8 aviso de universo | baixa | – | – | muito baixo | – |

O6 sobe para o primeiro lugar porque corrige um rótulo errado que já está na tela e custa pouco.

## 5. Arquivos afetados

**Back-end (`api/`)**
* `src/modules/analytics/domain/metrics.py` (O1, O2), novo `src/modules/analytics/domain/risk_ratios.py` (O1), `src/modules/analytics/presentation/schemas.py` (O1, O2).
* `src/modules/backtesting/domain/engine.py` (`bars_in_market`), `domain/models.py` (`BacktestOutcome`, `BacktestConfig`: `cost_ladder`, tolerâncias), `domain/segments.py` (passar `bar`/preços), novo `domain/periods.py` (O5).
* `src/modules/backtesting/application/service.py` (O1, O4, O5, `prior_trials`), `application/ports.py`, `infrastructure/orm.py` e `infrastructure/repository.py` (colunas `cost_ladder`, `periods`).
* `src/modules/backtesting/presentation/router.py` (`BacktestCreate`, `BacktestOut`, `SweepRunOut`, `SweepOut`, `rank_by`).
* `src/modules/bots/application/service.py` (`performance` passa `bar` e preços dos snapshots).
* `migrations/versions/0008_backtest_cost_ladder.py`, `docs/openapi.json`.
* Testes: novo `tests/unit/test_risk_ratios.py`, `tests/unit/test_backtest_engine.py`, `tests/integration/test_phase1_flow.py` (varredura e campos novos), `tests/integration/test_frontend_api.py`.

**Front-end (`app/`)**
* `src/lib/shared/analytics.ts` (schema), `src/lib/shared/equity-chart-rows.ts` (+ teste) (O2), `src/lib/backtests/backtests.api.ts` (sweep, `cost_ladder`, `periods`), `src/lib/backtests/form.ts` (+ teste), novo `src/lib/backtests/screening.ts` (+ teste), `src/lib/shared/bot-prefill.ts`, `src/lib/shared/api/api.d.ts` (gerado).
* `src/components/shared/metrics/metrics-grid.tsx`, `equity-chart.tsx`, novo `underwater-chart.tsx`.
* `src/components/backtests/backtest-detail-page.tsx` (triagem, custos, períodos, underwater), `sweep-page.tsx`, `compare-page.tsx`, `backtest-form-page.tsx`; `src/components/bots/bot-tabs.tsx` (underwater e métricas novas no desempenho do bot).

## 6. Plano incremental

Cada passo é um PR pequeno, com testes, e pode ir para produção sozinho.

1. **Correção rápida (O6 parte 1):** `train_return_pct` em `SweepRunOut` + coluna corrigida em `sweep-page.tsx` + `trials` no cabeçalho.
2. **Métricas puras (O1, O2):** `risk_ratios.py` e `drawdown_stats` com testes unitários, sem mudar a API.
3. **Expor métricas:** campos opcionais em `Metrics`/`MetricsOut`, `bars_in_market`, ligação no backtest e no bot; OpenAPI + `api:types`; `MetricsGrid` e colunas de Sharpe.
4. **Gráficos (O2):** `underwaterRows`, downsample min/max, gráfico "Abaixo do pico".
5. **Triagem (O3):** `screening.ts` + `ScreeningPanel`.
6. **Ranking pelo treino e `prior_trials` (O6 parte 2).**
7. **Subperíodos (O5)** e **sensibilidade a custos (O4)**, com a migração `0008`.
8. **Tolerância (O7)** e **aviso de universo (O8)**.

## 7. Critérios de aceite e testes

* Métricas existentes e execuções armazenadas inalteradas (apenas campos aditivos); execuções antigas abrem sem erro e mostram "—" nos campos novos, tanto em backtests quanto em `/bots/{id}/performance`.
* `max_drawdown_pct` continua com o mesmo valor depois da troca para `drawdown_stats`.
* Fixtures calculadas à mão para Sharpe, Sortino, information ratio e duração de drawdown (incluindo nunca recuperado); Exemplo 3.4 reproduzido.
* Todos os números continuam `Decimal` no domínio; variância zero ou amostra curta dão `None`, nunca infinito ou erro.
* O vale do gráfico de capital coincide com `max_drawdown_pct` mesmo com mais de 1.000 pontos.
* A coluna "Retorno (treino)" da varredura mostra o retorno de treino; o cabeçalho mostra o número de tentativas.
* O nível 1× da escada de custos é idêntico à execução principal.
* As novas métricas sempre mostram o tamanho da amostra; nenhuma é apresentada como garantia de retornos futuros; a triagem nunca diz "aprovado".
* `npm run lint`, `typecheck`, `test`, `check:consistency` e os testes da API passam.

## Ressalvas
Os limiares de Chan (Sharpe > 1, > 2, > 3; drawdown de 10% / 4 meses) são **regras práticas da experiência dele com ações/futuros**, não leis, e não foram calibrados para cripto, que tem volatilidade bem maior. Usar apenas como padrões iniciais de triagem, em constantes nomeadas e fáceis de mudar. A anualização por 365 dias é adaptação nossa (Cap. 3, O1).
