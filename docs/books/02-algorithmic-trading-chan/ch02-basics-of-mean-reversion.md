# Livro 2 · Capítulo 2 — Fundamentos da reversão à média

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 39–62 foi lido.

## 1. Resumo do capítulo (pp. 39–62)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | A maioria das séries de preços se comporta como passeio aleatório geométrico; são os **retornos**, e não os preços, que oscilam em torno de zero. A reversão à média dos preços equivale à autocorrelação negativa dos retornos, que pode ser explorada. Poucas séries são estacionárias por natureza; outras podem ser **construídas** pela combinação de séries não estacionárias (cointegração). Reversão à média de *série temporal* (retorno à própria média) versus *transversal* (reversão de retornos relativos; cap. 4). | Quais séries podem ser negociadas por reversão à média. | 39–41 |
| C2 | **Duas interpretações equivalentes.** Reversão à média: a variação seguinte é proporcional à diferença entre a média e o valor atual → **teste ADF** para verificar se essa constante de proporcionalidade é zero. Estacionariedade: a variância dos log-preços cresce mais devagar que num passeio aleatório: `Var(τ) ∝ τ^(2H)`. **Expoente de Hurst H < 0,5** indica reversão, H = 0,5 passeio aleatório e H > 0,5 tendência → **teste da razão de variâncias** para H = 0,5. “Estacionária” não significa limitada a uma faixa. | Testes estatísticos. | 41, 44–45 |
| C3 | **ADF**: regressão de `Δy(t)` em `y(t−1)` (mais diferenças defasadas); estatística `λ / SE(λ)`, que deve ser negativa e inferior aos valores críticos de Dickey–Fuller (dependem do tamanho da amostra e da inclusão de constante/tendência; na prática, supõe-se tendência zero). Exemplo: USD.CAD, estatística −1,84 ante valor crítico de 90% igual a −2,594: não é estacionária. | Testar reversão à média. | 42–44 |
| C4 | **Hurst/razão de variâncias**: no exemplo USD.CAD, H = 0,49 e valor-p = 0,367; não é possível rejeitar a hipótese de passeio aleatório. | Testar estacionariedade. | 44–46 |
| C5 | **Meia-vida**: no processo de Ornstein–Uhlenbeck `Δy = λ·y(t−1) + μ + ε`, o preço esperado converge exponencialmente para `−μ/λ`, com **meia-vida = −ln(2)/λ**. Se λ > 0, não se deve criar estratégia de reversão à média; se λ ≈ 0, haverá poucas operações completas. A meia-vida fornece uma **escala temporal natural** (janela retrospectiva de um pequeno múltiplo da meia-vida), evitando otimizar exaustivamente essa janela. Os testes estatísticos são exigentes (≥ 90%); a rentabilidade prática exige menos certeza. Meia-vida de USD.CAD: cerca de 115 dias. | Velocidade da reversão e escolha da janela. | 46–48 |
| C6 | **Estratégia linear de reversão à média** (sem parâmetros): manter unidades em quantidade **proporcional ao z-score negativo** (preço menos média móvel, dividido pelo desvio-padrão móvel), com janela igual à meia-vida. O autor aponta problemas no exemplo: meia-vida calculada dentro da amostra (antecipação), capital sem limite e custos ignorados. A finalidade dos testes preliminares é usar cada barra e obter maior poder estatístico do que um backtest com poucas operações completas. | Estratégia sem otimização. | 48–50 |
| C7 | **Cointegração**: combinação linear estacionária de séries não estacionárias. **CADF** (Engle–Granger): regredir uma série na outra para obter a razão de hedge e testar os resíduos; o resultado depende de qual série é a variável explicativa. EWA/EWC: estatística −3,64 ante valor crítico de 5% −3,359. O teste **Johansen** aceita várias séries, não depende da ordem e devolve o número de relações cointegrantes e autovetores que podem servir como razões de hedge (o maior autovalor corresponde à menor meia-vida). Carteira EWA-EWC-IGE: meia-vida de cerca de 23 dias; estratégia linear com retorno anual de 12,6% e Sharpe 1,4, sem custos. | Construir carteiras estacionárias. | 50–60 |
| C8 | **Vantagens e desvantagens**: há muitas opções e, muitas vezes, uma explicação fundamental para a cointegração de um par e sua ruptura; horizontes curtos geram muitas operações e confiança estatística. Porém, a consistência pode levar a **excesso de confiança e alavancagem** (LTCM); uma ruptura ocorre quando a alavancagem está no máximo; **não é possível justificar logicamente stops de perda** (gestão de risco no cap. 8). | Riscos desse estilo. | 60–61 |

