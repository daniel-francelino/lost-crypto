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

## Ressalvas

Os retornos anuais e Sharpe do livro (10,9%, 17,8%, 26,2% etc.) vêm de pares de ETFs comprados e vendidos, sem custos, alguns com parâmetros escolhidos retrospectivamente. Não devem ser esperados em criptoativos. A afirmação de que entradas graduais nunca são ótimas baseia-se num exemplo estilizado com probabilidades constantes.
