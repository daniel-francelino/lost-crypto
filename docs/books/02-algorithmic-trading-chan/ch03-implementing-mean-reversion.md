# Livro 2 · Capítulo 3 — Implementação de estratégias de reversão à média

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 63–85 foi lido.

O autor informa que **nenhum backtest do livro inclui custos de transação** e que alguns usam os mesmos dados para ajustar parâmetros e testar, incorrendo em viés de antecipação (p. 64). A ressalva aplica-se a todos os números abaixo.

## 1. Resumo do capítulo (pp. 63–85)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Não é necessário haver estacionariedade ou cointegração verdadeiras: é possível negociar reversões de curto prazo ou sazonais, saindo antes do próximo equilíbrio. Uma série estacionária com meia-vida de dez anos, por sua vez, não é negociável. | Dependência excessiva de testes estatísticos. | 63 |
| C2 | **Spread, log-spread ou razão?** O spread de preços `y = Σ hᵢyᵢ` fixa a *quantidade de ações*; uma combinação de log-preços fixa os *pesos de capital* e exige rebalanceamento constante (custo adicional). Uma razão só é estacionária se as razões de hedge tiverem a mesma magnitude, mas pode funcionar melhor quando o par não é realmente cointegrado e evita razão de hedge dinâmica. Pares cambiais são razões por natureza. No exemplo GLD/USO, o spread de preços com razão de hedge dinâmica supera o log-spread e a razão (retorno anual/Sharpe: 10,9%/0,59 contra 9%/0,5 e resultado negativo). | Escolha do sinal. | 64–70 |
| C3 | **Estratégia de bandas de Bollinger**: entrar quando o z-score do spread ultrapassa `entryZscore` (abaixo de −entry → posição comprada); sair ao atingir `exitZscore` (< entry; 0 = média; −entry = banda oposta). A janela pode ser livre ou **definida pela meia-vida**. Manter no máximo uma unidade facilita a gestão de capital e risco. GLD/USO: retorno anual de 17,8%, Sharpe 0,96, com entrada em 1 e saída em 0. | Versão prática e limitada da estratégia linear. | 70–72 |
| C4 | **Aumentar a posição em etapas** (várias bandas) parece intuitivo, mas **Schoenberg e Corwin mostram que, dentro da amostra, fazer preço médio nunca é ótimo** quando a probabilidade de queda permanece constante. Exemplo com L₁, L₂ e F: retorno esperado de investir tudo em L₁ é `2(F−L₁)`; em L₂, `2p(F−L₂)`; escalonar dá `(F−L₁)+p(F−L₂)`; a média nunca é máxima. Fora da amostra, pode ajudar quando a volatilidade e, portanto, *p*, variam, além de reduzir impacto de mercado. Reduzir a posição gradualmente ainda pode ser lucrativo se a série não for realmente estacionária. | Se vale a pena aumentar a posição gradualmente. | 72–74 |
| C5 | **Filtro de Kalman como regressão dinâmica**: variável observada `y(t) = x(t)β(t) + ε`; estado oculto `β(t) = β(t−1) + ω`, com transição de estado identidade; equações iterativas (3.7–3.13). Produz simultaneamente uma razão de hedge dinâmica, o *intercepto* (substitui a média móvel) e a variância do erro de previsão `Q(t)` (substitui o desvio-padrão móvel). Os parâmetros δ (0,0001 no exemplo) e `V_e` (0,001) foram escolhidos “com o benefício da retrospectiva”. Exemplo EWA/EWC: retorno anual de 26,2%, Sharpe 2,4, sem custos. Evita efeitos abruptos da janela fixa e da ponderação arbitrária. | Média, spread e razão de hedge adaptativos. | 74–82 |
| C6 | **Filtro de Kalman como modelo de “formação de mercado” para uma série**: média oculta `m(t)` e preço observado `y(t)`; o ruído de observação pode variar com o tamanho da operação (operação maior → mais certeza), semelhante a um preço médio ponderado por volume e tempo. | Estimativa adaptativa de valor justo. | 82–83 |
| C7 | **Erros de dados inflam backtests de reversão à média** (um tick incorreto para cima é “vendido” e depois “recomprado” com lucro fictício), mas *reduzem* resultados de momentum. Spreads amplificam pequenos erros de cotação (erro de US$ 1 num spread de US$ 5 = 20%). O autor relata operações reais perdedoras causadas por um feed da corretora, que desapareceram ao trocar de provedor. Ticks incorretos também podem acionar ordens reais erradas em qualquer estilo. | Qualidade dos dados. | 83–84 |
| C8 | Síntese: séries de preços para quantidade fixa de ações; log-séries para capital fixo; razões para pares cambiais; Kalman ou janela móvel para parâmetros variáveis no tempo; bandas de Bollinger, com aumento gradual da posição como forma prática; atenção a erros nos dados. | – | 85 |

