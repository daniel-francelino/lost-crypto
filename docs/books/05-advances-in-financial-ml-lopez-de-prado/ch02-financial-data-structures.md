# Livro 5 · Capítulo 2 — Estruturas de dados financeiros

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 23–41 foram lidas (tipos de dados, barras padrão e orientadas à informação, séries de vários produtos incluindo o truque de ETF, pesos PCA e rolagem de futuros, atributos de amostragem e filtro CUSUM, lista de exercícios). Trechos de código foram consultados superficialmente; fórmulas de barras de desequilíbrio e sequências foram lidas no nível da definição.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Não consumir conjunto de dados processado por terceiros; partir dos dados brutos para descobrir atributos informativos. Quatro tipos: **fundamentais** (divulgados com atraso; alinhar à data de divulgação, não ao fim do período; valores retroativamente preenchidos/revistos geram look-ahead; “quantidade substancial de resultados publicados não pode ser reproduzida após alinhar os dados corretamente”), **de mercado**, **analíticos** (derivados, caros e opacos) e **alternativos**. | Alinhamento e look-ahead. | 23–25 |
| C2 | **Evitar barras temporais**: mercados não processam informação em intervalos constantes (hora após abertura é mais ativa que meio-dia); barras temporais sobreamostram períodos de pouca atividade e subamostram os ativos. Séries amostradas por tempo exibem autocorrelação, heterocedasticidade e não normalidade. | Escolha de amostragem. | 25–26 |
| C3 | **Barras de ticks** (amostrar a cada N transações; Mandelbrot–Taylor: retornos de número fixo de transações se aproximam mais da normal), **barras de volume** (a cada N unidades; evita arbitrariedade de fragmentação de ordens; Clark, 1973: aproximação maior a Normal IID), **barras de dólar** (a cada N unidades monetárias negociadas; robustas a variação de preço e ações corporativas; quantidade diária é mais estável ao longo dos anos que ticks/volume para tamanho fixo — fig. 2.1; tamanho pode ser adaptado dinamicamente). Cuidado com negócios de leilão que parecem um único tick. | Amostragem por atividade. | 26–28 |
| C4 | **Barras orientadas à informação**: barras de desequilíbrio de ticks, volume e dólar (amostrar quando o desequilíbrio acumulado com sinal exceder a expectativa; sinais pela **regra do tick** `b_t = b_{t−1}` se `Δp = 0`, caso contrário `sign(Δp)`; expectativas por médias móveis exponencialmente ponderadas de barras anteriores) e **barras de sequências** (amostrar quando a sequência mais longa de um lado exceder sua expectativa). Ideia: amostrar mais quando chegam operadores informados. | Amostragem por informação do fluxo de ordens. | 29–32 |
| C5 | **Séries de vários produtos**: eventos que alteram a série (rolagens, dividendos, rebalanceamentos, pesos do spread) criam quebras estruturais. **Truque de ETF**: construir série do valor de US$ 1 investido numa cesta/spread (positiva, inclui carry e custos), para o código tratar a cesta como um produto à vista; custos de rebalanceamento, bid-ask e volume (limitado pelo componente menos ativo) são acompanhados separadamente. **Pesos PCA** para razões de hedge; **rolagem de futuro único**: subtrair gaps de rolagem acumulados dos preços; preços rolados podem ficar negativos, então formar série não negativa com retornos calculados sobre preços brutos anteriores. | Séries contínuas para futuros/spreads. | 32–37 |
| C6 | **Amostragem de atributos**: redução da série por amostragem (linspace ou uniforme) versus **amostragem por evento**: posicionar apostas após evento (quebra estrutural, sinal extraído, fenômeno de microestrutura) e deixar o modelo aprender se é acionável. **Filtro CUSUM simétrico**: `S⁺_t = max(0, S⁺_{t−1} + y_t − E_{t−1}[y_t])`, `S⁻_t = min(0, S⁻_{t−1} + y_t − E_{t−1}[y_t])`; amostrar barra quando `S⁺ > h` ou `S⁻ < −h`, depois zerar; para primeiras diferenças, `E_{t−1}[y_t] = y_{t−1}`. Ao contrário do cruzamento de bandas de Bollinger, **não dispara repetidamente enquanto a série oscila perto do limite** — “exige uma sequência completa de comprimento h”. | Escolher observações para modelar. | 38–40 |
| C7 | Exercícios comparam barras de ticks/volume/dólar em autocorrelação, estabilidade da contagem semanal, variância das variâncias e estatísticas de Jarque–Bera (o leitor deve obter os resultados; não são fornecidos). | Método de comparação empírica. | 40–41 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Barras temporais | ✅ (únicas) | `Candle` é amostrado por tempo (timeframes 1m–1d); toda a pilha presume intervalos fixos. |
| Barras de volume/dólar | ❌ | `Candle` contém volume (volume-base e talvez volume em moeda cotada — verificar `market_data/domain/models.py`), mas apenas klines de intervalo fixo são importados. Klines Binance incluem volume do ativo cotado e número de negócios; barras de ticks/volume/dólar só podem ser aproximadas grosseiramente com candles. Barras precisas exigem negócios agregados (`aggTrades`) e `isBuyerMaker`, que a plataforma não importa. |
| Regra do tick / desequilíbrio do fluxo | ❌ | Sem dados no nível de negócio. |
| Look-ahead/alinhamento | ✅ (candles) | Horário de fechamento do candle é conhecido; execução ocorre na abertura seguinte. Dados fundamentais/alternativos não são usados. |
| Rolagens/futuros contínuos | n/a | Somente spot. |
| Amostragem por evento (CUSUM) | ❌ | Estratégias avaliam cada candle; não há amostrador de eventos. |
| Gaps/integridade de candles | ❌ | Ver livro 4, cap. 22, O1. |