Os instrumentos do capítulo são moedas e ETFs, com posições compradas e vendidas. As referências a criptoativos são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Estratégias de reversão à média | ❌ | Só existem estratégias de tendência e rompimento (livro 1, cap. 7). |
| Testes de estacionariedade/reversão (ADF, Hurst, VR) | ❌ | Não há módulo estatístico para séries temporais; `analytics/domain/metrics.py` contém apenas métricas de desempenho. |
| Meia-vida | ❌ | Não é calculada (também proposta no livro 1, cap. 7 O3; este capítulo detalha o método). |
| Cointegração (CADF/Johansen) | ❌ e não utilizável tal como está | Exige posição vendida e vários ativos por bot. |
| Escolha da janela retrospectiva | ⚠️ | As janelas (`fast_period`, `slow_period`, `entry_period` etc.) são parâmetros do usuário e otimizadas por varreduras, exatamente a busca exaustiva que C5 procura evitar. |
| Dimensionamento linear/sem parâmetros | ❌ | O dimensionamento usa todo o capital ou `max_position_fraction`; não há posição proporcional ao sinal. |
| Controle de excesso de confiança | ✅ parcialmente | Existem limites na operação real e pausas por perda diária e drawdown (livro 1, cap. 6). |

## 3. Oportunidades

### O1 — Módulo estatístico de pesquisa: ADF, razão de variâncias, Hurst e meia-vida *(livro: C2–C5, pp. 41–48)*

* **Problema:** antes do backtest, não é possível determinar se um símbolo e intervalo temporal apresentam tendência, passeio aleatório ou reversão; varreduras acabam sendo usadas como substituto.
* **Proposta:** funções puras para preços ou log-preços de candles armazenados: estatística ADF com valores críticos de Dickey–Fuller; meia-vida `−ln2/λ`; expoente de Hurst pela relação de variância; estatística da razão de variâncias. Expor num endpoint somente de leitura e num painel de dados de mercado (“Este par tende ou reverte neste intervalo?”). Devolver `None` se a amostra for insuficiente ou a regressão degenerada.
* **Benefício:** indica qual família de estratégias pode se adequar ao par/intervalo e qual janela usar, com poder estatístico maior que o de um backtest (raciocínio de C6, p. 50). Também permitiria testar em criptoativos a afirmação do livro 1, cap. 7 de que a reversão à média é mais comum, sem pressupô-la.
* **Complexidade:** média (MQO, um pequeno sistema linear, tabelas de valores críticos; decidir a fronteira entre decimal e float, pois os testes precisam de `sqrt`, `log` e regressão. A regra “dinheiro nunca é float” aplica-se a valores monetários, não à estatística; ainda assim, documentar um único ponto de conversão). O teste Johansen fica de fora.
* **Riscos:** séries de criptoativos têm caudas pesadas, volatilidade e heterocedasticidade; um resultado ADF favorável numa janela pode não persistir; valores críticos dependem do modelo exato (com constante, sem tendência). Candles de 1 minuto sobrepostos não são observações independentes: amostrar no horizonte da estratégia (o autor usa fechamentos diários derivados de barras de minutos, p. 43).
* **Validação:** séries sintéticas de Ornstein–Uhlenbeck com λ conhecido (recuperar a meia-vida dentro de uma tolerância), passeios aleatórios (não rejeitar) e séries tendenciais (H > 0,5); reproduzir a identidade `−log(2)/λ`; garantir determinismo.

### O2 — Usar a meia-vida como escala temporal para reduzir varreduras exaustivas *(livro: C5, p. 47)*

* **Proposta:** quando uma estratégia tem parâmetro de janela retrospectiva, exibir a meia-vida da série como faixa sugerida e usar, por padrão, um múltiplo estreito nas varreduras. **Complexidade:** baixa após O1. **Risco:** só faz sentido para reversão à média; numa série tendencial a meia-vida é indefinida (λ ≥ 0), e a interface deve informar isso. **Validação:** teste de API/interface com série sintética.