Os instrumentos são ETFs dos EUA e pares cambiais negociados comprados e vendidos. Referências a criptoativos são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Estratégia de bandas de Bollinger/z-score | ❌ | Não existe no catálogo (apenas `ema_crossover` e `donchian_breakout`); não há função auxiliar de desvio-padrão ou z-score em `strategies/domain`. |
| Janela derivada da meia-vida | ❌ | Depende do livro 2, cap. 2 O1. |
| Aumentar/reduzir posição em etapas | ❌ | Uma entrada e uma saída por operação completa (o motor rejeita COMPRA enquanto há posição: `"already in position"` em `engine.py`). O contrato de sinais não representa ordens parciais. |
| Filtro de Kalman/média adaptativa | ❌ | Não existe. |
| Estrutura para spread/razão/pares | n/a | Um ativo por bot e posições compradas. Um símbolo de razão, como ETH/BTC, é um mercado à vista negociável (adaptação nossa), permitindo reversão à média de razões sem posição vendida. |
| Proteção contra erro de dados no backtest | ❌ | Candles armazenados não passam por verificação de integridade (livro 1, cap. 3 O3). |
| Proteção contra erro de dados na operação real | ⚠️ | `max_candle_range_pct` (25% por padrão) rejeita *entradas* com candles suspeitos (`risk_management/domain/models.py`); o trader usa apenas candles fechados. A verificação só considera a amplitude. |
| Custos incluídos no backtest | ✅ | `run_backtest` sempre aplica taxas e slippage, ao contrário dos exemplos do livro. |
| Mesmos dados para ajuste e teste | ⚠️ | Existe divisão treino/teste; estratégias com estado adaptativo (janela do z-score) percorrem todos os dados uma vez, o que é correto se o estado usar apenas candles passados. |

## 3. Oportunidades

### O1 — Estratégia comprada de reversão à média com Bollinger/z-score *(livro: C3, pp. 70–72 · versão comprada para cripto é adaptação nossa)*

* **Problema:** o catálogo não tem estratégia de reversão à média; o livro apresenta esta forma como prática e limitada a uma unidade, facilitando o dimensionamento e a gestão de risco.
* **Proposta:** criar `bollinger_reversion`: comprar quando `z < −entry_z`, calculado sobre fechamentos na janela `lookback`; sair quando `z ≥ −exit_z` (por padrão, na média) ou num stop opcional. Parâmetros: `lookback`, `entry_z`, `exit_z` e níveis de proteção opcionais. Registrar como as estratégias atuais, sem mudar o motor ou contrato de sinais (uma entrada e uma saída).
* **Benefício:** acrescentar uma família de reversão à média compatível com a arquitetura atual; com os diagnósticos do cap. 2, verificar primeiro se a série cripto reverte no intervalo escolhido.
* **Complexidade:** baixa a média (novo arquivo de estratégia, registro, catálogo, formulário de parâmetros no app e testes).
* **Riscos:** por ser comprada, pode capturar uma queda e não obtém ganhos do lado vendido; o autor considera stops inadequados à família, embora as quedas de cripto sejam acentuadas; três parâmetros podem causar sobreajuste; caudas pesadas reduzem a utilidade do z-score; erros de dados inflam especialmente esse backtest (C7). Não lançar sem o trabalho de integridade de dados do livro 1, cap. 3 O3, o teste de truncamento e a análise de sensibilidade a custos.
* **Validação:** teste de truncamento; varredura de custos; divisão treino/teste; série OU sintética em que deve haver lucro e série tendencial em que não deve; sensibilidade dos parâmetros (um pico isolado sugere sobreajuste).