## 3. Oportunidades

### O1 — Diagnósticos de volume em dólar com candles existentes, antes de novos tipos de barra *(livro: C2, C3, pp. 25–28)*

* **Proposta:** nos diagnósticos de série, calcular por timeframe: (a) **distribuição do volume cotado por candle** e coeficiente de variação entre horas e dias da semana; (b) **autocorrelação de retornos** e retornos absolutos; (c) **normalidade** dos retornos (curtose, Jarque–Bera) dos candles temporais; (d) mesmas estatísticas para **barras de dólar aproximadas**, agregando candles de 1 minuto até atingir limite monetário (se houver dados 1m). Isso permite verificar com os dados da plataforma se a alegação do livro (amostragem por atividade tem propriedades estatísticas melhores) vale para o par negociado.
* **Motivo:** barato, somente leitura, e decide se vale o trabalho dispendioso com dados de negócios (O2). **Complexidade:** baixa–média. **Riscos:** agregar candles de 1m é aproximação (cada candle cobre faixa de preços); pode ultrapassar o limite dentro do candle. Identificar apenas como diagnóstico. **Validação:** série sintética com heterocedasticidade conhecida deve mostrar melhora com amostragem em dólar; resultados temporais permanecem iguais.

### O2 — Barras de dólar (e, opcionalmente, desequilíbrio) como produto de pesquisa baseado em negócios *(livro: C3, C4, pp. 27–32)*

Importar negócios agregados Binance para pares selecionados, armazená-los de forma compacta (Parquet ou tabelas particionadas; volume de dados alto) e criar **barras de dólar** com limite escolhido para igualar a quantidade média diária de barras ao timeframe atual. Opcionalmente adicionar **barras de desequilíbrio em dólar** com regra do tick (Binance fornece `isBuyerMaker`, indicando lado agressor, melhor que regra do tick). Estratégias continuariam baseadas em candles a menos que optassem por isso; backtester precisaria de objeto semelhante a candle (OHLCV + início/fim), compatível com modelo `Candle` se “timeframe” passar a ser “tipo de barra + limite”.

**Custos/riscos:** muito armazenamento e tempo de importação (`aggTrades` de BTCUSDT tem centenas de milhões de linhas ao longo de anos), limites de requisição, qualidade de dados e mudança maior no motor: timestamps deixam de estar numa grade fixa, então indicadores “por dia” ou anualização precisam considerar tempo por barra; taxas/slippage por tempo também mudam. **Recomendado somente se O1 indicar benefício** e existir pipeline de evidências. **Complexidade:** alta.

