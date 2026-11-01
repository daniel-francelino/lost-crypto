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

## Ressalvas

Todos os números de desempenho (retorno anual de 12,6%, Sharpe 1,4 e meias-vidas de 115 e 23 dias) vêm de exemplos anteriores a 2013 com moedas e ETFs, **sem custos de transação** (p. 49), parcialmente dentro da amostra, e não dizem nada sobre criptoativos. O próprio autor considera a estratégia-exemplo impraticável (p. 50).
