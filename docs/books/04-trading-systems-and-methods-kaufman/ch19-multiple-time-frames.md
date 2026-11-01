# Livro 4 · Capítulo 19 — Múltiplos períodos gráficos

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foram lidas as pp. 833–841; as últimas páginas (842–844: sistema KST de Pring e resumo) não foram lidas. O conteúdo de Gann/Fibonacci de Krausz (838–841) foi lido apenas para entender sua estrutura; baseia-se em geometria não testável e foi excluído.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Sistemas que combinam dados **intradiários, diários e semanais**: usar um período longo para identificar a tendência (tendências são identificadas melhor em períodos longos) e um curto para escolher a entrada (que exige resposta rápida). Um único período apresenta problemas: períodos muito curtos = ruído; apenas semanal = direção, mas alto risco e entrada ruim. | Tendência versus momento da entrada. | 833 |
| C2 | **Ajuste de dois períodos**: o período do indicador de timing deve ser **muito menor que o período da tendência**; se a operação de tendência durar cerca de 23 dias úteis, o oscilador deve buscar uma entrada melhor nos primeiros 3–5 dias (10–20%). O lucro isolado do oscilador não importa, pois o ganho vem do componente de tendência; usar somente o **primeiro** sinal de sobrevenda após o sinal da tendência. Exemplo (euro, média móvel de 60 dias, estocástico de 3 dias): esperar a sobrevenda transformou um ganho de US$ 2.075 em US$ 6.200 em uma operação, mas em outra a entrada foi pior (“nem toda entrada melhora”); um estocástico de 14 dias gerou entrada atrasada. Entradas contra o movimento curto também tendem a sofrer menos slippage. | Timing de correção dentro de uma tendência (cf. cap. 9). | 833–835 |
| C3 | **Triple Screen de Elder**: três períodos relacionados por um fator de aproximadamente 5 (por exemplo, horário, diário e semanal); Tela 1 (semanal): a inclinação de um MACD/média exponencial de 13 semanas define a direção da operação; Tela 2 (diário): um oscilador (Force Index `= volume × (fechamento − fechamento anterior)`, suavizado em 2 dias; ou bull/bear power do Elder-Ray em relação a uma média exponencial de 13 dias; ou um estocástico) encontra recuos para compra em uma tendência de alta; Tela 3 (intradiário): entrada por ordem stop. **Stop:** abaixo da mínima do dia de entrada ou da mínima anterior; mover para o ponto de equilíbrio assim que houver espaço e, em seguida, proteger 50% do maior lucro alcançado. | Um processo concreto de múltiplos períodos. | 835–838 |
| C4 | **Leis de Krausz** (por exemplo, “períodos maiores prevalecem sobre os menores”, “níveis de suporte/resistência convergem entre períodos”): baseadas na geometria de Gann e em Fibonacci, não são testáveis como formuladas. **Padrão robusto** a preservar: em um sistema de tendência, períodos de cálculo mais longos geram maior lucro por operação, maior confiabilidade e, proporcionalmente, menos operações; os retornos por operação devem formar um **padrão contínuo em relação ao tempo médio de permanência** — expectativa útil para avaliar resultados de testes. | Uma expectativa de robustez. | 838–841 |

As observações sobre cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Um único período por bot | ✅ (limitação) | Um bot tem um `timeframe`; `StrategyContext` carrega um candle; o trader e o backtester recebem uma única série. |
| Filtro de tendência de período superior | ❌ | Não é possível sem uma segunda série. |
| Reamostragem de períodos menores para maiores | ❌ | Os candles são armazenados por período conforme importados; não existe helper de agregação (`Timeframe` disponível: 1m, 5m, 15m, 1h, 4h, 1d). |
| Proteção contra look-ahead com múltiplos períodos | n/a | Exigiria cuidado (usar somente candles fechados do período superior). |
| Timing de entrada em recuos | ❌ | Consulte O1 do cap. 9. |
| Política de stop: abaixo da mínima de entrada, ponto de equilíbrio e trailing de 50% | ❌ | Os stops são percentuais fixos; não há trailing stop em `risk_management/domain/stops.py` (`stop_price` e `take_profit_price` estáticos). |

## 3. Oportunidades

### O1 — Filtro de tendência de período superior agregando os próprios candles da estratégia (experimento) *(livro: C1–C3, pp. 833–837)*

