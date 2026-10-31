# Livro 1 · Capítulo 3 — Backtesting

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **apenas análise**; nada novo implementado por este relatório. Diagnóstico revisado contra o código em 2026-10-31, **depois** da implementação do [Cap. 2](ch02-fishing-for-ideas.md), que já entregou O1, O2, O9 e parte de O7 (ver §2.1).

Nota de leitura: as pp. 32–36 (Excel, MATLAB, TradeStation e plataformas comerciais) foram apenas folheadas; descrevem ferramentas, não métodos. O restante (pp. 36–67) foi lido. No texto extraído o sinal de raiz quadrada se perde na prosa (a p. 44 imprime "12 times"), mas o código das pp. 45–46 mostra `SQRT(252)`, o que confirma a fórmula abaixo.

## 1. Resumo do capítulo (pp. 31–67)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Replicar cada estratégia você mesmo: prova que você a entendeu, expõe erros da pesquisa original e permite testar variações. | Confiar em resultados publicados não verificados. | 31 |
| C2 | **Dados ajustados** (splits, dividendos): multiplicar os preços anteriores por um fator para que os retornos não mudem; dados sem ajuste criam sinais falsos nas datas ex. | Saltos de preço falsos. | 36–40 |
| C3 | **Viés de sobrevivência**: o exemplo de brinquedo "comprar as ações de menor preço" deu −42% com papéis deslistados incluídos e +388% sem eles. Mitigação: registrar dados point-in-time você mesmo daqui em diante, ou testar em dados recentes. | Resultados inflados. | 40–42 |
| C4 | **Dados de máxima/mínima são mais ruidosos** que abertura/fechamento; uma ordem limitada "abaixo da máxima" pode não ter sido executada. Uma checagem de sanidade: calcular os retornos, inspecionar os que passam de ~4 desvios-padrão e exigir um evento de notícia ou um movimento de todo o mercado que os explique. | Backtests que lucram com ticks ruins. | 42–43 |
| C5 | **Sharpe e drawdown** são as duas medidas principais (o retorno anual bruto exige qualificações demais: denominador, alavancagem). **Não** subtrair a taxa livre de risco em estratégias dollar-neutral ou só intradiárias (sem custo de financiamento); subtrair quando a estratégia tem financiamento. **Sharpe anualizado = √N_T × Sharpe no período T**, onde N_T é o número de períodos em um ano (N_T = 252 × 6,5 = 1.638 para retornos horários da sessão dos EUA; calcular 252 × 24 é citado como erro comum). Exemplo 3.4: `SQRT(252)*AVERAGE(excess)/STDEV(excess)`. | Comparar estratégias de forma justa. | 43–47 |
| C6 | **Cálculo do drawdown** (Exemplo 3.5): retorno composto acumulado; high watermark corrente; drawdown = (1+HWM)/(1+cum) − 1; contador de duração volta a 0 quando o drawdown é 0, senão +1; máximos de ambos. Resultado do exemplo: 10,53% e 497 dias. | Números de drawdown reprodutíveis. | 48–50 |
| C7 | **Viés de look-ahead**: usar informação ainda não disponível (por exemplo a mínima do dia, ou coeficientes de regressão ajustados em toda a amostra). Corrige-se atrasando (lag) as entradas do sinal. **Teste de truncamento**: rodar em todos os dados e salvar as posições A; rodar nos dados truncados pelos últimos N períodos (10–100) e salvar B; cortar A ao mesmo tamanho; devem ser idênticas. | Vazamento silencioso do futuro. | 51–52, 59 |
| C8 | **Viés de data-snooping**: regra prática ≤ **5 parâmetros**; escolhas qualitativas (entrar na abertura vs. fechamento, carregar overnight…) também contam; tamanho de amostra ≈ **252 × número de parâmetros livres** (declarado como baseado em experiência, não em literatura), contado em observações *independentes* (7 meses de dados por minuto para um modelo diário são só ~147 pontos). | Overfitting. | 52–53 |
| C9 | **Fora da amostra**: treinar primeiro, testar na parte posterior (metades aproximadamente iguais; teste ≥ ⅓ do treino, no mínimo). Se o teste for ruim, simplificar o modelo. A **otimização móvel (rolling)** é a versão mais rigorosa; modelo "sem parâmetros" = parâmetros reotimizados numa janela móvel de lookback; é melhor tirar a média entre conjuntos de parâmetros do que escolher um só "melhor". O **paper trading** é o teste final fora da amostra, e o período desde a publicação conta como fora da amostra se você não ajustou sobre ele. | Estimativa honesta de generalização. | 53–55 |
| C10 | **Análise de sensibilidade**: variar parâmetros e fazer pequenas mudanças qualitativas; um modelo que só funciona no ótimo exato está sobreajustado. Remover condições uma a uma e continuar removendo enquanto o resultado do **teste** não piorar. Nunca adicionar ou ajustar para melhorar o conjunto de teste (ele vira treino). Depois, dividir o capital entre valores de parâmetros. | Ótimos frágeis. | 60 |
| C11 | **Custos** (Exemplo 3.7): uma estratégia com Sharpe 4,47 antes dos custos em small caps teve 0,25 no S&P 500 e −3,19 após 5 bp por operação. Tratar resultados sem dados livres de sobrevivência como limites superiores. | Custos e universo decidem a viabilidade. | 60–65 |
| C12 | **Refinamento**: pequenas variações (por exemplo agir na abertura em vez do fechamento elevou o Sharpe de −3,19 para 0,78 após custos, Exemplo 3.8); preferir refinamentos com lógica econômica, e qualquer mudança deve melhorar treino e teste. | Melhorar sem sobreajustar. | 65–66 |
| C13 | Honestidade do resumo: pular algumas precauções é aceitável para uma primeira olhada; problemas ainda podem aparecer só no paper/live. | Perfeccionismo vs. progresso. | 67 |