### O3 — Estratégia linear de reversão à média, comprada apenas *(livro: C6, pp. 48–50)*

* **Proposta:** estratégia que mantém uma fração do orçamento de posição proporcional a `max(0, −z)`, usando como janela a meia-vida calculada. Assim, não há parâmetro ajustável além da janela derivada automaticamente. A estratégia só pode aumentar a posição abaixo da média e reduzi-la acima dela; o módulo de risco existente deve limitar a exposição, ao contrário da versão do livro, que também vende a descoberto e não limita o capital.
* **Problema resolvido:** acrescentar ao catálogo uma primeira estratégia de reversão à média sem busca de parâmetros.
* **Complexidade:** média. Hoje as estratégias emitem sinais discretos de COMPRA/VENDA para uma posição; posições proporcionais exigem ordens parciais (o motor hoje aceita uma compra seguida de uma venda) ou um sinal com tamanho-alvo, o que afeta o contrato de sinais, o motor e o módulo de risco.
* **Riscos:** no exemplo, o autor usa meia-vida calculada na própria amostra (antecipação) e precisa de capital ilimitado; stops de perda não são logicamente adequados a essa família (C8); a versão apenas comprada perde metade da vantagem e pode capturar um mercado em queda.
* **Validação:** teste de truncamento (livro 1, cap. 3 O5), calculando a meia-vida apenas com o prefixo; sensibilidade a custos; avaliação no segmento de teste. Adiar até O1 mostrar que certos pares criptoativos realmente revertem em algum intervalo.

### O4 — Aviso ao combinar reversão à média com stop ou escalonamento ilimitado *(livro: C8, p. 61; relacionado ao livro 1, cap. 6 C9)*

* **Proposta:** metadado de estratégia `family = mean_reversion`, aviso na interface sobre stop de perda e exigência de limites de exposição. **Complexidade:** baixa. Implementar depois de O3.

### Não aplicável ou adiado

Testes de cointegração (CADF, Johansen) e carteiras de pares/trios: o sistema é à vista, somente comprado, com um ativo por bot. Uma possibilidade específica de cripto que se encaixa na arquitetura atual é testar a estacionariedade de um **símbolo de razão negociável**, como ETH/BTC (um único mercado à vista cujo preço já é a razão). Isso é adaptação nossa, não do livro; depende de O1 e não exige posição vendida.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 diagnósticos (primeiro meia-vida, depois ADF/VR/Hurst) | alta | – | – | média | – |
| 2 | O2 sugestão de escala temporal | média | – | – | baixa | O1 |
| 3 | O4 aviso sobre família da estratégia | baixa | média | – | baixa | metadados da estratégia |
| 4 | O3 estratégia linear | média | média | – | média–alta | O1, mudança no contrato de sinais |

## 5. Arquivos afetados

Novo módulo puro em `analytics/domain/` (estatísticas de séries), `market_data/presentation/router.py` (endpoint de diagnóstico), `docs/openapi.json`, `strategies/domain/base.py` (metadados da família), `backtesting/domain/engine.py` e `strategies/domain/types.py` (apenas para O3), página de dados de mercado e linhas do gráfico no app (`lib/market-data/`), `check:consistency` e testes em `api/tests/unit`.

## 6. Plano incremental

1. Calcular meia-vida e Hurst/razão de variâncias numa série armazenada (sem interface), com testes de séries sintéticas.
2. Acrescentar ADF e valores críticos, endpoint de diagnóstico e painel no app.
3. Incluir sugestão de escala temporal nos formulários das estratégias.
4. Adicionar metadados de família e avisos.
5. Decidir sobre O3 depois de avaliar o que os diagnósticos indicam para pares reais.

## 7. Critérios de aceitação e testes

