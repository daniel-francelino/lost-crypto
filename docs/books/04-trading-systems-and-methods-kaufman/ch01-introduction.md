# Livro 4 · Capítulo 1 — Introdução

*Trading Systems and Methods*, 5.ª ed., Perry J. Kaufman (Wiley, 2013). Páginas do livro (PDF = livro + 20; alguns símbolos se perderam no texto). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Foram lidas pp. 1–24, exceto pp. 2–5 (visão geral de estilos e fundamentos versus análise técnica), percorridas por alto, e pp. 16–17 (maturidade dos mercados por região e bibliografia), também lidas por alto.

## 1. Resumo do capítulo (pp. 1–24)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Passeio aleatório versus antecipação**: dois argumentos contra aleatoriedade pura são décadas de desempenho sistemático documentado e preços que se movem por **antecipação**. Aleatoriedade depende da frequência dos dados: a mesma série parece mais ruidosa em alta frequência e mais tendencial em horizontes longos. Preços **não são simétricos nem normais**; têm **caudas pesadas em sequências** (sequências longas mais frequentes do que prevê a distribuição normal). Motivos pelos quais métodos funcionam: fluxos sem relação com o momento (aportes/resgates mensais de fundos), antecipação, volatilidade extrema e preço distante do valor. | Se é possível negociar com vantagem. | 6–8 |
| C2 | **Estilo depende da frequência dos dados**: seguidores de tendência de longo prazo devem usar dados de baixa frequência (tendências mais visíveis); operadores de curto prazo preferem reversão à média e movimentos rápidos em dados de alta frequência. | Ajustar estratégia ao horizonte. | 8–9 |
| C3 | **Medir ruído**: **razão de eficiência (ER)** `= |P_t − P_{t−n}| / Σ|P_i − P_{i−1}|` (1 = linha reta, 0 = ruído puro), distinta de volatilidade. Alternativas: **densidade de preço** (soma das máximas menos mínimas sobre altura da faixa de n dias) e **dimensão fractal** (estimada em seis etapas). O autor prefere ER por clareza. | Quantificar “o quanto há de tendência”. | 10–12 |
| C4 | **Evidência**: em futuros e índices de ações globais (2000–mar. 2012), média de ruído de 20 dias versus fator de lucro de sistema tendencial básico de média móvel de 40 dias, sempre posicionado e sem custos, mostra relação positiva: **baixo ruído favorece seguir tendência; alto ruído favorece reversão à média**. Mais tendenciais: futuros de juros de curto prazo, juros longos, cruzamentos USD, energia e metais. **Índices de ações tinham mais ruído e pior desempenho tendencial**. | Escolher mercado/estilo pelo ruído. | 13–14 |
| C5 | **Maturidade do mercado**: ruído dos índices de ações norte-americanos aumentou em 20 anos, junto com volume e participação; fenômeno semelhante ocorre em outros lugares. | Erosão da vantagem com aumento de participantes. | 14–16 |
| C6 | **Oito diretrizes de pesquisa**: partir de premissa sólida (não descoberta testando tudo); enunciá-la simples (Occam); não pressupor; testar primeiro as partes mais simples e importantes (soluções transparentes); evitar erros de omissão (custos, risco); **questionar resultados bons tanto quanto os ruins**; não buscar atalhos (verificar trabalho alheio); começar pelo fim (definir objetivo). | Disciplina de pesquisa. | 18–19 |
| C7 | **Perfil de um sistema de negociação**: mudanças do mercado e longevidade do sistema (tecnologia, participação, globalização, custos menores); escolha dos dados; diversificação (inclusive entre estratégias num mercado); **seleção de operações** (muitos filtros causam sobreajuste ou nenhuma operação); **testes servem para validação e robustez, não para varreduras massivas** (solução robusta em vários mercados nunca parece tão boa quanto resultado otimizado para uma única ação); controle de risco em quatro níveis (operação, setor, carteira de um sistema, carteira de sistemas; risco por volatilidade; alavancagem); **custos de transação** (sistemas rápidos são mais sensíveis; sistemas direcionais têm mais slippage que reversão à média; **superestimar custos é tão prejudicial quanto subestimá-los**); **monitoramento e retorno de informação** comparados às expectativas. | Lista de verificação de sistema completo. | 20–23 |
| C8 | Navalha de Occam em todo o processo: acrescentar complexidade por poucos pontos-base aumenta problemas e riscos mais que retornos. | Simplicidade como princípio. | 23 |

Os exemplos são futuros e índices de ações. Referências a criptoativos são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Medida de ruído/razão de eficiência | ❌ | Não calculada em `analytics/domain/metrics.py` nem em dados de mercado. |
| Escolha de intervalo pelo ruído | ❌ | Operador escolhe um dos seis intervalos (`Timeframe`), sem orientação. |
| Família de estratégia conforme o mercado | ❌ | Só há estratégias de tendência. |
| Diretrizes de pesquisa | ⚠️ | Restrições do produto já incorporam várias (estratégias simples, custos sempre aplicados, treino/teste); faltam questionar resultados bons e começar pela premissa. |
| Custos: superestimar/subestimar é prejudicial | ⚠️ | Taxa/slippage fixos, sem calibração pela execução real (livro 1, cap. 5 O4). |
| Slippage direcional versus reversão | ❌ | Um único valor para todas as estratégias e lados. |
| Monitoramento versus expectativas | ⚠️ | Existem métricas e reconciliação do bot, mas sem comparação com expectativas do backtest (livro 1, cap. 5). |