Os dois exemplos trabalhados de Chan, de pairs trading e reversão à média, são específicos de ações (pares de ETFs, S&P 500) e não são transferíveis como tal; só a metodologia é. Nenhum conselho sobre cripto aparece no capítulo.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C2 dados ajustados | n/a | O spot cripto não tem splits/dividendos. Eventos do lado da exchange (redenominação de símbolo, deslistagem) não são tratados. |
| C3 sobrevivência | ❌ | Sem registro de listagens nem de deslistagens; universo escolhido à mão. A tela de comparação já avisa quando os pares diferem (Cap. 2, O8), mas não há dado point-in-time. |
| C4 sanidade dos dados | ❌ | `Candle` (`api/src/modules/market_data/domain/models.py`) não valida nada: nem `high ≥ max(open, close)`, nem `low ≤ min(open, close)`, nem preços positivos, nem volume ≥ 0, nem `open_time` alinhado ao timeframe. O parser da exchange (`exchanges/infrastructure/ccxt_exchange.py`) monta o candle direto da resposta; o importador (`CandleImporter._import`) grava tudo com `upsert_many`, que **sobrescreve** linhas existentes; a tabela `candles` não tem CHECK de OHLC. O único filtro é do risco do bot: recusa *entradas* em candles com amplitude acima de `max_candle_range_pct` (padrão 25%). O backtester não filtra nem relata nada; não há relatório de outliers. |
| C4 cobertura / lacunas | ⚠️ | `find_gaps` existe e `GET /market-data/coverage` devolve as lacunas, mas **da série inteira guardada**, não do período pedido. No app, `CoverageNotice` (formulário de backtest) só avisa, não bloqueia, e o aviso pode citar lacunas fora do período escolhido. No back-end, `BacktestService._check_candles` exige só **um** candle no intervalo. O motor atravessa o buraco: o sinal emitido antes dele é executado na abertura do primeiro candle depois do buraco. Desde o Cap. 2 o Sharpe descarta os retornos através de buracos e mostra `return_gaps`, mas a execução ainda roda e o resultado não diz quantos candles faltaram. |
| C5 Sharpe | ✅ | Implementado no Cap. 2 (`analytics/domain/risk_ratios.py`): `√N_T × média / desvio`, N_T = 365 dias / candle, taxa livre de risco 0. Falta só reproduzir o Exemplo 3.4 (sem os dados do IGE no repositório). |
| C6 drawdown | ✅ | Implementado no Cap. 2 (`drawdown_stats`): profundidade, duração do pico até recuperar (equivale ao contador do livro, que zera quando o drawdown é 0), drawdown em aberto; curva underwater no app. |
| C7 look-ahead | ✅ por construção, ❌ sem teste | O motor executa na abertura do candle seguinte e a estratégia só recebe o candle fechado e seu próprio estado (`StrategyContext`), o que torna o vazamento difícil hoje. Mas não há teste de truncamento (grep por `truncat` em `api/tests` não acha nada). O risco cresce quando entrarem estratégias que pré-calculam indicadores sobre a série inteira (ML, regressões) ou mudanças no motor (stops, fills). |
| C8 snooping / tamanho da amostra | ⚠️ | As duas estratégias (`ema_crossover`, `donchian_breakout`) têm 4 parâmetros cada (2 períodos + stop + alvo opcionais), dentro do limite de 5 do livro. Desde o Cap. 2 a varredura mostra `trials` e `prior_trials`. Falta: nenhuma checagem de tamanho de amostra (252 × parâmetros livres) nem de observações independentes. |
| C9 fora da amostra | ⚠️ | Uma divisão fixa (`segments.py`); desde o Cap. 2 a varredura escolhe pelo treino e confere no teste. Falta: nenhuma regra de tamanho mínimo do teste (o livro pede teste ≥ ⅓ do treino, ou seja `test_fraction ≥ 0,25`); o formulário aceita qualquer valor entre 0 e 1. Sem walk-forward. O paper trading existe e é obrigatório antes do live, mas não há comparação paper × backtest (tema do Cap. 5). |
| C10 sensibilidade | ⚠️ | A varredura dá a matéria-prima, mas não há visão de robustez: nada diz se o vencedor é um platô ou um pico isolado, nem a média dos vizinhos. |
| C11 custos | ✅ | Escada de custos e custo de equilíbrio implementados no Cap. 2 (`backtesting/domain/cost_ladder.py`). |
| C12 refinamento | ✅ possível | Experimentos são baratos; a contagem de tentativas do Cap. 2 já registra o custo de refinar. |

