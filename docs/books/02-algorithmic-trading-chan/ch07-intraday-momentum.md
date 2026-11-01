# Livro 2 · Capítulo 7 — Estratégias de momentum intradiário

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 155–168 foi lido. O raspador do calendário de resultados em MATLAB (Quadro 7.1) foi lido, mas não resumido.

Os exemplos são estratégias de ações, futuros e câmbio, com vendas a descoberto, aberturas/fechos diários, calendários de resultados, rebalanceamento de ETFs e livros de ordens; os resultados não incluem custos e cobrem 2004–2012. A maioria não se aplica ao Lost Crypto.

## 1. Resumo do capítulo (pp. 155–168)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Momentum entre pregões tem poucos sinais independentes (Sharpe menor e significância fraca) e sofre após crises; **momentum intradiário mais curto evita ambos os problemas**. Todas as causas de momentum do cap. 6 atuam intradiariamente, exceto retornos de rolagem; uma nova causa é o **acionamento de ordens stop** (rompimentos). | 155–156 |
| C2 | **Estratégia de lacuna na abertura**: comprar se a abertura superar a máxima anterior por uma fração (0,1) do desvio-padrão dos retornos diários dos últimos 90 dias; vender a descoberto se ficar abaixo da mínima anterior pelo mesmo valor; fechar no fim do dia. Futuros FSTX: retorno anual 13%, Sharpe 1,4 (2004–2012); GBPUSD com horários próprios de abertura/fecho: 7,2%, Sharpe 1,3. Hipótese: após período sem negociação (noite/fim de semana), stops são acionados em conjunto e desencadeiam uma cascata. | 156–157 |
| C3 | **Momentum acionado por notícias**: deriva pós-divulgação de resultados (entrar na abertura se o retorno overnight superar meio desvio-padrão em qualquer direção, **sem interpretar a notícia**; sair no fecho): S&P 500, 2011–2012, retorno anual 6,7%, Sharpe 1,5, alavancagem possível de apenas cerca de 4×; manter durante a noite teve retorno médio negativo, indicando que o horizonte da deriva encolheu para intradiário. Outros eventos (mudanças de analistas, fusões/aquisições, cerca de 3% ao ano, mudanças em índices) também mostram esse encurtamento. Nos testes do autor, divulgações macroeconômicas não tiveram efeito significativo em EURUSD; estudo anterior encontrou momentum de GBPUSD em 10 minutos. | 157–163 |
| C4 | **ETFs alavancados** precisam rebalancear perto do fecho na direção da variação do dia, criando momentum. Comprar DRN se o retorno até 15 minutos antes do fecho superar +2%, vender a descoberto se ficar abaixo de −2%: retorno anual 15%, Sharpe 1,8 (out. 2011–out. 2012); efeito maior em ETFs com mais ativos. | 163–164 |
| C5 | **Alta frequência**: desequilíbrio entre volumes de compra/venda prevê variações de preço de curto prazo (relação linear, mais forte em ações de baixo volume). Táticas: juntar-se à melhor oferta de compra (operação de razão), ajustar cotações, iniciar momentum e inverter posição (ordens enganosas), caçar stops junto a suportes/resistências e números redondos, fluxo de ordens (volume com sinal). O autor observa que lucros de HFT vêm de operadores mais lentos e que os tamanhos cotados diminuíram por causa disso. | 164–168 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Momentum por rompimento | ✅ | `donchian_breakout` compra acima da máxima de N barras; é da família de C1/C2 e somente comprada. |
| Lacuna/abertura de sessão | n/a | Cripto negocia 24/7; não há lacuna noturna/de fim de semana. “Abertura diária” (00:00 UTC) é apenas convenção. |
| Intervalos intradiários | ✅ | Há suporte a candles de 1m, 5m, 15m, 1h, 4h e 1d (`Timeframe`). |
| Notícias/eventos, mudanças em índices, rebalanceamento de ETFs | ❌ / n/a | Não há dados de eventos; anúncios de listagem e rebalanceamento não existem no sistema. |
| Livro/fluxo de ordens | ❌ | Só se armazenam candles OHLCV (`market_data/domain/models.py::Candle`: abertura, máxima, mínima, fecho, volume). Sem compra/venda, profundidade ou volume com sinal. |
| Execução de alta frequência | n/a | Fluxo baseado em candles via REST, mínimo de 1 minuto; preenchimento simulado na próxima abertura. Não é uma infraestrutura HFT. |
| Custos em horizontes curtos | ✅ | Taxas e slippage sempre aplicados; modelo usa bps fixos, otimista em 1m. |