* Para série OU sintética com meia-vida *h*, estimativa dentro de tolerância definida; para passeio aleatório, não rejeitar na maioria das execuções, no nível indicado; para tendência, H > 0,5.
* Diagnósticos devolvem `None` com motivo explícito para séries curtas ou constantes; nunca devolvem NaN ou infinito.
* Nenhuma mudança nas estratégias, sinais, risco ou operação real existentes; Ruff, mypy e testes atuais passam.
* O texto da interface informa que um resultado estatístico favorável não garante lucro.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`), números como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil. A última migração é `0014_backtest_regime`. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| C5 meia-vida | ❌ | ✅ `analytics/domain/mean_reversion.py` (`half_life`: regressão `Δy = a + b·y₋₁`, só `Decimal`, mínimo de 100 pontos, `t` contra −2,86 de Dickey–Fuller **sem defasagens**), endpoint `GET /api/v1/market-data/half-life` (limite de 200.000 candles) e `components/market-data/half-life-card.tsx` na página de dados de mercado. |
| C2–C4 ADF completo, Hurst, razão de variâncias | ❌ | ❌ continuam. O teste atual é o ADF mais simples (sem termos defasados) e não há `H` nem `VR`. |
| O2 meia-vida como escala de janela | ❌ | ❌ continua: nenhum formulário usa a meia-vida. |
| O3 estratégia de reversão | ❌ | ❌ continua; o catálogo tem só `ema_crossover` e `donchian_breakout`. O desenho da estratégia de z-score está no [livro 1, cap. 7, Fase 2](../01-quantitative-trading-chan/ch07-special-topics.md). |
| O4 metadado de família | ❌ | ❌ continua (`STYLE`/`StrategyStyle` não existem); planejado no [livro 1, cap. 6, Fase C](../01-quantitative-trading-chan/ch06-money-and-risk-management.md). |
| Regime | ❌ | ⚠️ `analytics/domain/regime.py` descreve volatilidade e eficiência por tercis em cada backtest (migração 0014); é descritivo. |

**Achado importante sobre testes:** uma busca em `api/tests` (2026-11-01) **não encontra nenhum teste** de `half_life`, `regime_report`, `kelly`/`sizing`, `tail_risk` nem de `max_holding_candles`, embora os planos do livro 1 os descrevam. Qualquer critério de aceite abaixo que dependa desses módulos pressupõe a Fase 0.

### Fase 0 — Testes que faltam nos módulos já implementados · prioridade 0 · só testes

Antes de estender `mean_reversion.py`, cobrir o que existe, porque as fases seguintes mudam a mesma função.

* `tests/unit/test_half_life.py`: série AR(1) sintética com semente fixa e `φ = 0,95` (meia-vida teórica ≈ 13,5 barras) em 5.000 pontos, estimada dentro de uma tolerância declarada no teste; passeio aleatório → `stationary = False`; série em tendência (`b ≥ 0`) → `None`; menos de 100 pontos → `None`; série constante → `None`; preço ≤ 0 com `log=True` → `None`; sem `float` em código de produção (o ruído do teste pode nascer em `float` e ser convertido).
* `tests/unit/test_regime.py`, `test_sizing.py`, `test_tail_risk.py`, `test_time_exit.py`: os casos já listados nos planos do livro 1 (cap. 6 Fase A, cap. 7 Fases 1 e 4). Esta fase só **cria os arquivos**; o conteúdo está lá.
* `tests/integration/test_half_life.py`: endpoint com candles importados, 422 acima do limite, 422 com `start >= end`.
* **Aceite:** os testes passam sem alterar código de produção; se algum falhar, é bug encontrado e vai para o relatório do capítulo correspondente.

### Fase A — Razão de variâncias e expoente de Hurst (completa O1) · prioridade 1 · sem migração

* **A.1 Funções puras** em `analytics/domain/mean_reversion.py` (mesma convenção: `Decimal`, contexto de 40 dígitos, `None` com motivo): `variance_ratio(series, lag) -> VarianceRatio | None` (`VR(q) = Var(y_t − y_{t−q}) ÷ (q · Var(y_t − y_{t−1}))`, com a estatística `z` sob homocedasticidade e o aviso de que cripto tem volatilidade agrupada) e `hurst(series, lags) -> Decimal | None` (inclinação da regressão de `ln Var(y_{t+τ} − y_t)` contra `ln τ`, dividida por 2; livro p. 45). `lags` fixo e curto (proposta: 2, 4, 8, 16, 32). `H < 0,5` reverte, `H = 0,5` passeio, `H > 0,5` tendência.
* **A.2 Amostragem no horizonte da estratégia:** parâmetro `sample_every >= 1` (padrão 1) que toma um fechamento a cada *k* candles, porque candles de 1 minuto sobrepostos não são observações independentes (livro p. 43). A meia-vida existente passa a respeitá-lo também.
* **A.3 API:** campos **aditivos** em `HalfLifeOut` (`hurst`, `variance_ratio`, `sample_every`) e `sample_every` na consulta de `GET /market-data/half-life` (`market_data/presentation/router.py`, `MarketDataService.half_life`). O caminho continua `half-life` por compatibilidade; **decisão pendente** se vale criar `/series-diagnostics` e manter o antigo como atalho.
* **A.4 Front-end:** `lib/shared/market-data/market-data.api.ts` (schema com os campos novos nullish), `half-life-card.tsx` ganha duas linhas ("Hurst ≈ 0,47: tende a reverter" / "razão de variâncias") e um campo "amostrar a cada N candles"; texto "um resultado estatístico favorável não garante lucro". Esqueleto, erro com nova tentativa, vazio, dados; 360 px; `vitest` do schema e da frase.
* **A.5 Testes:** `tests/unit/test_mean_reversion_stats.py`: OU sintética → `H < 0,5` e `VR < 1`; passeio aleatório → `H ≈ 0,5` e `VR ≈ 1` dentro da tolerância; tendência → `H > 0,5`; série curta ou constante → `None` sem `NaN` nem infinito; `sample_every` reduz `n` como esperado.
* **Aceite:** o resultado atual da meia-vida não muda quando os campos novos não são lidos; mypy estrito e testes antigos passam.

### Fase B — Meia-vida como escala nos formulários (O2) · prioridade 2 · só front-end

* `lib/shared/strategies/half-life-hint.ts` (função pura, com teste): dado `half_life_bars` e o nome do parâmetro de janela, devolve a faixa sugerida (proposta: 0,5×, 1× e 2× a meia-vida, arredondada para inteiro ≥ o mínimo do `ParamSpec`) ou `null` quando não há reversão estimada.
* `components/backtests/backtest-form-page.tsx` e `sweep-page.tsx`: ao escolher símbolo, intervalo e datas, chamar o hook que o card de meia-vida já usa (`getHalfLife`; criar `useHalfLife` em `hooks/shared/` se ainda não houver) e mostrar **uma dica sob o campo de janela** ("meia-vida ≈ 14 barras; faixa sugerida 7–28") com botão "usar na varredura" que preenche a grade (`parseGridList` já aceita listas).
* Regra de honestidade da interface: se a série não é estacionária (`stationary_at_5pct = false`) ou a meia-vida é `null`, a dica diz isso e **não sugere faixa**. Para estratégias de tendência, a dica não aparece (depende do `STYLE` do livro 1, cap. 6, Fase C; sem ele, mostrar apenas no sweep de uma estratégia de reversão quando existir).
* **Testes:** `vitest` da função e do componente (sem meia-vida, não estacionária, faixa válida). **Aceite:** nenhuma chamada nova ao salvar o backtest; a dica nunca altera valores sem clique.

### Fase C — Estratégia de reversão (O3): fazer o que já está desenhado, não duplicar · prioridade 3

O desenho da estratégia de z-score (`mean_reversion_zscore`, cinco parâmetros, saída por tempo, teste de contrato por estilo) está pronto no [livro 1, cap. 7, Fase 2](../01-quantitative-trading-chan/ch07-special-topics.md) e no [livro 2, cap. 3](ch03-implementing-mean-reversion.md). **Este capítulo não cria outra estratégia.** A versão **linear** do livro (posição proporcional a `−z`) continua **adiada**, e o que ela exigiria fica registrado aqui para a decisão:

* `Signal` ganharia um `target_fraction` opcional (`strategies/domain/types.py`); o motor (`backtesting/domain/engine.py`) hoje rejeita COMPRA com posição aberta (`"already in position"`), então precisaria de ordens parciais; o trader (`trading/application/trader.py`) e o replay de paridade (`trading/application/parity.py`) precisariam do mesmo; `assess_signal` (`risk_management/domain/models.py`) teria de limitar o tamanho-alvo. É a mudança mais invasiva do catálogo e **só se justifica se a Fase A mostrar reversão real em algum par**.
* **Decisão pendente:** abrir esse trabalho só depois de `H < 0,5` e meia-vida estacionária em pelo menos um par e intervalo de interesse.

### Fase D — Aviso de família (O4) · prioridade 4 · já planejado

É exatamente o `StrategyStyle` e a dica de stop do [livro 1, cap. 6, Fase C](../01-quantitative-trading-chan/ch06-money-and-risk-management.md). Não há trabalho extra aqui além de conferir que o texto para `MEAN_REVERSION` cobre o alerta do livro (p. 61): *"escalonar sem limite e usar stop curto sai no pior momento; prefira o teto de risco"*.

### Estado da implementação (2026-11-01)

* **Fase 0 implementada:** `test_half_life.py`, `test_regime.py`, `test_sizing.py` (inclui `tail_risk`), `test_time_exit.py` e o teste de integração do endpoint. Todos passam **sem alterar código de produção**: nenhum bug apareceu nesses módulos. A reprodução dos Exemplos 6.1 e 6.2 do livro 1 (Kelly 2,528; `g` = 13,14% e 9,8%) está em `test_sizing.py`.
* **Fase A implementada:** `variance_ratio`, `hurst`, `sample_every` e `suggested_windows` em `analytics/domain/mean_reversion.py`; o mesmo endpoint `/market-data/half-life` ganhou os campos aditivos `hurst`, `variance_ratios` (lags 2, 4 e 8), `sample_every` e `suggested_windows`. Decisão adotada: **mesmo endpoint**, sem `/series-diagnostics`. Card atualizado com o campo "amostrar a cada N candles". Testes: `test_mean_reversion_stats.py`.
* **Fase B implementada, com um desvio:** a faixa vem do **servidor** (`suggested_windows`, em `Decimal`: 0,5×, 1× e 2× a meia-vida, só quando a série é estacionária a 5%), para o app não fazer aritmética. A dica aparece no formulário de backtest (`half-life-hint.tsx`); o botão "usar na varredura" só existe para `mean_reversion_zscore` (`lib/backtests/half-life-hint.ts`), que **ainda não existe**: hoje a dica é só informativa. A chamada da API foi para `lib/shared/market-data/half-life.api.ts` porque módulos do app não importam uns dos outros.
* **Fases C e D:** nada a implementar neste capítulo (a estratégia e o `StrategyStyle` seguem os planos do livro 1, cap. 7 Fase 2 e cap. 6 Fase C).

### Ordem, dependências e estimativa

0 → A → B; C e D seguem os planos do livro 1. Estimativa grosseira: Fase 0 ≈ 1,5 dia (só testes); A ≈ 2 (1,5 back, 0,5 front); B ≈ 1 (front). Nenhuma fase deste capítulo mexe no banco.

### Decisões pendentes (para o operador)

* Se Hurst e razão de variâncias entram no mesmo endpoint (proposta) ou em um novo.
* Lags do Hurst (proposta: 2, 4, 8, 16, 32) e o padrão de `sample_every`.
* Faixa sugerida da janela (proposta: 0,5×, 1× e 2× a meia-vida).
* Se o valor crítico de −2,86 (5%, constante, sem defasagens) é conferido na fonte antes de ser exibido como veredito; hoje ele é só **indicativo**.

### Fora do escopo (decidido)

ADF com termos defasados e Johansen/CADF (exigem carteira de vários ativos e posição vendida), estratégia linear de reversão enquanto a Fase A não mostrar evidência, qualquer sugestão automática aplicada a bot.

### Critérios de aceite gerais

Nenhum comportamento de ordem, de risco ou de estratégia existente muda; nenhum `float` no domínio; as respostas atuais de `/market-data/half-life` continuam válidas; `make check` e a suíte de integração verdes; `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas conferidas em 1366 px e 360 px. Um resultado estatístico favorável não prova lucro em cripto.

## Ressalvas

Todos os números de desempenho (retorno anual de 12,6%, Sharpe 1,4 e meias-vidas de 115 e 23 dias) vêm de exemplos anteriores a 2013 com moedas e ETFs, **sem custos de transação** (p. 49), parcialmente dentro da amostra, e não dizem nada sobre criptoativos. O próprio autor considera a estratégia-exemplo impraticável (p. 50).