### O2 — Usar a meia-vida como janela padrão para reduzir parâmetros livres *(livro: C3, p. 70; cap. 2 C5)*

Preencher e limitar `lookback` a partir da meia-vida da série, apresentando-o como sugestão que o usuário pode alterar. Depende do cap. 2 O1. Complexidade baixa.

### O3 — Decidir sobre entradas graduais com base em evidências *(livro: C4, pp. 72–74)*

O resultado do livro é que, **dentro da amostra, um único nível de entrada supera o preço médio**, enquanto mudanças de volatilidade no mercado real podem favorecer o escalonamento. O modelo atual de entrada única é, portanto, a referência recomendada pelo livro. **Não** adicionar agora entradas parciais; reconsiderar somente se as varreduras mostrarem que a entrada única sofre com o momento de entrada e depois de ampliar o contrato de sinais para aceitar tamanhos-alvo. Registrar como **B-SCALE-IN**.

### O4 — Média/volatilidade adaptativas com estimador exponencial ou de Kalman *(livro: C5, C6, pp. 74–83)*

* **Proposta:** oferecer média e variância baseadas em EMA (já usadas pelas estratégias atuais para preços) e, mais adiante, estimador de Kalman unidimensional (`m(t)`, `Q(t)`) para substituir média móvel e desvio-padrão em O1. Segundo o livro, isso evita o efeito abrupto de uma janela fixa. A versão com razão de hedge entre dois ativos está fora de escopo.
* **Complexidade:** média (estado adicional e dois parâmetros de ruído, escolhidos retrospectivamente pelo autor). **Risco:** dois parâmetros extras aumentam a seleção de dados; o filtro unidimensional oferece ganho modesto sobre uma EMA. **Validação:** comparar EMA/janela móvel em dados sintéticos e medir sensibilidade a δ e `V_e`. Prioridade baixa.

### O5 — Reforçar a defesa contra ticks incorretos na operação real *(livro: C7, pp. 83–84)*

* **Proposta:** além do filtro de amplitude, verificar o *fechamento anterior* (salto em relação à volatilidade recente) e uma segunda fonte (por exemplo, ticker da corretora versus último fechamento) antes de executar uma entrada de reversão à média. **Complexidade:** média. **Risco:** mais quedas legítimas podem ser rejeitadas; calibrar com cuidado e registrar cada rejeição. Combinar com livro 1, cap. 3 O3.

### Não aplicável ou adiado

Pares, construção de spread/log-spread/razão de hedge, hedge dinâmico por Johansen/Kalman, pares cambiais e formação de mercado com ruído ponderado pelo tamanho da operação (não há dados de ticks).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O5 defesa contra ticks incorretos na operação real | – | alta | alta | média | livro 1, cap. 3 O3 |
| 2 | O1 `bollinger_reversion` | média | média | – | baixa–média | livro 1, cap. 3 O3/O5; livro 2, cap. 2 O1 |
| 3 | O2 padrão pela meia-vida | média | – | – | baixa | livro 2, cap. 2 O1 |
| 4 | O4 estimadores adaptativos | baixa | – | – | média | O1 |
| 5 | O3 entradas graduais | – | – | – | alta | contrato de sinais (B-SCALE-IN) |