## 3. Oportunidades

### O1 — Pesquisa de tendências em horizontes curtos e mais sinais independentes *(livro: C1, p. 155; relacionado ao livro 2, cap. 6 C7)*

* **Problema:** bots de tendência entre pregões fazem poucas operações, reduzindo a confiança estatística (livro 2, cap. 6). O livro propõe períodos de manutenção mais curtos.
* **Proposta:** usar intervalos existentes de 5m/15m/1h nos backtests e apresentar, por intervalo, quantidade de operações completas independentes, custo e significância (livro 2, cap. 1 O1), permitindo observar o compromisso. Não exige nova função além das métricas já propostas; é orientação de pesquisa/interface (“operações completas necessárias”).
* **Risco:** em horizontes curtos, custos e slippage dominam; o modelo fixo em bps é menos realista (ver O2).

### O2 — Slippage dependente do tamanho da ordem e da volatilidade em intervalos curtos *(livro: C5 e cap. 1, pp. 164–167 · adaptação)*

* **Problema:** slippage constante subestima os custos em movimentos rápidos e livros pouco líquidos, justamente onde atua o momentum intradiário; o autor alerta que backtests de comportamento semelhante a HFT são pouco confiáveis (livro 2, cap. 1 C7).
* **Proposta:** modelo opcional de slippage escalado pela volatilidade recente (por exemplo, amplitude do candle) e pelo tamanho da ordem em relação ao volume do candle; manter o modelo fixo como padrão e exibir faixa de sensibilidade de custos (livro 1, cap. 2 O4).
* **Benefício:** backtests de curto prazo mais honestos. **Complexidade:** média. **Riscos:** parâmetros adicionais também podem ser ajustados em excesso; calibrar com slippage realizado registrado (livro 1, cap. 5 O4), não por estimativa arbitrária. **Validação:** testes unitários com valores calculados manualmente e análise de sensibilidade.

### O3 — Indicador de fluxo de ordens por candle com volume agressor *(livro: C5, pp. 167–168 · adaptação; o livro usa dados de ticks)*

* **Problema:** armazenamos apenas OHLCV, mas a ideia de fluxo de ordens do livro (volume com sinal prevê movimentos curtos) exige distinguir compras e vendas.
* **Proposta (verificar antes de desenvolver):** dados de *kline* da corretora costumam incluir volume de compras a mercado por candle (confirmar no adaptador Binance e testnet); armazená-lo numa coluna aditiva e expor indicador “desequilíbrio de fluxo” (volume comprador agressor ÷ volume total) para diagnósticos e, mais tarde, estratégias. É **adaptação nossa**; a evidência do livro refere-se a fluxo por tick em ações/futuros/câmbio.
* **Benefício:** caminho de baixo custo para sinais de microestrutura sem feed do livro de ordens. **Complexidade:** média (migração, mudança no importador, carga retroativa). **Riscos:** agregação em candles perde o momento dentro do candle considerado pelo livro; mais dados armazenados; não há evidência de poder preditivo em cripto. **Validação:** teste de importação com fonte falsa; correlação do indicador com retorno do candle seguinte, apenas como diagnóstico.

### O4 — Considerar ideias de abertura de sessão inaplicáveis; não portar estratégia de lacuna *(livro: C2, pp. 156–157)*

Não existe lacuna de noite/fim de semana no mercado cripto à vista. Um mecanismo parecido poderia ser um rompimento da faixa anterior de N horas/dias, já aproximado por Donchian. Não se propõe trabalho.

### O5 — Momentum baseado em eventos: apenas no backlog *(livro: C3, pp. 157–163)*

Exige eventos legíveis por máquina (listagens, remoções, atualizações de protocolo, divulgações macroeconômicas). Registrar como **B-EVENTS**; hoje não há fonte, e o livro diz que esses efeitos encolheram até o horizonte intradiário.

### Não aplicável

Deriva de resultados empresariais, alterações de índices, rebalanceamento de ETFs alavancados, desequilíbrio entre compra/venda, ajuste de cotações, ignição de momentum, inversão de posição e caça a stops (os dois últimos descrevem comportamentos adversariais contra os quais o sistema deve **se defender**, não imitar; ver nota).

