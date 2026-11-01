# Livro 4 · Capítulo 9 — Momentum e osciladores

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** lidas pp. 369–379 (momentum), 385–389 (osciladores, RSI e variantes) e 426 (comentários finais). Índice de divergência (384–385), estocástico/outros osciladores (389–404), momentum com suavização dupla, velocidade/aceleração, técnicas híbridas e divergência (404–425) **não** foram lidos nem resumidos.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Momentum = variação de preço num intervalo** (`M(n) = p_t − p_{t−n}`); velocidade = momentum dividido por `n`; aceleração (variação do momentum) é ainda mais sensível. Momentum **não é volatilidade** (ida e volta dá momentum zero e volatilidade alta). Terminologia varia: “ROC” muitas vezes significa momentum. | Definições. | 369–371 |
| C2 | **Momentum versus média móvel**: momentum não tem atraso no mesmo sentido e atinge pico antes da média móvel de mesma duração, ao custo de ruído; cruzar zero é basicamente equivalente à virada da média, portanto serve como sinal tendencial, com pequena banda ao redor de zero. Momentum percentual compara mercados melhor, mas é inadequado para futuros ajustados retroativamente. “Momentum” também pode significar preço menos média móvel (“força relativa”), com formato e extremos iguais. | Posição do momentum entre ferramentas tendenciais. | 372–375 |
| C3 | **Escolher janela**: usar valores amostrais ou marcar topos/fundos no gráfico e usar metade a duas vezes a distância média entre picos. Momentum/osciladores servem sobretudo para **timing** em relação a tendência maior. **Momento de entrada**: momentum curto (ex. 6 dias) dentro de tendência de 30–50 dias oferece entrada em cerca de três dias. | Usar momentum dentro de tendência. | 376 |
| C4 | **Operar contra extremos** (sobrecompra/sobrevenda): momentum rápido oscila em torno de zero; lento comporta-se como tendência. Limites podem ser visuais, fração do momentum máximo ou **múltiplo do desvio-padrão do indicador** (2σ ≈ 5% dos valores além). Entradas: agressiva (ao cruzar limite), confirmação menor (primeira virada após cruzar), maior (retorno pelo limite), por tempo (após n dias fora). Saídas variam de “entrar no oposto” a **“sair no momentum zero”** (premissa de reversão à média) ou “permitir movimento prolongado”. Escala do momentum **muda com a volatilidade** (faixa ±30 em 2006 versus anos posteriores), então limites fixos se deslocam. | Opções de regras e problema de escala. | 377–379 |
| C5 | **Osciladores** são momentum normalizado a faixa limitada (ex.: dividir pelo máximo móvel; variação de US$ 2 em 2006 e US$ 8,77 em 2011 na Amazon dão ambos 0,52); busca valores altos nos picos e baixos nos fundos, seguidos de reversão. | Extremos ajustados à volatilidade. | 385–386 |
| C6 | **RSI de Wilder**: `RSI = 100 − 100/(1+RS)`, `RS = AU/AD` em 14 dias por atualização de média exponencial; limites 30/70. Mais estável que momentum porque considera todas as variações; RSI 14 dias permanece extremo em movimento sustentado. Dados indicam topos/fundos de RSI perto de **72 e 32**, tornando 70/30 “próximos demais para selecionar”; **1,5 desvios-padrão** é compromisso sugerido entre frequência e risco. Variantes suavizadas usam variação n-diária em vez de 1 dia; **oscilador contrário pela variação do RSI** (`RSI_t − RSI_{t−k} > a`); **CMO** `100·(Su − Sd)/(Su + Sd)`; e **RSI de 2 dias** (substituir variação diária pela de dois dias, maior suavização e volatilidade). | Especificidades de osciladores. | 386–389 |
| C7 | **Comentários finais**: indicadores em intervalos curtos são instáveis; **indicadores de momentum usados contra a direção do preço têm alto risco**; melhor usá-los como **ferramenta de timing numa estratégia tendencial**, ajustando período para extremos ocorrerem com frequência desejada. Ex.: operação tendencial mantida ~20 dias e espera de até dois dias para entrada; criar oscilador (3 períodos em candles diários, 10 em horários) que dê ao menos um, preferivelmente dois, sinais de sobrevenda em cada janela de dois dias, favorecendo “comprar recuos, não altas”. | Uso prudente. | 426 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Momentum, RSI, CMO e osciladores | ❌ | Não existem em `strategies/domain`. |
| Timing de entrada em recuos dentro de tendência | ❌ | Ambas estratégias entram na abertura após candle-sinal. |
| Limites em unidades de volatilidade | ❌ | Não há auxiliar de desvio/ATR. |
| Reversão contra tendência | ❌ | Não presente. |
| Stops/ordens limite para timing de entrada | ⚠️ | Entradas são ordens a mercado na abertura seguinte; sem simulação de limite. |