### 2.1 O que mudou desde a versão anterior deste relatório

* **Já implementado pelo Cap. 2:** O1 (Sharpe/Sortino), O2 (duração do drawdown), O9 (sensibilidade a custos) e a parte de O7 que conta tentativas e escolhe pelo treino. Ficam aqui só como referência.
* **Diagnóstico de lacunas refinado:** a cobertura calcula lacunas sobre a série inteira, não sobre o período do backtest; o aviso do app pode estar errado nos dois sentidos.
* **Achado novo:** `upsert_many` sobrescreve candles já guardados em toda reimportação, sem validar e sem registrar o que mudou; uma resposta ruim da exchange pode corromper dados que estavam bons.
* **Achado novo:** o trader dos bots usa o mesmo `Candle` sem validação; um candle malformado chega à estratégia em produção.

## 3. Oportunidades

Convenções (as mesmas do Cap. 2): campos novos na API são opcionais e aditivos; tudo `Decimal` no domínio; cada mudança de contrato atualiza `api/docs/openapi.json`, `npm run api:types` e `npm run check:consistency`; textos da UI em português; nada é apresentado como garantia de resultado.

### Já implementados (Cap. 2)
* **O1 — Sharpe/Sortino anualizados:** feito. Pendente opcional: fixture do Exemplo 3.4 se os preços do IGE forem adicionados ao repositório.
* **O2 — Duração do drawdown e watermark:** feito (métrica + curva underwater).
* **O9 — Sensibilidade a custos e custo de equilíbrio:** feito (`cost_sensitivity`, `cost_ladder`).