## 3. Oportunidades

### O1 — Diagnóstico da razão de eficiência (ruído) por par/intervalo *(livro: C3, C4, pp. 10–14)*

* **Problema:** operador escolhe intervalo e estratégia tendencial sem evidência de que a série tenha tendência suficiente nessa frequência.
* **Proposta:** acrescentar aos diagnósticos de séries (livro 2, cap. 2 O1 e cap. 6 O1) ER móvel `ER(n)` para janela escolhida, média e distribuição (percentis) por intervalo, por par importado, junto da relação medida pelo autor: menos ruído → maior fator de lucro tendencial. Opcionalmente, calcular essa relação nos **nossos dados**: fator de lucro bruto do sistema tendencial básico sempre posicionado versus ER média por par/intervalo, reproduzindo o gráfico do livro com candles cripto para testar a afirmação em vez de pressupô-la.
* **Benefício:** filtro inicial barato para escolher estratégia/intervalo, complementar a meia-vida e Hurst, e variável de segmentação (desempenho por tercil de ruído). **Complexidade:** baixa (função pura nos fechamentos, endpoint aditivo e gráfico no app).
* **Riscos:** regressão do livro usa 12 anos de futuros/índices sem custos; relação pode ser fraca ou diferente em cripto; ER depende da janela; ER baixo pode refletir ruído microestrutural. **Validação:** série reta sintética → ER=1; série alternada → ER≈0; reproduzir Tabela 1.1 do livro (0,06 e 0,56).

### O2 — Desempenho por regime de ruído *(livro: C4, pp. 13–14 · adaptação)*

Dividir resultados do backtest por tercil ER (calculado na mesma janela) para mostrar se tendência só rende em períodos de pouco ruído. Amplia relatórios por subperíodo (livro 1, cap. 2 O5; livro 2, cap. 5 O1). **Complexidade:** baixa a média. **Risco:** mais segmentação e testes múltiplos; identificar tamanhos de amostra.

### O3 — Verificações “questione resultados bons” como alertas automáticos *(livro: C6, p. 19)*

Acrescentar ao bloco de triagem (livro 2, cap. 1 O3): fator de lucro/Sharpe excepcional ante mediana de execuções comparáveis; poucas operações; desempenho muito superior a comprar e manter com drawdown incompatível; lucro dominado pela primeira/última operação. O livro oferece diretriz, não limite específico. **Complexidade:** baixa. **Validação:** teste unitário de cada alerta.

### O4 — Slippage conforme lado e estratégia *(livro: C7, p. 22 · adaptação)*

O autor diz que sistemas direcionais (rompimento/tendência) têm mais slippage que reversão à média, que provê liquidez. Tornar `slippage_bps` configurável **por tipo de entrada** (entrada a mercado em rompimento versus entrada tipo limite) quando houver simulação de ordens limite; até lá, documentar que modelo único provavelmente subestima custo de entrada tendencial e superestima o de estratégia limite. Relaciona-se ao livro 2, cap. 7 O2. **Complexidade:** média. **Dependência:** registros de slippage realizado (livro 1, cap. 5 O4).

### O5 — Lista de verificação de feedback no runbook *(livro: C7, pp. 22–23)*

Documentar métricas esperadas ao iniciar operação real, frequência de comparação e critério para alterar tamanho ou encerrar (livro 2, cap. 4 O1 e cap. 8 O7). **Complexidade:** muito baixa.

### Não aplicável

Listas específicas de futuros, classificações regionais de ruído em ações, bibliografia e notação de planilha/EasyLanguage.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 diagnóstico ER | média | – | – | baixa | módulo de diagnósticos |
| 2 | O3 alertas de bons resultados | média | – | – | baixa | métricas |
| 3 | O2 desempenho por ruído | média | – | – | baixa–média | O1 |
| 4 | O5 runbook | – | média | – | muito baixa | – |
| 5 | O4 slippage por tipo | média | – | – | média | registros de execução |

## 5. Arquivos afetados

`analytics/domain/` (ER, densidade de preço), `market_data/presentation/router.py` (diagnósticos), `backtesting/domain/segments.py` ou novo divisor de regimes, página de dados de mercado (`lib/market-data/*`), runbook em `docs/` e testes.

## 6. Plano incremental

1. Função pura ER com exemplo do livro como teste.
2. Endpoint e gráfico no app.
3. Replicar a relação ruído versus lucro tendencial nos dados próprios (relatório de pesquisa).
4. Alertas e segmentação por regime.

## 7. Critérios de aceitação e testes

* ER reproduz Tabela 1.1 (0,06 e 0,56) e casos extremos (1,0 e aproximadamente 0).
* Diagnósticos são somente leitura e não alteram negociação nem execuções armazenadas; Ruff, mypy e testes atuais passam.

## Ressalvas

A relação ruído/lucro usa sistema tendencial sem custos e sempre posicionado em futuros e índices (p. 13). É evidência do autor para seu modelo, não regra para cripto à vista; relações passadas podem não persistir.