### Nota defensiva (interpretação nossa, não recomendação do livro)

O livro descreve táticas enganosas de ordens (ignição de momentum, inversão de posição e caça a stops). Para um bot que usa ordens a mercado em níveis de stop conhecidos, a lição relevante é que **níveis visíveis de stops e concentrações em números redondos podem ser alvo**. A simulação já executa stops atravessados por uma lacuna na abertura; não se propõe outro controle, mas o registro do slippage realizado (livro 1, cap. 5 O4) mostrará se a execução dos stops é sistematicamente pior que a estimada.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O2 slippage ajustado por volatilidade/tamanho | alta | média | – | média | livro 1, cap. 5 O4 (dados de calibração) |
| 2 | O1 comparação de intervalos temporais | média | – | – | baixa | livro 2, cap. 1 O1 |
| 3 | O3 indicador de volume agressor | baixa (especulativo) | – | – | média | confirmar campos da corretora |
| 4 | O5 eventos | – | – | – | n/a | B-EVENTS |

## 5. Arquivos afetados

`execution/domain/fills.py`, `backtesting/domain/models.py` (opção de slippage), `market_data/domain/models.py`, `orm.py`, importador e adaptadores de corretora (O3, aditivo), formulário/detalhes de backtest no app e testes.

## 6. Plano incremental

1. Registrar slippage realizado (livro 1, cap. 5 O4) para calibrar o modelo.
2. Adicionar modelo opcional de slippage, mantendo o padrão atual.
3. Incluir sugestões de comparação entre intervalos.
4. Verificar disponibilidade de volume agressor; se houver, armazenar e executar o diagnóstico.

## 7. Critérios de aceitação e testes