## 5. Arquivos afetados

`strategies/domain/` (novo arquivo de estratégia e registro), `strategies/catalog.py`, `risk_management/domain/models.py` (O5), `market_data/domain/models.py`, formulários de parâmetros e rótulos de estratégias no app (`lib/shared/strategies/params.ts`), `check:consistency` e testes (`api/tests/unit`).

## 6. Plano incremental

1. Primeiro, integridade dos dados e teste de truncamento (livro 1, cap. 3).
2. Aplicar os diagnósticos (livro 2, cap. 2 O1) a séries cripto reais para verificar a reversão à média no intervalo pretendido.
3. Se houver evidência, criar `bollinger_reversion` com análise de custos e sensibilidade; caso contrário, interromper.
4. Acrescentar verificações de ticks incorretos na operação real.
5. Considerar estimadores adaptativos apenas se a estratégia demonstrar utilidade.

## 7. Critérios de aceitação e testes

* A estratégia passa no teste de truncamento e valida seus parâmetros como as existentes.
* Opera em dados sintéticos com reversão à média e permanece sem posição ou perde pouco numa série tendencial de teste.
* Custos sempre incluídos; resultados apresentados com divisão treino/teste e análise de sensibilidade dos parâmetros.
* Nenhuma alteração nas estratégias atuais ou nas salvaguardas da operação real; Ruff, mypy e testes passam.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`), números como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil. A última migração é `0014_backtest_regime`. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| C3 estratégia de bandas/z-score | ❌ | ❌ continua; o desenho completo está no [livro 1, cap. 7, Fase 2](../01-quantitative-trading-chan/ch07-special-topics.md) com o nome `mean_reversion_zscore`. **O1 deste capítulo é essa mesma estratégia** (outro nome no relatório, mesmo conteúdo). |
| C3 janela pela meia-vida | ❌ | ⚠️ a meia-vida existe (`GET /market-data/half-life`), mas nenhum formulário a usa ([cap. 2, Fase B](ch02-basics-of-mean-reversion.md)). |
| C7 erro de dados no backtest | ❌ | ✅ `market_data/domain/quality.py` (`candle_problems`: OHLC inconsistente, preço ≤ 0, volume negativo, horário fora da grade) rejeita na importação; `find_outliers` (> 4σ) e a guarda de lacunas ficam em `data_quality` por execução. |
| C7 erro de dados na operação real | ⚠️ | ⚠️ continua: o trader pula candles inválidos com evento `data.invalid_candle`, e o risco recusa entrada se a **amplitude** passa de `max_candle_range_pct` (25%). Não olha o salto contra o fechamento anterior. |
| Portões de qualidade | parciais | ✅ truncamento em toda estratégia (`test_lookahead.py`), escada de custos, treino × teste, robustez de vizinhos nas varreduras, paridade bot × backtest. Estratégia nova ganha tudo isso. |
| Catálogo | 2 de tendência | 2 de tendência. |

**Achados que moldam o plano:**
* Limites de risco do **bot** são colunas (`BotRow` em `bots/infrastructure/orm.py`); os do **backtest** ficam em `risk_limits` JSONB. Um campo novo em `RiskLimits` exige migração para os bots, mas **não** para os backtests. Precedente exato: `max_order_pct_of_volume` (migração `0011_execution_parity`), que tocou `risk_management/domain/models.py` e `presentation/schemas.py`, `bots/infrastructure/orm.py` e `repository.py`, `lib/bots/bots.api.ts` e `form.ts`, `lib/backtests/backtests.api.ts` e `form.ts`, `api.d.ts` e `openapi.json`.
* `StrategyOut.too_many_parameters` marca mais de **5** parâmetros declarados. `mean_reversion_zscore` já nasce com 5 (`lookback`, `entry_z`, `exit_z`, `max_holding_candles`, `stop_loss_pct`); qualquer parâmetro a mais (filtro de tendência do [cap. 4](ch04-mean-reversion-stocks-etfs.md), Kalman) estoura o limite.

### Fase A — A estratégia (O1 + O2): executar o plano do livro 1 · prioridade 2

Não há desenho novo aqui. Seguir o [livro 1, cap. 7, Fase 2](../01-quantitative-trading-chan/ch07-special-topics.md) (arquivo `strategies/domain/mean_reversion_zscore.py`, uma linha em `strategies/catalog.py`, `ParamSpec.minimum` decimal, teste de contrato por estilo) e acrescentar só o que este capítulo pede:

* **A.1 `lookback` padrão pela meia-vida (O2), no front:** o formulário (`strategy-fields.tsx`) já recebe a dica do [cap. 2, Fase B](ch02-basics-of-mean-reversion.md); aqui só se garante que, quando a estratégia é `mean_reversion_zscore`, o campo `lookback` mostra "sugerido: ≈ meia-vida" **sem preencher sozinho**. O valor padrão do backend continua 20 (valor de partida nosso, não do livro).
* **A.2 Portão de pesquisa (não é código):** antes de qualquer bot, os controles já existentes: backtest de pelo menos 2 anos em vários pares, `cost_sensitivity`, `test_fraction`, `fill_timing = signal_close`, risco do bot, sweep em `lookback × entry_z` lendo a robustez e a contagem de tentativas, depois paper e paridade. **Pré-condição nova:** os diagnósticos do [cap. 2](ch02-basics-of-mean-reversion.md) (`H < 0,5`, meia-vida estacionária) para o par e o intervalo. Sem eles, a estratégia não sobe para paper.
* **Aceite:** o que já está no plano do livro 1 (contrato, truncamento com a série fazendo a estratégia **operar**, 422 claro nos parâmetros) mais: nenhuma estratégia existente muda de comportamento.

### Fase B — Defesa contra tick incorreto na operação real (O5) · prioridade 1 · migração própria

Objetivo: recusar **entrada** quando o candle fechado destoa do anterior além do que a volatilidade recente explica. Saídas nunca são recusadas (regra existente: `test_suspect_candles_block_entries_but_not_exits`).

* **B.1 Back-end, regra pura** em `risk_management/domain/models.py`: `RiskLimits.max_close_jump_pct: Decimal | None = None` (validação como as demais porcentagens, `0 < x ≤ 100`), e em `assess_signal` uma recusa `"suspect candle: close moved X% from the previous close"` ao lado da recusa por amplitude. Para isso o contexto de avaliação precisa do **fechamento anterior**; verificar como `assess_signal` recebe o candle hoje e acrescentar o campo opcional sem quebrar os chamadores (motor de backtest e trader). Padrão `None` (desligada), para nada mudar sozinho; **decisão pendente** sobre um padrão ligado.
* **B.2 Persistência:** migração `NNNN_max_close_jump` (`ALTER TABLE bots ADD COLUMN max_close_jump_pct NUMERIC NULL`; `downgrade` remove), mais `bots/infrastructure/orm.py`, `repository.py` (`_to_bot` e `_config_values`), `risk_management/presentation/schemas.py`, `api/docs/openapi.json`. Backtests guardam os limites em JSON e não precisam de coluna. Seguir a lista de arquivos do precedente `max_order_pct_of_volume`.
* **B.3 Segunda fonte (a parte cara, adiada):** comparar com o ticker da exchange antes de executar. Exige uma chamada a mais por entrada e um campo no contrato `Exchange` (`exchanges/application/exchange.py`); **não entra neste corte** e fica como decisão: o salto contra o fechamento anterior já cobre o erro de dados mais comum.
* **B.4 Front-end:** campo "Salto máximo do fechamento (%)" no bloco de risco de `lib/bots/form.ts` e `lib/backtests/form.ts` (opcional, vazio = desligado), schemas em `bots.api.ts` e `backtests.api.ts`, texto de apoio ("recusa entradas, nunca saídas; calibre com cuidado: quedas legítimas de cripto também são grandes"). `npm run api:types` e `check:consistency`. 360 px.
* **B.5 Testes:** `tests/unit/test_risk_and_stops.py` (ou novo `test_close_jump.py`): recusa na entrada com salto acima do limite, aceita abaixo, **nunca recusa saída**, desligada não muda nada; paridade: o replay aplica a mesma regra (o replay usa os limites do bot). Integração: bot paper recebe um candle com salto e registra a recusa com o motivo.
* **Aceite:** com o campo vazio, todos os testes existentes passam sem mudança; a recusa aparece na aba Sinais com o motivo; salvaguardas live intactas.

### Fase C — Entradas graduais (O3): nada a fazer · registro

O capítulo conclui que, dentro da amostra, **uma entrada única** supera o preço médio. O modelo atual (uma entrada, uma saída) é a referência. Registrar **B-SCALE-IN** no backlog e reabrir só se as varreduras mostrarem sensibilidade ao momento da entrada **e** o contrato de sinais (`target_fraction`, [cap. 2, Fase C](ch02-basics-of-mean-reversion.md)) existir.

### Fase D — Média e variância adaptativas (O4) · prioridade 4 · só desenho

Só depois da Fase A mostrar utilidade. Desenho mínimo: função pura `analytics/domain/filters.py` com média e variância exponenciais (`ema_mean_variance(series, alpha)`) e, mais tarde, o estimador de Kalman unidimensional; entra na estratégia como **opção** (`mean_type`), o que **estoura o limite de 5 parâmetros** e exige decidir: aumentar o limite de `too_many_parameters`, tirar `stop_loss_pct` da estratégia ou criar a variante como estratégia separada. **Decisão pendente.** Teste: comparar janela fixa × EMA em série sintética e medir sensibilidade (um pico isolado sugere sobreajuste).

### Ordem, dependências e estimativa

B é independente e a única com migração; A depende do [livro 1, cap. 6, Fase C](../01-quantitative-trading-chan/ch06-money-and-risk-management.md) (metadados de estilo) e da Fase 1 do livro 1, cap. 7 (já implementada: `max_holding_candles`); D só depois de A. Estimativa grosseira: A ≈ 3 dias (a adaptação do teste de contrato pesa; já contada no livro 1); B ≈ 2 (1,5 back, 0,5 front); C zero; D fora do corte.

### Decisões pendentes (para o operador)

* Padrão de `max_close_jump_pct` (proposta: desligado até haver dados de candles reais para calibrar).
* Se a segunda fonte de preço (B.3) vale a chamada extra por entrada.
* Como resolver o limite de 5 parâmetros se a estratégia crescer (Fase D e filtro de tendência do cap. 4).

### Fora do escopo (decidido)

Pares, razão de hedge, Johansen e Kalman bidimensional (posição vendida, vários ativos), formação de mercado com ruído ponderado por tamanho (não há ticks).

### Critérios de aceite gerais

Nenhuma estratégia existente e nenhuma salvaguarda live muda; custos sempre incluídos; resultados com treino × teste e sensibilidade dos parâmetros; nenhum `float` no domínio; `make check`, integração, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas em 1366 px e 360 px. Resultados do livro (10,9%, 17,8%, 26,2% ao ano) são de ETFs e câmbio, sem custos, e não valem para cripto.

## Ressalvas

Os retornos anuais e Sharpe do livro (10,9%, 17,8%, 26,2% etc.) vêm de pares de ETFs comprados e vendidos, sem custos, alguns com parâmetros escolhidos retrospectivamente. Não devem ser esperados em criptoativos. A afirmação de que entradas graduais nunca são ótimas baseia-se num exemplo estilizado com probabilidades constantes.