### O3 — Integridade dos candles *(livro: C4, pp. 42–43)*
* **Problema:** dados ruins entram sem filtro e o backtest pode lucrar com um tick errado; uma reimportação pode estragar dados bons.
* **Back-end:**
  * Função pura `candle_problems(candle) -> list[CandleProblem]` em `market_data/domain/quality.py`: `high < max(open, close)`, `low > min(open, close)`, `high < low`, preço ≤ 0, volume < 0, `open_time` desalinhado do timeframe. Enum `CandleProblem` com códigos estáveis.
  * Importador: candles com problema **não são gravados**; o job conta e guarda amostras. Novas colunas em `candle_import_jobs`: `candles_rejected INTEGER NOT NULL DEFAULT 0`, `rejection_samples JSONB` (até 20: horário + códigos). O job termina como `completed` mesmo com rejeições; `ImportJobOut` ganha os dois campos.
  * Reimportação: antes do `upsert`, comparar com o que já existe; se o OHLC mudar, contar em `candles_changed` (coluna nova) em vez de sobrescrever em silêncio. A sobrescrita continua (a exchange pode corrigir dados), mas fica visível.
  * Trader dos bots (`trading/application/trader.py`): candle com problema não chega à estratégia; o ciclo é pulado e grava um evento de auditoria `data.invalid_candle` com os códigos (o trader já grava eventos como `signal.rejected` e `risk.*`), visível na tela de auditoria e na atividade do bot.
  * **Relatório de outliers:** `GET /market-data/outliers?exchange&symbol&timeframe&start&end&k=4`. Calcula os retornos close-a-close no período, o desvio-padrão e devolve os candles com |retorno| > k·σ (padrão k = 4, como no livro), cada um com o retorno, quantos σ e, quando houver candles do mesmo horário de `BTC/USDT`, o retorno do BTC no mesmo candle (adaptação do "movimento de todo o mercado" do livro: se o BTC também se moveu, provavelmente é real).
  * Backtest: ao executar, contar candles com problema e outliers no período e salvar em nova coluna JSONB `data_quality` de `backtest_runs` (`invalid`, `outliers`, `outlier_samples`, `k`). **Sinalizar, não excluir:** tirar candles muda a linha do tempo e pode apagar crashes reais.
* **Front-end:**
  * Dados de mercado (`market-data-page.tsx`): coluna "Rejeitados" e "Alterados" na tabela de importações, com as amostras num popover; card "Movimentos fora do comum" com a tabela de outliers (data UTC, retorno, σ, retorno do BTC) e o candle destacado no gráfico existente.
  * Detalhe do backtest: card "Qualidade dos dados" (candles usados, lacunas — ver O4 —, outliers com link para a tela de dados de mercado já filtrada); vira alerta amarelo quando houver outlier ou candle inválido.
  * Triagem rápida (`lib/backtests/screening.ts`): novo alerta quando `data_quality.outliers > 0` — "o resultado pode depender de dados errados; confira os N movimentos fora do comum".
* **Complexidade:** média. **Risco:** crashes reais (ex.: março de 2020) passam de 4σ; por isso o relatório só sinaliza e mostra o BTC como referência. **Validação:** testes de unidade de `candle_problems` para cada código; teste de integração com uma fonte falsa que devolve candles malformados (contagem certa, nada gravado); teste do relatório de outliers com uma série sintética com um salto conhecido; teste do trader recusando o candle.

### O4 — Lacunas no período do backtest *(adaptação, motivada por C4/C11)*
* **Problema:** o backtest roda sobre buracos sem avisar; o app mostra lacunas da série inteira.
* **Back-end:**
  * `GET /market-data/coverage` aceita `start`/`end` opcionais e devolve também `range_gaps`, `range_missing` e `range_expected` para o período (sem quebrar a resposta atual).
  * `BacktestService._check_candles` calcula as lacunas do período com `find_gaps`; se faltar mais que `MAX_MISSING_SHARE` (sugestão: 1% dos candles esperados) ou houver um buraco maior que 24 h, responde 422 com o resumo, a menos que o pedido traga `allow_gaps: true` (campo novo em `BacktestCreate`/`BacktestConfig`, guardado na execução).
  * O resultado guarda as lacunas em `data_quality.gaps` (mesma coluna de O3): quantidade, candles faltando, maior buraco.
  * O motor não muda: continua executando na próxima abertura disponível; a documentação do motor passa a dizer isso.
* **Front-end:**
  * `CoverageNotice` passa `start`/`end` e mostra só as lacunas **do período**, com o maior buraco ("faltam 37 candles; maior buraco: 12 h em 14/03").
  * Formulário: com lacunas acima do limite, o botão "Rodar backtest" fica bloqueado até marcar "Rodar mesmo com lacunas" (envia `allow_gaps`), com o atalho para importar que já existe.
  * Detalhe do backtest: as lacunas aparecem no card "Qualidade dos dados" (O3), junto com `return_gaps` das métricas.
