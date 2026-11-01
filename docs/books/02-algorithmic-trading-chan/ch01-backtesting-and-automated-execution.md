# Livro 2 · Capítulo 1 — Backtesting e execução automatizada

*Algorithmic Trading: Winning Strategies and Their Rationale*, Ernest P. Chan (Wiley, 2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

Nota de leitura: foram lidas as pp. 1–38. O levantamento de plataformas de software (pp. 25–36: Deltix, Apama, integrações com MATLAB, IDEs de código aberto, colocalização, multithreading e CEP) foi considerado apenas quanto aos princípios.

## 1. Resumo do capítulo (pp. 1–38)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Faça o backtest de cada estratégia por conta própria**: os resultados dependem dos detalhes de implementação (tipo de ordem, preço que a aciona); o mesmo programa deve ser usado na execução. Uma estratégia publicada oferece um período genuinamente fora da amostra **após a publicação**. Siga o método científico: hipótese → backtest → refinamento. | Afirmações difíceis de reproduzir ou sensíveis aos detalhes. | 1–3 |
| C2 | O **viés de antecipação** (*look-ahead bias*) é um erro de programação que só pode existir no backtest; se o backtest e a operação real usam o *mesmo programa* com dados diferentes, ele não ocorre. | Vazamento de informação futura. | 4 |
| C3 | **Viés de seleção de dados** (*data-snooping bias*): excesso de parâmetros livres. Detecte-o com dados fora da amostra; ajustar a estratégia após um resultado ruim fora da amostra transforma esses dados em dados de treino. Use **validação cruzada** (vários subconjuntos); prefira Sharpe alto e duração máxima de drawdown curta, pois essas características tendem a sobreviver à validação cruzada. Use poucos parâmetros **e poucas regras**; **modelos lineares são menos sujeitos à seleção de dados** que os não lineares (um modelo não linear tem uma aproximação linear; justifique por que ela não serve). A parcimônia de Occam também se aplica às distribuições: suponha normalidade, salvo forte motivo em contrário (argumento do autor). A combinação de fatores com pesos iguais (escores z ou postos com sinal) é citada como robusta (citação de Kahneman; a “fórmula mágica” de Greenblatt, 30,8% contra 12,4% de retorno anual entre 1988 e 2004, é um exemplo do autor). | Sobreajuste. | 4–7 |
| C4 | O **teste walk-forward** é a verificação final fora da amostra: negociação em paper ou, de preferência, negociação real com alavancagem mínima; **pela experiência do autor, a maioria dos traders ficaria satisfeita se o Sharpe real superasse metade do Sharpe do backtest**. | Validação final. | 7 |
| C5 | **Armadilhas nos dados**: desdobramentos e dividendos (ajustar o histórico e os dados em tempo real); viés de sobrevivência (afeta sobretudo a reversão à média comprada, menos o momentum; exemplo de comprar o maior perdedor); **preços primários e consolidados** (preços de leilão de abertura/fecho versus transações em outras bolsas; máximas e mínimas consolidadas são exageradas e podem inflar os resultados de reversão à média); **dependência da bolsa nas cotações cambiais** (usar dados da bolsa em que se negocia; os spreads variam); **restrições a vendas a descoberto** (ativos difíceis de tomar emprestados, proibições e regras de uptick); **contratos contínuos de futuros** (lacunas na rolagem criam P&L falso; ajustes retroativos por preço e por retorno não podem ser ambos corretos; preços negativos); **preço de liquidação versus último preço**; **preços assíncronos em spreads**. | Backtests inflados ou pouco realistas. | 7–16 |
| C6 | **Significância estatística por teste de hipóteses**: hipótese nula = retorno médio verdadeiro igual a zero; estatística de teste = retorno diário médio; valor-p. Três formas de construir a distribuição nula: (1) supor normalidade: estatística = `média/desvio-padrão × √n` (equivalente a Sharpe diário × √n), com valores críticos 1,282 / 1,645 / 2,326 / 3,091 para p = 0,10 / 0,05 / 0,01 / 0,001; (2) **Monte Carlo** sobre preços simulados com os quatro primeiros momentos da série real (no exemplo, 1.166 de 10.000 simulações tiveram resultado igual ou melhor, ou seja, confiança de apenas 88%); (3) **datas de entrada aleatórias**, mantendo o número de operações e a duração das posições (Lo et al.; no exemplo, 0 de 100.000 tiveram resultado igual ou melhor). Os métodos podem discordar porque cada um define aleatoriedade de forma diferente. Ressalva: valores-p indicam P(R | H0), não P(H0 | R). Mais operações completas implicam maior significância. | “Este backtest pode ser acaso?” | 15–22 |
| C7 | **Quando não fazer backtest** (sinais de alerta): retorno alto, mas Sharpe 0,3 e drawdown de dois anos; estratégia comprada que não supera comprar e manter pelo **índice de informação**; “comprar as ações mais baratas” sem dados livres de viés de sobrevivência; rede neural com cerca de 100 nós; backtests de alta frequência cujos resultados dependem da reação dos demais participantes. | Evitar esforço desperdiçado. | 22–24 |
| C8 | **O backtest prevê o futuro?** Ele pressupõe propriedades estatísticas constantes; mudanças de regime (decimalização em 2001, crise de 2008, Reg NMS em 2007, alterações na regra de uptick) podem tornar inúteis os dados anteriores; dados recentes também não oferecem garantia. | Estabilidade da vantagem estatística. | 24–25 |
| C9 | **Escolha da plataforma**: uma plataforma que usa o mesmo programa no backtest e na operação real evita erros de transcrição e viés de antecipação; processamento orientado a eventos (ticks) versus barras; a latência vem principalmente dos dados e da confirmação da corretora (confirmações de varejo podem levar segundos); colocalizar num servidor em nuvem pode sobretudo proteger contra falhas de energia e Internet, sem necessariamente reduzir a latência (verificar com ping); multithreading, CEP e feeds de notícias. | Operação do sistema. | 25–36 |
| C10 | Recapitulação dos pontos principais: o teste walk-forward supera outras defesas contra seleção de dados; prefira modelos simples; valide com o benchmark adequado. | – | 37–38 |

As observações sobre ações, futuros e moedas aplicam-se especificamente a esses mercados. As observações sobre criptoativos são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| C1 mesmo código de estratégia no backtest e na operação real | ✅ | Há uma classe `Strategy` por tipo, usada por `run_backtest` e pelo trader; a lógica de execução e stops é compartilhada (`execution/domain/fills.py`, `risk_management/domain/stops.py`). Os *loops* do motor são diferentes (`backtesting/domain/engine.py` e `trading/application/trader.py`), e o dimensionamento de risco existe apenas na operação real (livro 1, cap. 5). |
| C2 viés de antecipação | ✅ por projeto, ❌ sem teste | A estratégia vê apenas o candle fechado; a execução ocorre na abertura seguinte. Não há teste automatizado de truncamento (livro 1, cap. 3 O5). |
| C3 validação cruzada | ❌ | Existe apenas uma divisão fixa entre treino e teste (`segments.py`). |
| C3 simplicidade | ✅ | No máximo quatro parâmetros por estratégia. |
| C4 walk-forward/operação real com alavancagem mínima | ✅ parcialmente | A etapa paper é obrigatória (`live_min_paper_days`) e há limites para a operação real, mas não se compara o Sharpe real com o do backtest. |
| C5 consistência da bolsa | ✅ | Os candles vêm do mesmo adaptador da corretora usado para executar (`ExchangeRegistry.market_data(cfg.exchange`); os dados são armazenados por bolsa. |
| C5 sobrevivência | ❌ | Não há tratamento de ativos removidos da listagem (livro 1, cap. 3). |
| C5 desdobramentos/dividendos/futuros/vendas a descoberto | n/a | Cripto à vista, apenas posições compradas. |
| C5 preços consolidados versus primários | n/a | Uma única bolsa; não são usados índices agregados. |
| C6 testes de significância | ❌ | Não há valor-p, Monte Carlo, teste de entradas aleatórias nem teste de significância do Sharpe. |
| C6 número de operações completas | ✅ | `round_trips` é exposto, mas não está ligado à confiança estatística. |
| C7 triagem de sinais de alerta | ❌ | Não há alertas automáticos para Sharpe baixo com drawdown longo ou desempenho inferior a comprar e manter. Existe `buy_and_hold_return_pct`. |
| C8 mudanças de regime | ❌ | Não são monitoradas; a divisão cronológica treino/teste retém dados recentes e ajuda parcialmente. |
| C9 mesmo programa | ⚠️ | A estratégia é a mesma; a orquestração é diferente. |
| C9 resiliência/hospedagem | ⚠️ | Ver livro 1, cap. 4 (runbook de continuidade). |
| C9 latência | ✅ | As barras têm duração de 1 minuto ou mais; latência de segundos é irrelevante nesses horizontes. |

## 3. Oportunidades

### O1 — Significância estatística do backtest *(livro: C6, pp. 15–22)*

* **Problema:** o retorno positivo do backtest é apresentado sem indicar se pode ser acaso; buscas de parâmetros agravam o problema.
* **Proposta (em etapas):**
  1. *Estatística de teste gaussiana*: `Sharpe diário × √n` (n = número de observações de retorno), comparada aos valores críticos do livro; apresentar valor-p aproximado. É simples e tem forma fechada.
  2. *Teste de entradas aleatórias*: reposicionar aleatoriamente o mesmo número de entradas, com a mesma distribuição de duração das posições, na série de preços observada; informar a fração de simulações cujo retorno médio é igual ou superior ao observado. Requer gerador determinístico com semente (a configuração já contém `seed`).
  3. *Monte Carlo sobre preços simulados* (compatíveis com os quatro momentos): deixar para depois; exige um gerador de distribuições (sistema de Pearson) e muito processamento.
* **Benefício:** quantifica a possibilidade de acaso. O exemplo do próprio livro mostra que os testes discordam; por isso, suas definições devem ser apresentadas. **Complexidade:** baixa na etapa 1; média na etapa 2. **Riscos:** retornos de cripto têm autocorrelação e caudas pesadas, então a aproximação gaussiana pode ser otimista; muitos testes numa busca aumentam falsos positivos (testes múltiplos, tratados nos livros seguintes); valor-p não é a probabilidade de a estratégia funcionar (o livro ressalta isso, p. 22). **Validação:** séries sintéticas conhecidas, com e sem vantagem; reproduzir os valores críticos do livro; garantir determinismo com semente fixa.

### O2 — Estrutura de walk-forward e validação cruzada *(livro: C3, C4, pp. 4–7)*

* **Proposta:** substituir a divisão única por *k* intervalos cronológicos (para uma estratégia de tendência, escolher parâmetros na janela anterior e avaliar na seguinte) e apresentar a dispersão dos resultados entre os intervalos. A validação temporal não deve embaralhar os dados. Relaciona-se ao livro 1, cap. 3 O8 (backlog B-WALK-FORWARD) e ao livro 5 (validação cruzada com purga), que trata corretamente o vazamento entre intervalos; **não implementar antes da análise do livro 5**.
* **Complexidade:** alta.

### O3 — Sinalizadores de triagem dos resultados *(livro: C7, pp. 22–24)*

* **Proposta:** bloco de “sinais de alerta” em cada backtest: Sharpe abaixo de um limite com duração longa de drawdown; retorno inferior ao de comprar e manter (estilo índice de informação, usando o benchmark existente); poucas operações completas para sustentar significância; muitos parâmetros em relação ao tamanho da amostra (livro 1, cap. 3 O6). Exibir avisos, sem bloquear. **Complexidade:** baixa quando Sharpe e duração do drawdown estiverem disponíveis. **Validação:** testes unitários para cada alerta. Os limites dos exemplos do autor devem ser configuráveis.

### O4 — Monitor de Sharpe real versus backtest *(livro: C4, p. 7)*

* **Proposta:** para um bot com histórico suficiente em paper ou real, calcular o Sharpe realizado a partir das amostras de patrimônio e compará-lo com o Sharpe do backtest; exibir a razão e a observação de que, pela experiência do autor — não por uma norma —, um valor ≥ 0,5 é aceitável. **Complexidade:** baixa a média. **Riscos:** amostras reais curtas são ruidosas; exibir o tamanho da amostra. **Dependências:** métrica de Sharpe (livro 1, cap. 2 O1) e relatório de paridade (livro 1, cap. 5 O1).

### O5 — Registro transparente das avaliações fora da amostra *(livro: C1, C3, pp. 3–4 · adaptação)*

* **Problema:** alterar repetidamente os parâmetros após observar o segmento de teste transforma esse segmento em dados de treino (alerta central do livro).
* **Proposta:** registrar, em cada execução, quais segmentos o operador consultou ao escolher parâmetros e contar quantas execuções usam a mesma janela de dados; avisar quando o segmento de teste já tiver sido usado muitas vezes. Versão prática: mostrar junto ao resultado o número de execuções para o mesmo par, intervalo e janela. **Complexidade:** baixa. **Validação:** teste da API.

### O6 — Índice de informação com benchmark adequado *(livro: C7, pp. 22–23)*

* **Proposta:** para estratégias compradas, calcular os retornos excedentes em relação à estratégia de comprar e manter o mesmo par e apresentar seu índice de informação (a fórmula consta no livro 1, cap. 2). Já há suporte parcial por `buy_and_hold_return_pct`. **Complexidade:** baixa.

### Não aplicável ou adiado

Desdobramentos e dividendos, preços primários e consolidados, dependência da bolsa nas cotações cambiais, regras de venda a descoberto, contratos contínuos de futuros, preços de liquidação, escolha da plataforma (a plataforma já existe), CEP, feeds de notícias e multithreading. A colocalização para **resiliência** é abordada no livro 1, cap. 4.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O6 índice de informação | média | – | – | baixa | livro 1, cap. 2 O1 |
| 2 | O3 sinais de alerta | alta | média | – | baixa | Sharpe, duração do drawdown |
| 3 | O1 etapa 1: significância gaussiana | alta | – | – | baixa | Sharpe |
| 4 | O5 contador de reutilização do teste | média | – | – | baixa | – |
| 5 | O1 etapa 2: entradas aleatórias | alta | – | – | média | O1 etapa 1 |
| 6 | O4 monitor da operação real versus backtest | – | média | média | baixa–média | relatório de paridade |
| 7 | O2 walk-forward/validação cruzada | alta | – | – | alta | livro 5 |

## 5. Arquivos afetados

`analytics/domain/` (funções de significância e índice de informação), `backtesting/application/service.py` e `router.py` (campos aditivos de resultado e contadores de execuções), `backtesting/domain/` (simulação de entradas aleatórias com semente), testes em `api/tests/unit`, `docs/openapi.json` e página de detalhes do backtest no app.

## 6. Plano incremental

1. Implementar os pré-requisitos das métricas no livro 1, cap. 2 (Sharpe e duração do drawdown).
2. Adicionar índice de informação e significância gaussiana aos resultados.
3. Incluir o bloco de sinais de alerta.
4. Implementar teste de entradas aleatórias com semente.
5. Acrescentar contador de reutilização e monitor da operação real versus backtest.
6. Implementar walk-forward após analisar o livro 5.

## 7. Critérios de aceitação e testes

* Os valores críticos reproduzem a Tabela 1.1; uma série com vantagem inserida tem valor-p pequeno e uma série de puro ruído não.
* O teste de entradas aleatórias é determinístico para uma semente fixa e tem tempo de execução limitado.
* Execuções antigas, sem os novos campos, continuam sendo exibidas; Ruff, mypy e os testes existentes passam.
* O texto da interface deixa claro que valor-p não é garantia.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`; qualquer exceção é declarada na fase), números e dinheiro como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil, fronteiras entre módulos protegidas por `tests/unit/test_architecture.py`. A última migração existente é `0014_backtest_regime`; cada fase que mexe no banco usa a **próxima livre** no momento de implementar. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| C2 viés de antecipação | ❌ sem teste | ✅ `tests/unit/test_lookahead.py` roda o teste de truncamento em toda estratégia do catálogo. |
| C5 sobrevivência | ❌ | ⚠️ o worker grava um snapshot diário das listagens (`/market-data/listings`); deslistagens anteriores continuam desconhecidas. |
| C6 significância | ❌ | ❌ continua: `Metrics` tem Sharpe, mas nenhum `t`, valor-p ou teste de acaso. |
| C7 / O3 triagem de sinais de alerta | ❌ | ✅ **no app**: `lib/backtests/screening.ts` (limiares em `CHAN_THRESHOLDS`: Sharpe < 1, profundidade e duração do drawdown, poucas operações por ano, exposição, comparação com comprar e manter, fração de teste, amostra) mostrada por `screening-panel.tsx`. É só front: não há campo na API e os limiares não são configuráveis. |
| O6 índice de informação | ⚠️ | ✅ `information_ratio` já está em `Metrics` (livro 1, cap. 2). **O6 está feito.** |
| C3 validação cruzada | ❌ | ❌ continua: uma divisão treino/teste, `periods.py` (métricas por ano/trimestre) e a robustez de vizinhos nas varreduras. |
| C4 Sharpe real × backtest | ❌ | ❌ continua, mas `BotService.performance` já devolve as **mesmas métricas** (inclusive Sharpe) para um bot; falta escolher o backtest equivalente. |
| O5 contador de reutilização | ❌ | ⚠️ `count_prior_trials` já conta execuções anteriores, mas só para varreduras (`SweepOut.prior_trials`); uma execução simples não mostra nada. |

**Achado novo que molda o plano:** `Metrics` é gravada como JSON e os campos novos entram como opcionais com valor `None` (é assim que os índices do livro 1, cap. 2 entraram). Logo, **a estatística gaussiana (Fase A) não exige migração**; as demais, só quando há bloco novo por execução.

### Fase A — Significância gaussiana (O1, etapa 1) · prioridade 1 · sem migração

Objetivo: dizer "este Sharpe é distinguível de acaso a p < X?", pela tabela do livro (`média/desvio × √n`, valores críticos 1,282 / 1,645 / 2,326 / 3,091).

* **A.1 Back-end, função pura** `api/src/modules/analytics/domain/significance.py` (sem frameworks, contexto de 40 dígitos como `risk_ratios.py`): `sharpe_t_stat(annual_sharpe, annualization_factor, periods)` = `Sharpe_por_barra × √n = Sharpe_anual × √(n ÷ N_T)` (o Sharpe de `risk_ratios.py` usa 365 dias; `Metrics.annualization_factor` e `return_periods` já trazem `N_T` e `n`). `significance_level(t) -> Decimal | None` devolve o **menor p da tabela** que `t` supera (0,10; 0,05; 0,01; 0,001) ou `None`. Sem amostra mínima própria: herda os `None` de `risk_ratios` (menos de 30 retornos ou 30 dias).
* **A.2 Campos aditivos em `Metrics`** (`analytics/domain/metrics.py`): `sharpe_t_stat: Decimal | None = None` e `significance_p: Decimal | None = None`, preenchidos em `compute_metrics`. Entram automaticamente em backtests, em cada segmento (treino/teste), nos períodos e nos **bots** (`BotService.performance`). Atualizar `MetricsOut` (`analytics/presentation/schemas.py`), `api/docs/openapi.json` e rodar `npm run api:types`.
* **A.3 Front-end:** `metricsSchema` em `lib/shared/analytics.ts` ganha os dois campos como `nullish`; em `components/shared/metrics/metrics-grid.tsx` um tile "Significância do Sharpe" com **texto** ("p < 0,05" / "não distinguível de acaso"), nunca só cor; o aviso fixo "valor-p não é a chance de a estratégia funcionar". Em `lib/backtests/screening.ts` uma flag `significance` (`Warning` quando `t < 1,645`, ou seja, não passa a 5%) com limiar novo em `CHAN_THRESHOLDS` (`minTStat: "1.645"`) e teste `vitest`.
* **A.4 Testes:** `tests/unit/test_significance.py`: os quatro valores críticos classificam corretamente (`t` logo abaixo e logo acima de cada limite); série sintética com vantagem inserida → `p` pequeno e série de ruído puro → `None` na maioria das sementes; `t` cresce com `√n` para o mesmo Sharpe anual; amostra curta → `None`. Em `test_risk_ratios.py`, nada muda.
* **Aceite:** execuções antigas continuam abrindo (campos `null`, tile mostra "—"); nenhum número existente muda; `make check` e `npm run lint/typecheck/test/build/check:consistency` verdes.

### Fase B — Contador de reutilização do teste (O5) · prioridade 2 · sem migração

* **B.1 Back-end:** `BacktestStore.count_prior_runs(config) -> int` (`backtesting/application/ports.py` e `infrastructure/repository.py`, ao lado de `count_prior_trials`): execuções com mesma exchange, símbolo, intervalo e `strategy_type` cujo período **se sobrepõe** ao da execução, excluída ela mesma. `BacktestService.get` chama e `BacktestOut.prior_runs: int` (`presentation/router.py`) carrega o valor. É consultado na leitura, não gravado: execuções antigas funcionam sem migração. Custo: um `COUNT` por detalhe; aceitável.
* **B.2 Front-end:** `lib/backtests/backtests.api.ts` (campo nullish). Em `backtest-detail-page.tsx`, junto às métricas de treino/teste, o texto "Esta janela já foi usada em N execuções" e, em `screening.ts`, a flag `reuse` (`Warning` a partir de `CHAN_THRESHOLDS.maxWindowReuse`, proposta 10; **decisão pendente**). Só aparece quando há divisão treino/teste.
* **B.3 Testes:** integração em `tests/integration` (três execuções na mesma janela → `prior_runs = 2` na terceira; janelas disjuntas não contam; outro símbolo não conta) e `vitest` da flag.

### Fase C — Teste de entradas aleatórias (O1, etapa 2) · prioridade 3 · migração própria

* **C.1 Back-end, função pura** `api/src/modules/backtesting/domain/random_entries.py`: recebe os fechamentos alinhados à curva, as durações em barras de cada operação completa (derivadas dos fills já gravados), o custo por operação (`fee_rate` e `slippage_bps` dos dois lados), `seed` e `simulations`. Para cada simulação sorteia as barras de entrada com `random.Random(seed)` mantendo número de operações e durações; o retorno é a soma dos retornos por operação **menos o mesmo custo**. Prefixos de `ln(fechamento)` calculados uma vez em `Decimal`, de modo que cada simulação só soma. Resultado: `{simulations, as_good_or_better, fraction, trades, seed, overlap_allowed: true, note}`. Menos de 10 operações → `None` com motivo. Limites fixos no módulo (`MAX_SIMULATIONS = 2_000`, `MIN_TRADES = 10`) para o tempo ficar previsível; roda em `asyncio.to_thread`.
* **C.2 Persistência:** migração `NNNN_backtest_significance` (`ALTER TABLE backtest_runs ADD COLUMN significance JSONB NULL`, `downgrade` remove; rodar `alembic check`) pelo mesmo caminho do `regime` (migração 0014): `backtesting/application/ports.py`, `infrastructure/orm.py`, `infrastructure/repository.py`, `application/service.py` (`_execute`, junto de `regime_report`), `presentation/router.py` (`SignificanceOut` em `BacktestOut`), OpenAPI. A `seed` da execução (hoje `0` por padrão e "decorativa" porque o modelo de preenchimento é determinístico) passa a ser usada de fato; atualizar o comentário em `backtesting/domain/models.py`.
* **C.3 Front-end:** schema nullish em `backtests.api.ts`; `components/backtests/significance-card.tsx` em `backtest-detail-page.tsx` depois de `RiskReportCard`: "X de N simulações com entradas aleatórias igualaram ou superaram este resultado", a semente, o número de operações, **a explicação de que este teste e o da Fase A podem discordar** (cada um define "acaso" de um jeito, livro p. 22) e o aviso de que valor-p não é garantia. Esqueleto, erro, vazio ("operações insuficientes"), dados; 360 px.
* **C.4 Testes:** `tests/unit/test_random_entries.py`: determinismo com semente fixa; durações e número de operações preservados; série de passeio aleatório → `fraction` próxima de 0,5 dentro de tolerância declarada; série com vantagem inserida → `fraction` baixa; menos de 10 operações → `None`; tempo limitado (`MAX_SIMULATIONS`). Integração: execução completa grava o bloco; execução antiga abre com `null`.
* **Aceite:** com a mesma semente, o resultado é idêntico entre execuções; nenhuma métrica existente muda; `alembic upgrade head` e `downgrade -1` funcionam em banco com dados.

### Fase D — Sharpe real × backtest (O4) · prioridade 4 · sem migração

* **D.1 Back-end:** `GET /api/v1/bots/{bot_id}/backtest-comparison?run_id=<opcional>`. O serviço mora em `trading/application/` (ao lado de `parity.py`, que já combina bot e backtester; o teste de arquitetura impede `bots` de importar `backtesting`). Sem `run_id`, usa a execução concluída **mais recente equivalente**: mesma exchange, símbolo, intervalo, `strategy_type`, parâmetros e limites de risco, achada por `BacktestStore.find_matching(config)` (método novo). Resposta `RealizedVsBacktestOut`: `{run_id | null, realized: {sharpe, return_periods, days}, backtest: {sharpe}, ratio, min_periods, hint}`; `ratio = realizado ÷ backtest`, `None` quando algum Sharpe é `None` ou o do backtest é ≤ 0. `hint` cita a regra prática de Chan (≥ 0,5; **observação do autor, não norma**). Sem backtest equivalente → corpo com `run_id: null` e o motivo, não erro. Leitura para qualquer papel.
* **D.2 Front-end:** `getBacktestComparison` e schema em `lib/bots/bots.api.ts`, `QueryKey.Bots.backtestComparison(id)`, hook em `hooks/bots/use-bots.ts`; card na aba "Desempenho" (`BotTab.Performance`) com os dois Sharpes, a razão, o **tamanho da amostra real** e o seletor "comparar com outro backtest". Esqueleto, erro, vazio ("nenhum backtest equivalente: rode um com esta configuração", com link que pré-preenche via `backtest-prefill.ts`), dados.
* **D.3 Testes:** unitário da razão (backtest ≤ 0 → `None`, amostra curta → `None`); integração com um bot paper com snapshots e um backtest equivalente; 404 para bot inexistente.
* **Depende de** nada novo (usa `BotService.performance`); alimenta o monitor de deterioração do [cap. 4, Fase B](ch04-mean-reversion-stocks-etfs.md).

### Fase E — Walk-forward e validação cruzada (O2) · **só desenho; depois do livro 5**

Não codar antes de analisar a validação com purga e embargo do livro 5. Desenho mínimo para quando chegar a hora: generalizar `backtesting/domain/segments.py` de "uma divisão" para *k* janelas cronológicas; para cada janela, ajustar na anterior e avaliar na seguinte; mostrar a dispersão (mínimo, mediana, máximo) por métrica. O custo cresce com *k*; reaproveitar a fila de execuções das varreduras.

### Estado da implementação (2026-11-01)

Fases **A, B, C e D implementadas**; a E continua só desenho.

* **A** — `analytics/domain/significance.py`; campos `sharpe_t_stat` e `significance_p` em `Metrics` (sem migração); tile e flag `significance` no app. Testes: `test_significance.py`.
* **B** — `count_prior_runs` e `BacktestOut.prior_runs` (só no detalhe, a lista devolve `null`); flag `reuse` com limite 10. Teste de integração em `test_data_quality_flow.py`.
* **C** — `backtesting/domain/random_entries.py`, migração `0015_backtest_significance`, `BacktestOut.significance.random_entries`, card no detalhe. Decisões adotadas: entradas **podem se sobrepor**; 1.000 simulações (teto 2.000); mesmo custo de ida e volta nos dois lados; o resultado é "indisponível" com motivo abaixo de 10 operações. Testes: `test_random_entries.py` (caminho disponível) e integração (caminho indisponível, com a série oscilante do teste).
* **D** — `trading/domain/comparison.py` e `trading/application/comparison.py` (protocolos, ligados no `container.py`), `GET /bots/{id}/backtest-comparison`, card na aba "Desempenho". O backtest equivalente é o mais recente concluído com os mesmos parâmetros de estratégia, preferindo o que usou os limites de risco do bot. Testes: `test_realized_vs_backtest.py` e integração.
* **Desvios do plano:** o texto da comparação mora em `lib/bots/backtest-comparison.ts`, com teste; `BacktestStore.matching_runs` foi o método novo em vez de `find_matching`.
* **Decisões ainda abertas:** valor-p contínuo (fica sem `float`, só a faixa da tabela).

### Ordem, dependências e estimativa

A → B → D → C → E. A e B são independentes e pequenas; D alimenta o cap. 4; C é a única com migração e a mais cara de testar. Estimativa grosseira: A ≈ 1,5 dia (1 back, 0,5 front); B ≈ 1; D ≈ 2 (1,5 back, 0,5 front); C ≈ 3; E fora do corte.

### Decisões pendentes (para o operador)

* Valor-p contínuo, além da faixa da tabela: exigiria `erfc` e portanto **uma** conversão para `float` isolada em `significance.py` (a regra "dinheiro nunca é `float`" não vale para estatística, mas o domínio hoje é só `Decimal`). Proposta: ficar com a faixa da tabela, sem `float`.
* Limite de reutilização da janela (proposta: 10 execuções) e se a flag bloqueia algo (proposta: não, só avisa).
* Entradas aleatórias com sobreposição permitida (proposta, mais simples) ou posições sem sobrepor.
* Quantas simulações por execução (proposta: 1.000, teto 2.000).

### Fora do escopo (decidido)

Monte Carlo sobre preços simulados com os quatro momentos (sistema de Pearson), correção por testes múltiplos (livros 3 e 5), qualquer bloqueio de execução por falta de significância, e as plataformas de software do capítulo.

### Critérios de aceite gerais

Nenhuma execução antiga deixa de abrir; nenhum número existente muda; nenhum `float` no domínio (salvo a decisão acima, se aprovada); `make check`, suíte de integração em Postgres, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas novas conferidas em 1366 px e 360 px; o texto da interface deixa claro que significância estatística não garante retorno.

## Ressalvas

Todos os limites (exceto os valores críticos) são heurísticas práticas de Chan. Os exemplos de Monte Carlo e entradas aleatórias referem-se a uma estratégia de momentum em futuros e não são generalizáveis. A significância estatística do backtest não garante retornos futuros; mudanças de regime podem anulá-la (p. 24).
