# Livro 4 · Capítulo 16 — Day trading

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 737–745 (custos, estratégias, ordens não executadas, estimativa de slippage e elementos essenciais), 759–761 (rompimento da faixa de abertura) e 775–777 (choques intradiários) foram lidas. Sistemas de padrões de preço (746–758), restante do rompimento da abertura (761–774) e padrões de volume intradiário (774–775) **não** foram lidos em detalhe nem são resumidos.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Day trading é difícil: preços intradiários reagem ao ruído (relatórios, grandes ordens, mudanças de analistas), não a fundamentos; exige disciplina e pune maus hábitos. Day traders podem mirar ~1¢ por ação. | Expectativas realistas. | 737–738 |
| C2 | **Custos de transação são maior obstáculo**: taxas e slippage. Melhorar desempenho exige comissões menores, seleção cuidadosa (volatilidade alta reduz custo percentual) e execução melhor. Tabelas de volatilidade/volume de ações e futuros (1995–2010); faixa **abertura-fecho do S&P é cerca de metade da amplitude diária total**. | Custos e oportunidade. | 738–740 |
| C3 | **Custo depende do estilo**: entradas de tendência/momentum pagam slippage (ao menos meio ponto em E-mini). Exemplo de dia: faixa US$931, taxa US$10 por lado, slippage US$100 → restam US$821; com 1/3 de vencedoras e ganhos 2× perdas, resultado após custos é negativo (“equilíbrio com US$90 para duas perdas de US$45”). **Sistema tendencial intradiário precisa superar sistema de tendência médio para sobreviver**. Reversão à média tem, conservadoramente, ~50% do slippage de tendência e pode receber rebates de liquidez. | Estilos que resistem a custos. | 740–742 |
| C4 | Escolher mercados de **alto volume e alta volatilidade**; mercados finos têm movimentos maiores, mas ordens a mercado/stop executam mal e limites podem não preencher. | Seleção por liquidez. | 741 |
| C5 | **Ordens perdidas (“unables”)**: em saltos de notícia, entradas tendenciais não executam perto do preço do sistema; operações ignoradas removem lucros, não perdas. No exemplo do autor, 10% de ordens perdidas reduzem fator de lucro de 1,66 para 1,50 (cinco vencedoras perdidas em 100, US$1.250). | Otimismo do backtest por execução perfeita. | 742–743 |
| C6 | **Estimar slippage**: depende de volatilidade, volume total, tamanho da ordem e atividade. Registrar preço da ordem/execução, volatilidade, volume, hora e ticks; ajustar `slippage = a0 + a1·volatilidade + a2·volume diário + a3·fator horário + a4·tamanho da ordem`. Greer e Brorsen encontraram slippage moderado em stops grandes. **Slippage ajustado à volatilidade**: aumentá-lo com volatilidade e **nunca deixá-lo abaixo de mínimo**; “ser conservador”. Usar ordens no preço de liquidação para fechar. | Calibrar custo. | 743–744 |
| C7 | **Evolução**: rompimentos de faixa de abertura (anos 1990) → pares (2000) → alta frequência. Métodos de tendência não são usados para posições menores que três dias e “provavelmente não se aplicam abaixo de vinte dias” (opinião do autor); movimento curto é sobretudo ruído; **esperar recuos em entradas direcionais e preferir reversão à média**. Padrões gráficos clássicos em dados intradiários são “simplesmente aleatórios”. | Mudança de estilo. | 744–745 |
| C8 | **Rompimento da faixa de abertura** (comprar após alta definida acima da abertura, inverter abaixo; sair no fecho), melhorado com filtro de dia interno (Crabel: taxa lucrativa sobe; títulos 60% → 76%). Números de 1989–1990 “não podem ser reproduzidos exatamente” hoje; tamanhos fixos devem ceder a limites por volatilidade. | Rompimento intradiário. | 759–760 |
| C9 | **Estratégia de choque intradiário (negociar contra a reação)**: choque = barra com amplitude verdadeira ≥3× média anterior (ou ≥2× média da mesma barra nos dias anteriores, comparando mesmo horário pois picos ocorrem na abertura). Se fecho ficar no 20% superior da faixa, vender a descoberto na próxima abertura (e vice-versa); sem stop por duas barras; depois stop além dos extremos das três barras; sair no fecho. “Movimento maior que o normal é mais frequentemente causado por ruído e tende a reverter”. Autor encontrou lucro em ouro (barras de 20 min) e títulos de 30 anos; sugere saída por volume de operador de pregão. | Operar contra choques. | 775–777 |

Referências cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Custos sempre aplicados | ✅ | `fee_rate` e `slippage_bps` aplicados sempre. |
| Slippage varia com volatilidade/tamanho/horário | ❌ | `slippage_bps` constante (também livro 2, cap. 7 O2; livro 1, cap. 5 O4). |
| Slippage mínimo após ajuste | n/a ainda | Não há escala. |
| Ordens perdidas no backtest | ❌ | Motor executa todo sinal na próxima abertura; falhas só na operação real (rejeições contadas em `rejected_signals`, ex. “already in position”). |
| Custo conforme estilo de estratégia | ❌ | Slippage único. |
| Reversão mais barata por ordem limite | ❌ | Sem simulação de limite; paper preenche a mercado. |
| Intervalos intradiários | ✅ | Suporta 1m/5m/15m/1h; cripto é contínuo, então abertura-fecho/faixa de abertura não existem naturalmente. |
| Relato de ordens perdidas em paper/real | ⚠️ | Ordens podem ser rejeitadas/não preenchidas; sem resumo de lucros perdidos versus perdas evitadas. |