* **Complexidade:** baixa. **Risco:** manutenções da exchange são buracos legítimos; por isso há tolerância e a opção explícita. **Validação:** teste de integração com um buraco (422 sem `allow_gaps`, 202 com, e `data_quality.gaps` preenchido); teste da cobertura por período.

### O5 — Teste de truncamento (look-ahead) *(livro: C7, pp. 52, 59)*
* **Back-end (só testes, sem código de produção):**
  * `api/tests/unit/test_lookahead.py`, parametrizado sobre **todas as estratégias do catálogo** (`strategies/catalog.py`), com parâmetros padrão e com stop/alvo ligados.
  * Para cada uma: rodar `run_backtest` com N candles (série sintética com tendência, lateralização e quedas) e com os últimos k removidos (k = 10, 50, 100, como no livro); comparar no prefixo comum as execuções (`fills` com horário anterior ao corte), `in_market` e os sinais rejeitados. Devem ser idênticos.
  * Fixture de controle: uma estratégia de teste que "espia" o próximo fechamento (recebe a série inteira por closure) deve **reprovar**, provando que o teste detecta vazamento.
  * Mesmo teste para o caminho do trader dos bots quando o Cap. 5 trouxer a paridade paper × backtest.
* **Front-end:** nada.
* **Complexidade:** baixa. **Benefício:** protege contra o erro silencioso mais caro toda vez que uma estratégia ou o motor mudar. **Validação:** o próprio teste roda no `make check`.

### O6 — Tamanho de amostra e parâmetros livres *(livro: C8, pp. 52–53 · limiares são regras práticas do autor)*
* **Back-end:**
  * `free_parameters(strategy_type, params)`: conta os `PARAMETERS` cujo valor efetivo não é nulo (stop e alvo desligados não contam).
  * Ao executar, salvar em nova chave `sample` do resultado (pode ir em `data_quality` ou coluna própria): `free_parameters`, `bars`, `round_trips`, `min_bars_rule = 252 × free_parameters`, `meets_bar_rule`, `meets_trade_rule` (round trips ≥ 30, adaptação nossa: o livro conta observações independentes, e as barras de um mesmo trade não são independentes).
  * Estratégia com mais de 5 parâmetros: aviso no catálogo (`GET /strategies`) com `parameter_count`.
* **Front-end:**
  * Formulário: dica sob o período — "este período tem ~N candles; com k parâmetros livres o livro sugere ≥ 252·k observações".
  * Triagem rápida: alertas "amostra pequena para k parâmetros" e "poucas operações independentes" (substitui o alerta atual de poucas operações por ano quando o dado existir).
* **Complexidade:** baixa. **Risco:** a regra do 252 é empírica e para dados diários de ações; manter como aviso configurável, nunca bloqueio. **Validação:** testes de unidade da contagem (stop nulo não conta) e do aviso.

### O7 — Robustez da varredura (platô × pico) *(livro: C8, C10, pp. 52–60)*
* **Já feito (Cap. 2):** `trials`, `prior_trials`, escolha pelo treino, verificação do vencedor no teste.
* **Back-end:**
  * `backtesting/domain/robustness.py`: para grades numéricas, montar a matriz de resultados pelo critério de ranking; para o vencedor, calcular a média e o mínimo dos **vizinhos** (±1 posição em cada parâmetro), a razão vizinhos/vencedor, a fração de combinações lucrativas, a mediana e a média do top 3 (o livro sugere dividir o capital entre conjuntos de parâmetros em vez de apostar em um).
  * `SweepOut.robustness`: `{neighbour_mean, neighbour_min, neighbour_ratio, profitable_share, top3_mean, median, verdict}` com `verdict` em `plateau | peak | insufficient` (pico quando os vizinhos ficam abaixo de, por exemplo, 50% do vencedor; insuficiente quando a grade tem menos de 3 valores por parâmetro).
  * Calculado na leitura a partir das execuções concluídas (sem coluna nova).