## 3. Oportunidades

### O1 — Timing de recuo para estratégias tendenciais (experimento) *(livro: C3, C7, pp. 376, 426)*

Após sinal tendencial, esperar até `k` barras por oscilador rápido (ex.: RSI de 3 períodos ou momentum curto) atingir sobrevenda e então entrar; se não ocorrer dentro de `k`, entrar mesmo assim ou ignorar sinal (duas variantes). Preço médio pode melhorar apenas se recuos forem frequentes; custo é entrada atrasada/perdida. Implementa “comprar recuos dentro de tendência” para sistema à vista comprado.

**Benefício:** possível redução de preço adverso/drawdown inicial, compatível com restrição comprada. **Complexidade:** média (auxiliar oscilador, estado e parâmetros `k`, período, limite). **Riscos:** perder captura de cauda (livro 4, cap. 8 alerta que atrasar/filtrar entrada reduz chance); mais três parâmetros e correlação com estratégia-base. **H-PULLBACK-ENTRY**: testar apenas pelo fluxo de evidências, contando os parâmetros. **Validação:** truncamento; preço médio de entrada versus base, quantidade de operações e sinais ignorados.

### O2 — Auxiliares de osciladores com limites escalados pela volatilidade *(livro: C4–C6, pp. 377–388)*

Funções puras: momentum n-barras, momentum normalizado (por amplitude móvel), RSI Wilder por atualização média (`Decimal`), CMO e limites como **múltiplos do desvio-padrão móvel** (sugestões 1,5σ/2σ) em vez de 30/70 fixos. Indicadores comparáveis entre regimes de volatilidade cripto. **Complexidade:** baixa a média. **Validação:** casos manuais (RSI de série monotônica = 100; alternada = 50) e invariância de escala.

### O3 — Escolher uma família de reversão e comparar, sem multiplicar variantes *(livro: C6, C7; relacionado ao livro 2, cap. 3 O1)*

Opções: bandas z-score (Chan), extremos RSI/oscilador (Kaufman), canal/CCI. Para não inflar universo com quase duplicatas, construir **uma** estratégia parametrizada com gatilho selecionável (z-score do preço versus média ou RSI em unidades σ) e comparar gatilhos num único estudo pré-registrado (livro 3, cap. 2 O3 e cap. 6 O2). Alertar na descrição/tese que entradas contra tendência têm risco alto. **Complexidade:** média.

### O4 — Mostrar deriva da escala do indicador *(livro: C4, p. 379)*

Para osciladores/momentum, mostrar distribuição móvel do indicador (ex.: faixa 2σ ao longo do tempo) nos detalhes do backtest, para evidenciar como seletividade de limite fixo deriva. Faz parte dos diagnósticos. **Complexidade:** baixa.

### Não aplicável

Uso de RSI em padrões gráficos (cabeça-e-ombros), índice/divergência de momentum (não lidos), estocástico e outros osciladores (não lidos), operações contrárias compradas/vendidas.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O2 auxiliares de oscilador + limites σ | média | – | – | baixa–média | auxiliares estatísticos |
| 2 | O4 exibir deriva de escala | baixa | – | – | baixa | O2 |
| 3 | O1 experimento de entrada em recuo | média | média | – | média | O2 e fluxo |
| 4 | O3 uma família de reversão | média | média | – | média | livro 2, caps. 2–3 |

## 5. Arquivos afetados

`strategies/domain/` (auxiliares e, depois, parâmetros), catálogo/formulários, `analytics/domain/`, formulários de estratégia no app e testes (incluindo truncamento).

## 6. Plano incremental

1. Auxiliares e casos de teste.
2. Exibição da deriva de escala.
3. Estudos pré-registrados para entradas de recuo e comparação de gatilhos de reversão.

## 7. Critérios de aceitação e testes

* Auxiliares RSI/CMO/momentum reproduzem casos; limites em σ são invariantes ao multiplicar preços por constante.
* Novas opções desligadas por padrão; estratégias existentes inalteradas; Ruff, mypy e testes passam.

## Ressalvas

Páginas lidas não apresentam resultados de desempenho para esses osciladores. Estatísticas RSI (topos ~72, fundos ~32) vêm de estudo de futuros de 1985. O próprio autor caracteriza negociação contra tendência como arriscada.