* **Proposta:** permitir que uma estratégia declare um período superior opcional (múltiplo do período do bot; o livro sugere fator próximo de 5) e fazer o framework **agregar candles fechados do período inferior em candles fechados do período superior** dentro do estado da estratégia (sem uma segunda fonte de dados e sem look-ahead, pois são usados apenas candles superiores concluídos). Uma entrada comprada permitida pela regra-base só seria aceita se a tendência no período superior (inclinação da EMA ou da KAMA) estivesse em alta. Isso mantém o contrato de “fluxo de um único candle” do trader e do backtester.
* **Benefício:** incorpora a ideia central de múltiplos períodos do livro a um custo moderado; espera-se reduzir entradas contra a tendência. **Complexidade:** média (agregação alinhada aos limites UTC, aquecimento, testes contra look-ahead e parâmetros da estratégia).
* **Riscos:** mais um par de parâmetros; entradas atrasadas; filtros de tendência costumam reduzir o número de operações; o efeito precisa passar pelo pipeline completo de evidências. **H-MTF-FILTER.** **Validação:** o teste de truncamento é essencial (a agregação não pode usar o candle superior ainda em formação); testes de alinhamento (candles horários formando exatamente um candle diário); avaliar efeitos sobre operações e drawdown.

### O2 — Opções de trailing stop (ponto de equilíbrio e fração do lucro máximo) *(livro: C3, p. 838)*

* A regra de stop do livro tem três etapas: stop inicial abaixo da mínima de entrada/anterior, mover ao ponto de equilíbrio quando possível e, depois, proteger 50% do melhor lucro aberto. O módulo de risco oferece apenas stop e alvo fixos. Um **trailing stop** (percentual abaixo do maior preço desde a entrada ou fração do lucro máximo) é uma regra de proteção padrão e testável, e também se alinha a stops baseados em ATR (cap. 20).
* **Ressalvas:** o próprio livro (cap. 8) alerta que stops e realização de lucro podem destruir a cauda longa dos sistemas de tendência; portanto, comparar com e sem essa regra (execução de ablação, O7 do cap. 8). Ordens stop nativas da corretora em operação ao vivo exigem mecanismo para substituir a ordem conforme o trailing avança. **Complexidade:** média (motor, ambiente de paper trading e ordens do trader/corretora ao vivo; regra de execução para gaps). **Validação:** testes unitários determinísticos da lógica do trailing e paridade entre backtest e paper trading.

### O3 — Verificação de expectativa: retornos por operação versus tempo de permanência são monotônicos *(livro: C4, p. 838)*

Em uma varredura de um parâmetro de uma estratégia de tendência, plotar o retorno líquido por operação, a taxa de acerto e o número de operações em função do **tempo médio de permanência**; o livro espera um padrão suave de aumento do lucro por operação e redução da quantidade de operações à medida que o período aumenta. Um resultado irregular é um alerta de sobreajuste ou de problema nos dados. Amplia a análise de robustez por varredura (O1 do cap. 5). **Complexidade:** baixa.

### Não aplicável

Geometria de Gann e leis de Fibonacci de Krausz; KST de Pring (não lido); detalhes do Force Index e do Elder-Ray além da ideia de um oscilador na Tela 2.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Expectativa de monotonicidade O3 | média | – | – | baixa | varreduras |
| 2 | Filtro de período superior O1 | média | – | – | média | helpers, pipeline |
| 3 | Trailing stops O2 | – | média | média | média | motor + projeto ao vivo |

## 5. Arquivos afetados

`strategies/domain/` (helper de agregação, parâmetros opcionais), `backtesting/domain/engine.py`, `risk_management/domain/stops.py` (trailing), `trading/application/trader.py` e adaptador da corretora (substituição de stop nativo), formulários do app, testes (truncamento, alinhamento).

## 6. Plano incremental

1. Visão da expectativa na varredura (sem alterar a estratégia).
2. Helper de agregação com testes contra look-ahead; experimento com o filtro.
3. Trailing stop primeiro no backtest/paper; operação ao vivo somente depois de comprovar a paridade.

## 7. Critérios de aceitação e testes

* Candles agregados iguais aos de uma importação direta do período superior em um conjunto de dados de referência; o filtro nunca usa um candle superior inacabado (teste de truncamento).
* Execuções do trailing stop e saídas determinísticas e idênticas no backtest e no paper trading.
* Os padrões deixam o comportamento existente inalterado; ruff, mypy e testes aprovados.

## Ressalvas

Os exemplos de desempenho são operações individuais em gráficos de futuros. Nas páginas lidas, o livro não apresenta estatísticas agregadas para sistemas de múltiplos períodos; portanto, qualquer benefício para cripto não está comprovado.