* **Front-end:**
  * Página da varredura: card "Robustez" com o veredito em texto ("platô: os vizinhos rendem ~85% do vencedor" / "pico isolado: os vizinhos rendem 20% — provável sobreajuste"), fração lucrativa e média do top 3.
  * Para grades de 2 parâmetros: tabela cruzada (linhas = parâmetro A, colunas = parâmetro B) com o valor escrito em cada célula e a cor por token só como reforço; o vencedor marcado com ícone. O lost-ui não tem heatmap: registrar o pedido em `app/docs/lost-ui-requests.md` em vez de desenhar um gráfico à mão.
* **Complexidade:** média. **Risco:** sem correção formal de testes múltiplos (PSR/DSR, PBO ficam para o Livro 5, backlog A5/A6). **Validação:** varredura sintética com um único pico deve dar `peak`; com superfície suave, `plateau`.

### O8 — Otimização walk-forward *(livro: C9, pp. 54–55)*
Continua fora do escopo: backlog **B-WALK-FORWARD** (A12), a planejar com os capítulos de validação cruzada do Livro 5 (purga e embargo). As peças que ele precisa (métricas, contagem de tentativas, escolha pelo treino) já existem.

### O10 — Registro de listagens point-in-time *(livro: C3, p. 40 · adaptação)*
* **Back-end:** tarefa diária no worker que lê os mercados da exchange (`load_markets`) e grava em nova tabela `exchange_listings` (`exchange`, `symbol`, `first_seen`, `last_seen`, `status`, `delisted_at`). `GET /market-data/listings?symbol=` devolve o histórico. O valor cresce com o tempo, então convém começar cedo.
* **Front-end:** na tela de dados de mercado, selo do status do par ("listado desde…", "deslistado em…"); o aviso de sobrevivência da comparação passa a citar pares deslistados conhecidos.
* **Complexidade:** baixa. **Risco:** a API da exchange só diz o estado de hoje; o histórico começa no dia em que a tarefa entrar no ar. **Validação:** teste do job com uma fonte falsa que remove um par.

### O11 — Tamanho mínimo do teste *(livro: C9, p. 54)*
* **Back-end:** nada obrigatório; `segments` já informa `test_fraction`.
* **Front-end:** no formulário, aviso (não bloqueio) quando `test_fraction < 0,25` ("o livro sugere o teste com pelo menos ⅓ do treino"); triagem rápida com o mesmo aviso no resultado.
* **Complexidade:** muito baixa. **Validação:** teste de unidade do aviso.

### Não recomendado agora
* **Executar no fechamento do candle do sinal (C12, Exemplo 3.8):** no nosso motor isso seria otimista (o sinal só existe depois do fechamento). Manter a execução na abertura seguinte.
* **Remover condições uma a uma (C10):** as estratégias atuais já são mínimas; reavaliar quando houver estratégias com filtros.
* **Paper trading como teste final (C9):** já é obrigatório; a comparação paper × backtest é o Cap. 5 (backlog B7).
* Ajuste de splits/dividendos (C2), exemplos com universos de ações (C11, C12), escolha de plataformas (pp. 32–36).

## 4. Prioridade

| # | Item | Qualidade do backtest | Confiabilidade | Esforço back | Esforço front | Depende de |
|---|---|---|---|---|---|---|
| 1 | O5 teste de truncamento | alta | alta | baixo | – | – |
| 2 | O4 lacunas no período | alta | média | baixo | baixo | – |
| 3 | O3 integridade + outliers | alta | alta | médio | médio | – |
| 4 | O7 robustez da varredura | alta | – | médio | médio | Cap. 2 (feito) |
| 5 | O6 tamanho de amostra | média | – | baixo | baixo | – |
| 6 | O11 tamanho mínimo do teste | média | – | – | muito baixo | – |
| 7 | O10 registro de listagens | baixa agora | – | baixo | baixo | – |
| 8 | O8 walk-forward | alta | – | alto | médio | Livro 5 |

O5 primeiro porque não toca código de produção e protege tudo o que vem depois. O4 antes de O3 porque é pequeno e reaproveita `find_gaps`.

## 5. Arquivos afetados