* Com a nova opção de slippage desligada, o resultado padrão do backtest permanece idêntico bit a bit.
* Testes unitários da nova opção cobrem escala por volatilidade/tamanho e garantem que o slippage nunca favorece a operação.
* Nova coluna de candle é anulável; candles existentes e hashes (`hash_candles`) não mudam, salvo adesão explícita à coluna.
* Ruff, mypy e testes existentes passam.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`), números como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil. A última migração é `0014_backtest_regime`. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| Registro de slippage realizado (pré-requisito do O2) | ❌ | ✅ livro 1, cap. 5: `execution/domain/orders.py` (`realized_slippage_bps`, `latency_ms`), `GET /bots/{id}/execution-quality` (por tipo de ordem: média, mediana e pior slippage, latência) e a aba de execução do bot (`components/bots/bot-execution.tsx`). Falta usar esses números para **calibrar** o modelo do backtest. |
| Slippage do backtest | fixo | fixo: `slipped_price(side, reference_price, slippage_bps)` em `execution/domain/fills.py`, um número por execução (`slippage_bps`, padrão 5). |
| Teto de ordem por volume | ❌ | ✅ `RiskLimits.max_order_pct_of_volume` (livro 1, cap. 5): recusa entrada acima de % do volume médio recente. Cobre o **tamanho**, não o custo. |
| Intervalos de 1m a 1d | ✅ | ✅ (`Timeframe`: 1m, 5m, 15m, 1h, 4h, 1d). |
| Comparação de execuções | ✅ | ✅ `/backtests/compare` e `compare-page.tsx`, com Sharpe, número de operações e as demais colunas lado a lado. |
| Volume agressor | ❌ | ❌ continua: `Candle` tem só `open/high/low/close/volume` (`market_data/domain/models.py`). `ccxt_exchange.py` obtém candles por `fetch_ohlcv`, que devolve seis campos. |

**Achados que moldam o plano:**
* Os parâmetros de um backtest são colunas em `backtest_runs` (a `seed` e o `slippage_bps` são exemplos); um modelo de slippage novo precisa de colunas e de migração.
* A paridade (`trading/application/parity.py`) reexecuta o bot com os limites **e o slippage** do bot. Se o modelo do backtest mudar sem o do bot mudar, a paridade passa a acusar `cost`. A solução é **manter o modelo fixo como padrão** e só aplicar o novo em pesquisa.

### Fase A — Comparar horizontes de tempo (O1) · prioridade 1 · só front-end, sem migração

Objetivo: mostrar, lado a lado, o compromisso entre mais operações independentes e mais custo, sem inventar função nova.

* **A.1 Front-end:** em `backtest-detail-page.tsx`, botão "Comparar em outros intervalos" que, para cada intervalo escolhido (5m, 15m, 1h), cria uma execução **idêntica** à atual trocando só o `timeframe` e abre `/backtests/compare?ids=...`. Antes de criar, checar a cobertura com o que a página de dados de mercado já usa (`useCoverage`, `coverage-notice.tsx`): intervalo sem candles armazenados fica desabilitado com o motivo e o atalho para importar. A criação reaproveita `backtest-prefill.ts` e `POST /backtests`; **nada novo no backend**.
* **A.2 Colunas que valem aqui** em `compare-page.tsx`: número de operações (já existe como `round_trips`), taxas pagas, retorno líquido e **Sharpe**; quando o [cap. 1, Fase A](ch01-backtesting-and-automated-execution.md) existir, a coluna de significância (`t`). Frase fixa: "intervalos curtos fazem mais operações, mas o custo e o slippage dominam; confira a escada de custos de cada execução".
* **A.3 Testes:** `vitest` do montador de configurações (só o `timeframe` muda, tudo o mais é igual) e do bloqueio por falta de cobertura; teste manual a 360 px.
* **Aceite:** nenhuma execução existente muda; criar as comparações é uma ação explícita do operador.

### Fase B — Modelo opcional de slippage por volatilidade e tamanho (O2) · prioridade 2 · migração própria

* **B.1 Domínio:** em `execution/domain/fills.py`, `slippage_bps_for(model, candle, order_notional, base_bps) -> Decimal`. Modelo `fixed` devolve `base_bps` (**comportamento atual, bit a bit**). Modelo `volatility_size`: `base_bps + k_range × amplitude_do_candle_em_bps + k_size × (notional ÷ volume_em_cotação_do_candle) × 10.000`, com `k_range` e `k_size` ≥ 0 dados pela execução; **nunca menor que `base_bps`** (o custo extra só pode piorar). A amplitude é `(high − low) ÷ open`, de dado já armazenado; o volume em cotação é `volume × close` (aproximação a registrar). `slipped_price` passa a receber o número já calculado, de modo que o preenchimento continue puro.
* **B.2 Motor e paridade:** `backtesting/domain/engine.py` chama `slippage_bps_for` com o candle e o notional de cada fill; **o trader e o replay de paridade continuam com `fixed`** neste corte (o paper trader usa `slippage_bps` fixo em `execution/venues/paper.py`); a diferença fica explícita na tela do backtest ("modelo de custo: volatilidade e tamanho; o bot usa custo fixo").
* **B.3 Persistência:** migração `NNNN_slippage_model` (`ALTER TABLE backtest_runs ADD COLUMN slippage_model TEXT NOT NULL DEFAULT 'fixed'`, `slippage_k_range NUMERIC NULL`, `slippage_k_size NUMERIC NULL`; `downgrade` remove), mais `backtesting/domain/models.py` (`BacktestConfig`), `infrastructure/orm.py`, `repository.py`, `presentation/router.py` (`BacktestCreate` e `BacktestOut`), OpenAPI. Execuções antigas ficam `fixed`; o `hash` de candles e o resultado delas não mudam.
* **B.4 Calibração (não é código de negociação):** `GET /bots/{id}/execution-quality` já devolve o slippage realizado por tipo de ordem. No front, a aba de execução ganha uma linha "modelo do backtest previsto × realizado" que **mostra os dois lados**, sem ajustar `k` sozinha: calibrar com o slippage **realizado** (livro 1, cap. 5), nunca por estimativa arbitrária. Os `k` não têm valor padrão, o operador os preenche.
* **B.5 Front-end:** `lib/backtests/form.ts` e `backtest-form-page.tsx`: seletor "Modelo de custo" (padrão "fixo") e, quando for o outro, os dois campos `k` com texto de apoio; `backtests.api.ts` (campos nullish). Em `cost-ladder-card.tsx`, a nota de que a escada só varia taxa e slippage fixos **não** vale quando o modelo é o novo (mostrar a observação). 360 px.
* **B.6 Testes:** `tests/unit/test_slippage_model.py`: `fixed` reproduz exatamente os valores atuais (**regressão bit a bit** nos testes de motor existentes); o novo modelo cresce com amplitude e com tamanho e **nunca fica abaixo do base**; valores conferidos à mão em um candle; compra paga mais, venda recebe menos. `tests/unit/test_backtest_engine.py`: com `fixed`, nada muda. Integração: execução com o modelo novo grava as colunas.
* **Aceite:** com `fixed`, todos os resultados e testes atuais são idênticos; o modelo novo só piora o custo; a tela diz qual modelo foi usado.

### Fase C — Volume do agressor por candle (O3) · **verificar antes de qualquer código**

* **C.0 Verificação (sem implementação):** confirmar, na testnet e na exchange real, se o campo "volume de compras a mercado" do kline está disponível. `fetch_ohlcv` do ccxt devolve só seis valores; o endpoint bruto de klines da Binance traz o volume de compra do agressor, e isso **teria de ser chamado direto** no adaptador (`ccxt_exchange.py`/`binance.py`), o que muda o contrato `Exchange`. Registrar o resultado neste relatório. **Se não estiver disponível de forma confiável, a fase termina aqui.**
* **C.1 Se estiver:** coluna anulável `taker_buy_volume` em `candles` (migração própria), campo opcional em `Candle`, importação e atualizador (`market_data/application/updater.py`) preenchendo-o; **`hash_candles` não muda** para candles sem o campo (acréscimo opt-in), e candles já gravados ficam `NULL`. Carga retroativa é uma decisão à parte (custa chamadas).
* **C.2 Diagnóstico e front:** `analytics/domain/` com `flow_imbalance = volume_comprador_agressor ÷ volume_total`, e correlação com o retorno do **candle seguinte** só como diagnóstico, no mesmo padrão do [cap. 6, Fase A](ch06-interday-momentum.md); nenhum sinal de negociação sai daqui.
* **Aceite do C.0:** um parágrafo no relatório dizendo "disponível" ou "indisponível", com a data e a fonte da verificação.

### Fase D — Eventos (O5): backlog · sem trabalho

Registrar **B-EVENTS**: sem fonte de eventos legíveis por máquina e, segundo o livro, o efeito encolheu até o horizonte intradiário.

### Nota defensiva (interpretação nossa, não recomendação do livro)

Para stops de mercado em níveis conhecidos, o slippage **realizado** de saídas protetoras é o que mostra se a execução é pior que a estimada. Isso é coberto pelo alerta do [cap. 8, Fase D](ch08-risk-management.md); aqui não há trabalho extra.

### Ordem, dependências e estimativa

A é independente e barata; B é a mais cara e só depois de haver slippage realizado suficiente para calibrar; C é uma verificação; D é registro. Estimativa grosseira: A ≈ 1,5 dia (front); B ≈ 4 (2,5 back, 1,5 front); C.0 ≈ 0,5. A única migração é a da Fase B (e a C.1, se a verificação permitir).

### Decisões pendentes (para o operador)

* Fórmula e unidades do modelo (proposta: amplitude em bps e razão notional/volume em bps) e se os `k` têm teto.
* Se o paper trader deve usar o mesmo modelo depois de calibrado (isso mudaria a paridade; proposta: só depois de comparar previsto × realizado por algumas semanas).
* Intervalos oferecidos na comparação (proposta: 5m, 15m, 1h).
* Se vale carregar o histórico do volume agressor (muitas chamadas por par) caso a Fase C.0 seja positiva.

### Fora do escopo (decidido)

Estratégia de lacuna de abertura, deriva pós-resultados, mudanças de índice, ETFs alavancados, ignição de momentum e caça a stops (adversariais), execução de alta frequência e livro de ordens.

### Critérios de aceite gerais

Com o modelo `fixed` (padrão), o resultado de qualquer execução é idêntico ao atual; nenhuma salvaguarda live muda; nenhum `float` no domínio; `make check`, integração com `alembic upgrade head` e `downgrade -1` em banco com dados, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas em 1366 px e 360 px. Os números do livro (7–15% ao ano, Sharpe 1,3–1,8) são de uma amostra de um ano ou de um único mercado, sem custos, e não sustentam afirmação alguma sobre cripto.

## Ressalvas

Os números (retorno anual de 7–15%, Sharpe 1,3–1,8) vêm de amostras de um ano ou de um único mercado, excluem custos e dependem de instrumentos/microestrutura diferentes do mercado cripto à vista. O autor diz que a duração do momentum de notícias continua diminuindo. O capítulo não sustenta afirmação alguma sobre rentabilidade em cripto.
