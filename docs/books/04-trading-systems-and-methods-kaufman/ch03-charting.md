# Livro 4 · Capítulo 3 — Gráficos

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 79–82 e 144–146 foram lidas. Os títulos das seções pp. 83–150 (gráficos de barras de Dow, formações, linhas de tendência, padrões de um dia, continuação, acumulação/distribuição, objetivos de preço, candles e evolução de padrões) foram percorridos. As cerca de 60 páginas com descrições de padrões **não foram lidas** em detalhe. A análise de padrões é subjetiva e o projeto a exclui (ver [livro 3, cap. 1](../03-evidence-based-technical-analysis-aronson/ch01-objective-rules-and-their-evaluation.md)).

## 1. Resumo do capítulo (conteúdo lido)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Todo sistema de negociação começou com um gráfico; sinais passados devem sempre ser vistos num gráfico (“a aparência de uma operação estranha pode poupar muito aborrecimento e dinheiro”). | 79 |
| C2 | Mercados têm um “caráter” (padrões habituais, como fundos em V em gado, topos arredondados em algodão e novas máximas seguidas de recuos rápidos no S&P). O autor refere-se a commodities dos anos 1970, sem apresentar evidência nesta seção. | 79–80 |
| C3 | Há várias interpretações válidas para o mesmo gráfico (frequência, data inicial, horizonte); análises gráficas publicadas podem ajudar a *causar* padrões repetidos (profecia autorrealizável). | 80 |
| C4 | **Causas dos padrões gráficos**: hábitos humanos; por exemplo, ordens agrupam-se em **números redondos** (dólares inteiros e depois 50¢/25¢) em ações e futuros; público entra na hora errada (“corrida geral”); extrapolação excessiva de até ~10%; psicologia de massas (bolhas e crashes). | 81–82 |
| C5 | Tendências são **mais fáceis de ver retrospectivamente**; sinal tendencial aparece no ponto de maior incerteza. Seguidores de tendência só precisam acertar **30–35%** das vezes, pois ganhos médios excedem perdas médias. Tendências longas são mais confiáveis que curtas (efeito diário é pequeno perante ruído); gráficos semanais revelam tendências ocultas nos diários. | 144–145 |
| C6 | Sinais confirmatórios que convergem no mesmo preço têm mais peso; **falhas de padrões** também sinalizam (rompimento falhado/“armadilha de alta ou baixa” é negociado no sentido oposto: “esforço e resultado” de Wyckoff); **mudança de caráter** (reações maiores dentro da tendência) sinaliza saída. | 145–146 |
| C7 | Resultados de candles citados de Bulkowski: candles melhores fecham no terço inferior da barra; padrões funcionam melhor em mercados de baixa e com volume maior; pavios muito longos ou candles altos têm desempenho superior. | 144 |

O capítulo 4 transforma alguns conceitos em sistemas e cita classificações de Bulkowski.

## 2. Diagnóstico (verificado no código e na interface)

| Conceito | Situação | Evidência |
|---|---|---|
| Ver operações no gráfico | ✅ | Detalhes de backtest mostram candles/curva patrimonial, operações e ordens (`candle-chart-rows.ts`, aba de operações). Não foi confirmado se sinais aparecem sobre os candles. |
| Agrupamento de ordens em números redondos | ❌ | Stops/alvos não consideram isso (`stop_loss_pct` é percentual do fecho de entrada). |
| Taxa de acerto como meta | ⚠️ | `win_rate_pct` é métrica principal; há `profit_factor` e `avg_trade_pnl`, mas não relação ganho/perda, expectativa por operação ou taxa de acerto de equilíbrio. |
| Falhas de padrão como sinal | ❌ | Não há. |
| Confirmação em vários intervalos | ❌ | Bot opera num único intervalo (ver cap. 19). |
| Padrões gráficos subjetivos | n/a (excluídos) | – |

## 3. Oportunidades

### O1 — Relação ganho/perda, expectativa e taxa de acerto de equilíbrio *(livro: C5, p. 144)*

* **Problema:** taxa de acerto de 35% é normal para estratégia de tendência, segundo o livro; exibi-la em destaque pode induzir a avaliação errada.
* **Proposta:** acrescentar `payoff_ratio = ganho médio / perda média`, `expectancy per trade` (líquida, após custos; próxima de `avg_trade_pnl`) e `breakeven_win_rate = 1 / (1 + payoff_ratio)`, com tamanho amostral. Exibir taxa de acerto junto à taxa de equilíbrio. **Complexidade:** muito baixa (funções puras sobre `round_trip_pnls`). **Validação:** casos calculados à mão.
* **Ressalva:** relação ganho/perda é ruidosa com poucas operações.

### O2 — Verificar se operações aparecem sobre candles no app *(livro: C1, p. 79)*

Verificar se entradas, saídas, stops e sinais rejeitados aparecem no gráfico de candles (bots e backtests); se não, adicionar marcadores. **Complexidade:** baixa (linhas do gráfico no frontend). Ver gráfico dos sinais passados é a recomendação do livro.

### O3 — Posicionar stop/alvo em relação a números redondos *(livro: C4, p. 81 · hipótese)*

O livro diz que ordens se agrupam em preços redondos. Stop num nível evidente pode executar com slippage pior (também livro 2, cap. 7, caça a stops). **Hipótese H-ROUND:** com execuções reais registradas (livro 1, cap. 5 O4), comparar slippage em stops/alvos redondos versus níveis próximos não redondos e decidir se convém deslocá-los. Sem mudança antes de medir. **Complexidade:** baixa após haver dados.

### O4 — Regra objetiva para rompimento falhado *(livro: C6, p. 146 · hipótese)*

Definir objetivamente: rompimento Donchian que regressa ao canal em *k* candles → sair/inverter. À vista e comprado, pode ser regra de **saída** da estratégia Donchian (“sair antes se o rompimento falhar”). **H-FAILED-BREAKOUT:** testar no fluxo varredura → melhor de N → validação; não assumir vantagem a priori. **Complexidade:** baixa a média.

### Não aplicável

Descrições de formações, desenho de linhas de tendência, teoria de Dow, nomes de candles e objetivos de preço de padrões.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 ganho/expectativa/equilíbrio | média | – | – | muito baixa | – |
| 2 | O2 verificar sobreposição no gráfico | – | – | média | baixa | revisão frontend |
| 3 | O4 experimento de rompimento falhado | baixa | – | – | baixa–média | fluxo do livro 3 |
| 4 | O3 estudo de números redondos | – | baixa | – | baixa | registros de slippage |

## 5. Arquivos afetados

`analytics/domain/metrics.py`, `analytics/presentation/schemas.py`, `docs/openapi.json`, cartões de métricas e gráficos no app (`components/backtests`, `components/bots`), `strategies/domain/donchian_breakout.py` (apenas O4) e testes.

## 6. Plano incremental

1. Métricas de ganho e equilíbrio.
2. Revisão de marcadores no gráfico.
3. Experimentos O3/O4 somente após ferramentas de evidência do livro 3.

## 7. Critérios de aceitação e testes

* Ganho/perda, expectativa e taxa de equilíbrio conferem com cálculos manuais; retornar `None` sem perdas ou operações.
* Comportamento das estratégias existentes não muda; Ruff, mypy e testes passam.

## Ressalvas

A maior parte do capítulo é análise gráfica subjetiva e anedotas de 1970–2000; relatos sobre padrões não foram verificados nem lidos. Taxa de acerto de 30–35% é afirmação geral sobre tendências, não número observado em cripto.