### O3 — Filtro CUSUM de eventos como ferramenta de pesquisa (eventos para rótulos e filtros de sinais) *(livro: C6, pp. 38–40)*

Implementar filtro CUSUM simétrico no domínio analytics (função pura: série de preços logarítmicos ou retornos + limite → timestamps de eventos). Usos: (a) amostrar barras para rotulagem/treino dos modelos a partir do cap. 3; (b) **filtro de sinal** para estratégias existentes: agir só quando evento CUSUM confirmar movimento de tamanho `h` (reduz sinais repetidos enquanto preço fica no limite); (c) exibir eventos no gráfico. `h` pode ser múltiplo da volatilidade móvel (livro usa h fixo, mas cita variantes). **Complexidade:** baixa. **Riscos:** parâmetro extra, interação com regras de tendência; tratar variante filtrada como hipótese via pipeline (**H-CUSUM-GATE**). **Validação:** passeio aleatório monotônico dispara em intervalos fixos; série oscilando em torno de nível não dispara novamente (contraste com Bollinger); teste de truncamento.

### O4 — Regras de alinhamento de dados como invariável documentada para novos feeds *(livro: C1, pp. 23–24)*

Se funding rates, open interest, dados on-chain ou sentimento forem adicionados, cada valor deve ser indexado pelo momento em que se tornou **publicamente disponível**, nunca pelo período que descreve; armazenar timestamp de divulgação e revisões (vintage). Exemplos cripto (nossos): funding é publicado em horários específicos; métricas on-chain são agregadas diariamente por provedores que podem revisá-las; índices de sentimento têm atraso de publicação. Registrar regra nas diretrizes de dados do projeto. **Complexidade:** documentação. **Validação futura:** testes que garantam que atributos em t nunca usem valores com divulgação posterior a t.

### Não aplicável

Dados fundamentais/de analistas, satélite e outros alternativos, rolagens de futuros e truque ETF (somente spot), pesos PCA para spreads, tratamento de negócios de leilão em ações. Truque ETF poderá ser relevante com spreads entre ativos ou pairs trading (livros 1/2); não agora.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Invariável de alinhamento (documentação) O4 | alta (futuro) | – | – | doc. | – |
| 2 | Diagnósticos de volume em dólar O1 | média | – | – | baixa–média | módulo de diagnósticos |
| 3 | Filtro CUSUM O3 | média | – | – | baixa | – |
| 4 | Barras de dólar/desequilíbrio por negócios O2 | média–alta | – | – | alta | resultados O1 |

## 5. Arquivos afetados

`analytics/domain/` (diagnósticos, CUSUM), `market_data` (importação/armazenamento de negócios, somente O2), `backtesting/domain` (abstração de barras, somente O2), página de diagnósticos do app, documentação/diretrizes de dados, testes.

## 6. Plano incremental

1. Documentar regra de alinhamento; implementar função CUSUM e testes.
2. Diagnósticos comparando estatísticas de candles (e barras de dólar agregadas de 1m, se disponíveis).
3. Decidir sobre importação de negócios após analisar os resultados.

## 7. Critérios de aceitação e testes

* CUSUM dispara exatamente quando deriva acumulada cruza ±h e reinicia; não dispara repetidamente em nível plano; determinístico.
* Diagnósticos produzem mesmos números de fixtures calculadas manualmente; somente leitura; ruff, mypy e testes existentes aprovados.

## Ressalvas

As alegações de superioridade estatística de barras de ticks/volume/dólar vêm de artigos citados (Mandelbrot–Taylor, Clark, Easley et al.) e sobretudo de ações/futuros; o livro apresenta uma figura, sem tabela com resultados cripto. Barras de desequilíbrio e de sequência dependem de dados de negócios e expectativas exponencialmente ponderadas cujos parâmetros (tamanho inicial esperado, janela) são arbitrários e podem tornar instável a contagem de barras; o livro reconhece parâmetros, mas não apresenta estudo de robustez nessas páginas.