## 3. Oportunidades

### O1 — Sensibilidade do backtest a ordens não executadas *(livro: C5, pp. 742–743)*

Opção determinística que remove fração `u` de entradas lucrativas segundo regra desfavorável (ex.: entradas nas maiores barras) ou, mais simples, entradas em candles cuja amplitude supere percentil recente; reportar impacto no fator de lucro/retorno. Quantifica fragilidade a falhas de preenchimento em movimentos rápidos. Exemplo do autor: PF 1,66 → 1,50 com 10% de ordens perdidas.

**Benefício:** medida de robustez para tendências que entram em rompimento, justamente quando execução piora. **Complexidade:** baixa a média (opção de motor e seleção determinística). **Riscos:** regra de seleção é nossa e aproxima falha real. **Validação:** fração removida confere com `u`; `u=0` reproduz resultado atual.

### O2 — Slippage ajustado à volatilidade com piso, calibrado por execuções *(livro: C6, pp. 743–744)*

Mesma direção do livro 2, cap. 7 O2 e livro 4, cap. 8; acrescenta regras do autor: escalar com volatilidade atual, **limitar redução por um mínimo** e ajustar `a0…a4` com execuções registradas (livro 1, cap. 5 O4). Emitir relatório de regressão quando houver execuções suficientes. **Complexidade:** média.

### O3 — Premissas de custo por tipo de estratégia *(livro: C3, pp. 740–742)*

Permitir slippage separado para entradas que pagam spread (rompimento/tendência, mercado) e entradas tipo limite (reversão); documentar estimativa conservadora do livro de 50% para reversão e necessidade de simulação honesta de limites (podem não executar: custo de oportunidade; livro 1, cap. 2 C7). **Complexidade:** média; depende de ambiente paper com ordens limite.

### O4 — Alerta de cobertura de custos por intervalo *(livro: C2, C3, pp. 738–741)*

Avisar se lucro bruto médio por operação for inferior a múltiplo (ex. 3×) do custo ida-volta, sobretudo em 1m/5m (métrica no livro 4, cap. 5 O6). Mostrar cálculo de equilíbrio do exemplo (taxa de acerto, ganho/perda e custo por operação) para explicar por que sistema 33%/2:1 perde vantagem em horizontes curtos. **Complexidade:** baixa.

### O5 — Experimento de reversão de choque (não recomendação) *(livro: C9, pp. 775–777)*

Detector de razão de volatilidade (livro 4, cap. 14 O1) e regra “candle de choque fecha no 20% superior/inferior → operar contra nas próximas barras” reproduzem exemplo do livro. Em posição à vista comprada, só metade de **comprar após liquidação brusca** está disponível (choque de baixa fecha no 20% inferior → comprar próxima abertura, stop abaixo do extremo, sair após k candles). É entrada contrária, perigosa em quedas cripto. **H-SHOCK-FADE**: testar só se diagnóstico de choques (cap. 14 O1) revelar reversão no intervalo. **Complexidade:** baixa a média.

### O6 — Referências de volume/volatilidade conforme horário *(livro: C9, p. 775)*

Reforça livro 4, cap. 12 O1: comparar barra com média da *mesma hora* evita tratar picos de abertura/fecho como choque. **Complexidade:** parte do cap. 12 O1.

### Não aplicável

Evolução de pares/HFT, limites de negociação, dias de limite travado, liquidação de futuros, comportamento de pregão e transição de viva voz para eletrônico.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O4 alerta de cobertura de custos | alta | – | – | baixa | métricas |
| 2 | O1 sensibilidade a ordens perdidas | alta | média | – | baixa–média | mudança no motor |
| 3 | O2 modelo/calibração de slippage | alta | média | – | média | registros de execução |
| 4 | O3 custos por estilo | média | – | – | média | ambiente limite |
| 5 | O5 experimento de reversão de choque | baixa | – | – | baixa–média | cap. 14 O1 |
| 6 | O6 referências horárias | baixa | – | – | baixa | cap. 12 O1 |

## 5. Arquivos afetados

`backtesting/domain/engine.py`, `models.py` (opções), `execution/domain/fills.py` (modelo de slippage), `analytics/domain/metrics.py`, `docs/openapi.json`, formulário/detalhes de backtest e testes.

## 6. Plano incremental

1. Alerta de cobertura e auxiliar de equilíbrio.
2. Opção de ordens perdidas.
3. Modelo de slippage e relatório de calibração quando houver dados.
4. Experimentos pelo fluxo de validação.

## 7. Critérios de aceitação e testes

* Opções padrão preservam comportamento atual; `u=0` idêntico bit a bit.
* Alerta de custos dispara abaixo do limite e não dispara com lucro suficiente.
* Ruff, mypy e testes existentes passam.

## Ressalvas

Números (taxa de acerto de rompimento, exemplos de custo e evolução do day trading) referem-se a 1990–2011, futuros e ações dos EUA. Não usar tendências abaixo de 3–20 dias é julgamento do autor nesses mercados, não teste cripto.