**Back-end (`api/`)**
* Novo `src/modules/market_data/domain/quality.py` (O3); `market_data/application/service.py` (importador, cobertura por período, outliers); `market_data/application/ports.py`, `infrastructure/orm.py`, `infrastructure/repository.py` (contadores de importação, comparação antes do upsert, listagens); `market_data/presentation/router.py` (`/coverage` com período, `/outliers`, `/listings`).
* `backtesting/application/service.py` (`_check_candles` com lacunas, `data_quality`, `sample`), `backtesting/domain/models.py` (`allow_gaps`), novo `backtesting/domain/robustness.py`, `backtesting/presentation/router.py`.
* `trading/application/trader.py` (recusa de candle inválido); `strategies/presentation` (`parameter_count`).
* Migração `0009_data_quality.py`: colunas de importação, `backtest_runs.data_quality`, `allow_gaps`, tabela `exchange_listings`.
* Testes: novos `tests/unit/test_lookahead.py`, `test_candle_quality.py`, `test_sweep_robustness.py`; integração em `test_phase1_flow.py` (lacunas, rejeições, outliers).

**Front-end (`app/`)**
* `src/components/market-data/market-data-page.tsx` (rejeitados, alterados, outliers, status de listagem), `src/lib/market-data/market-data.api.ts`, `src/lib/shared/market-data/coverage.api.ts` e `src/components/shared/market-data/coverage-notice.tsx` (período).
* `src/components/backtests/backtest-form-page.tsx` e `src/lib/backtests/form.ts` (`allow_gaps`, avisos de amostra e de teste mínimo); novo `src/components/backtests/data-quality-card.tsx`; `backtest-detail-page.tsx`; `src/lib/backtests/screening.ts` (novos alertas); `sweep-page.tsx` + novo `src/components/backtests/robustness-card.tsx`.
* `app/docs/06-screens.md`, `app/docs/lost-ui-requests.md` (heatmap).

## 6. Plano incremental

Cada passo é um PR pequeno, com testes, e pode ir para produção sozinho.

1. **O5:** teste de truncamento para todas as estratégias + estratégia de controle com vazamento.
2. **O4:** cobertura por período, guarda de lacunas com `allow_gaps`, aviso e bloqueio no formulário.
3. **O3 parte 1:** `candle_problems`, importador com rejeições e alterações, trader recusando candle inválido; colunas na tela de dados de mercado.
4. **O3 parte 2:** relatório de outliers, `data_quality` no backtest, card "Qualidade dos dados" e alerta na triagem.
5. **O6 + O11:** tamanho de amostra e teste mínimo (avisos no formulário e na triagem).
6. **O7:** robustez da varredura e tabela cruzada.
7. **O10:** registro de listagens.

## 7. Critérios de aceite e testes
* O teste de truncamento passa para todas as estratégias do catálogo e falha para a estratégia de controle com vazamento.
* Candles malformados nunca são gravados nem chegam à estratégia; o job de importação mostra a contagem e as amostras, e o trader grava um evento de auditoria. Nenhum descarte silencioso.
* Uma reimportação que muda OHLC já guardado fica registrada em `candles_changed`.
* Um backtest sobre período com lacunas acima do limite é recusado sem `allow_gaps` e, com ele, mostra as lacunas no resultado.
* O aviso de cobertura do formulário fala só do período escolhido.
* O relatório de outliers acha o salto de uma série sintética e não marca uma série sem saltos.
* A varredura sintética de pico único sai `peak`; a suave sai `plateau`.
* Apenas mudanças aditivas na API; execuções antigas abrem com "—" nos campos novos.
* Tudo `Decimal` no domínio; `make check`, testes de integração, `npm run lint`, `typecheck`, `test`, `build` e `check:consistency` verdes; telas novas conferidas no navegador em 1366 px e 360 px.

## Ressalvas
Os números de Chan (≤ 5 parâmetros, 252 × parâmetros, 4 desvios-padrão, teste ≥ ⅓ do treino) são **regras práticas dele**, não resultados estatísticos, e foram derivados para estratégias de ações. Resultados de backtest não garantem retornos futuros; taxas, slippage, overfitting e efeitos específicos de cripto (24/7, liquidez fragmentada, deslistagens) podem piorar os resultados reais.
