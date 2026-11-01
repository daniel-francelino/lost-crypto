# Livro 4 · Capítulo 6 — Análise de regressão

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 235–237, 257–259 e 273–276 foram lidas. Matemática de regressão simples/múltipla, ajustes não lineares, ARIMA e filtro de Kalman (pp. 238–256, 259–272), e “Medir a força do mercado” (pp. 276–278) **não** foram lidos nem resumidos.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Série de preços tem **tendência**, componente **sazonal/cíclico** e resíduo **aleatório** inexplicado; regressão isola tendência. Tendências curtas (dias/semanas) não se explicam por fatores macro e refletem sobretudo reação de investidores a notícias. Evitar relações espúrias: “premissa sólida é base do sucesso”. | Para que serve regressão. | 235–236 |
| C2 | Dados de frequência menor suavizam a série (extremos raramente coincidem com último dia do mês); período de cálculo não deve coincidir com ciclo que se anularia na média (janela de 12 meses neutraliza sazonalidade anual). | Escolher janela. | 236–237 |
| C3 | Ajustes logarítmicos/exponenciais tornam relações não lineares em mínimos quadrados lineares, transformando variáveis. Melhor ajuste estatístico (menor desvio dos erros) **não é necessariamente melhor previsão**: modelo logarítmico de pior ajuste deu previsão de soja mais realista; exibir desempenho de sistema com investimento fixo em **escala logarítmica**; reajustar modelos em janela móvel. | Ajuste versus previsão. | 257–258 |
| C4 | **Regra de negociação por regressão (semelhante à média móvel)**: regressão linear de n dias dos fechamentos gera previsão `F_{t+1}`; comprar quando fecho de amanhã superar previsão, vender a descoberto se ficar abaixo. Para evitar oscilações falsas, adicionar **bandas de confiança**: 90% = 1,65 e 95% = 1,96 (normalmente 2,0) vezes desvio-padrão dos resíduos. Regressão sinaliza mudança de direção **antes da média móvel**, cujo atraso é zona de segurança; desempenho tende a melhorar com períodos longos. | Regra tendencial objetiva com banda. | 273–274 |
| C5 | **Regra de inclinação**: comprar com inclinação positiva, vender com negativa; inclinação tem escala diferente do preço (painel separado); compete com outros métodos de tendência (cap. 8). Inclinação pode enganar: igual valor pode resultar de movimento suave ou ruidoso. Acrescentar **correlação R entre preço e sequência de inteiros** (não R², para preservar sinal/direção); inclinação é mais rápida que média móvel, mas menos estável; R oferece informação complementar. | Direção e consistência da tendência. | 275–276 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Regras tendenciais por regressão | ❌ | Não constam no catálogo; sem auxiliar de regressão. |
| Medida R da qualidade da tendência como filtro | ❌ | Não existe (nem ER; ver livro 4, cap. 1 O1). |
| Banda de confiança baseada em resíduo | ❌ | Não há. |
| Reajuste móvel | ✅ | Estratégias calculam indicadores apenas com candles passados. |
| Exibição logarítmica de patrimônio com tamanho fixo | ⚠️ | Escala do gráfico patrimonial não foi verificada. |

## 3. Oportunidades

### O1 — Filtros opcionais de qualidade da tendência *(livro: C5, pp. 275–276; junto à ER do cap. 1)*

* **Problema:** EMA/Donchian negociam ruído lateral; medida de consistência poderia ignorar entradas de baixa qualidade.
* **Proposta:** duas medidas candidatas numa janela: correlação `R` entre fechamentos e índice temporal (sinal = direção; magnitude = consistência) e razão de eficiência do livro 4, cap. 1. Parâmetro opcional como `min_trend_quality`; entrar apenas acima do limite. Desligado por padrão.
* **Benefício:** hipótese para reduzir *whipsaws* sem nova estratégia. **Complexidade:** baixa a média (auxiliares, parâmetro e testes).
* **Riscos:** filtros/parâmetros extras causam sobreajuste (alerta do autor, cap. 1); filtro atrasa entradas; não há métricas de desempenho nas páginas lidas. Registrar **H-TREND-QUALITY** e testar somente no fluxo varredura → melhor de N → validação, contando parâmetro adicional em N. **Validação:** truncamento, efeito em contagem/drawdown e sensibilidade.

### O2 — Nova família tendencial por inclinação de regressão (com R) *(livro: C4, C5, pp. 273–276)*

Comprar com inclinação positiva da regressão de n barras dos fechamentos (opcionalmente usar banda residual, multiplicadores 1,65/1,96/2,0 ou R acima de limite); vender quando inclinação inverter ou cair abaixo da banda. Relaciona-se ao canal de regressão do livro 4, cap. 4 O1; implementar como uma estratégia com modos explícitos, não duas quase duplicadas (duplicatas inflam N sem informação nova, livro 3, cap. 6 O4).

**Benefício:** resposta mais rápida que média móvel com medida de qualidade. **Complexidade:** média. **Riscos:** resposta rápida gera mais falsos sinais/custos; livro diz que desempenho “tende a melhorar com período maior”, o que deve ser testado em cripto. **Validação:** como O1.

### O3 — Verificar escala do gráfico patrimonial *(livro: C3, p. 257)*

Conferir gráficos de patrimônio e drawdown no app: sistemas com fração fixa são representados honestamente em escala logarítmica; se atual for linear, oferecer alternância (pedido de gráfico lost-ui L-n). **Complexidade:** baixa, conforme biblioteca de gráficos (notas anteriores citam eixo y iniciado em zero como limitação).

### Não aplicável

Mínimos quadrados não lineares, regressão multivariada, ARIMA e filtro de Kalman (ver livro 2, cap. 3 para reversão à média), classificações de força do mercado.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O3 verificar escala do gráfico | – | – | baixa | baixa | capacidades lost-ui |
| 2 | O1 filtro de qualidade | média | – | – | baixa–média | auxiliares e fluxo de validação |
| 3 | O2 estratégia de inclinação | média | – | – | média | auxiliares e fluxo |

## 5. Arquivos afetados

`strategies/domain/` (auxiliares, parâmetro opcional, estratégia), catálogo e formulários, gráficos do app (`equity-chart-rows.ts`) e testes, incluindo truncamento.

## 6. Plano incremental

1. Auxiliares (inclinação linear, R, desvio residual, ER) com testes unitários.
2. Opção de filtro nas estratégias tendenciais existentes.
3. Estratégia de regressão após implantação do fluxo.

## 7. Critérios de aceitação e testes

* Auxiliares reproduzem inclinações, correlações e desvios residuais calculados à mão; janelas degeneradas retornam `None` ou nenhum sinal.
* Novos parâmetros opcionais não alteram padrões das estratégias atuais; Ruff, mypy e testes passam.

## Ressalvas

A maior parte do capítulo (derivações estatísticas e exemplos de commodities/ações) não foi lida. Melhor desempenho com janelas longas refere-se a testes de futuros do livro e pode não valer para cripto.
