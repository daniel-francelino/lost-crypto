# Livro 3 · Introdução e Capítulo 1 — Regras objetivas e sua avaliação

*Evidence-Based Technical Analysis*, David R. Aronson (Wiley, 2007). Páginas do livro (PDF = livro + 16). O PDF é uma digitalização com OCR; fórmulas foram conferidas com o texto ao redor. Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. A introdução (pp. 1–11) e o capítulo 1 (pp. 15–31) foram lidos na íntegra.

## 1. Resumo (pp. 1–31)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Uma afirmação precisa ter **conteúdo cognitivo** (critério de diferença discernível): deve ser possível determinar se está certa ou errada. Conhecimento é crença verdadeira justificada; o conhecimento científico é provisório. | Previsões vagas e impossíveis de testar. | 2–5 |
| C2 | Análise técnica **objetiva versus subjetiva**. Critério de programabilidade: um método é objetivo se pode ser codificado para produzir posições inequívocas. Métodos subjetivos (padrões gráficos, ondas de Elliott) são rejeitados como não testáveis. Backtest lucrativo de método objetivo é *necessário, mas não suficiente*: pode ser acaso ou sofrer **viés de seleção de dados**; a “inferência estatística avançada” (caps. 4–6) é que decide. | O que conta como evidência. | 5–7, 15–16 |
| C3 | Estudos acadêmicos citados (seleção do autor, sem evidência nova aqui): indicadores de tendência funcionam em commodities e câmbio; regras simples em índices de empresas jovens; analistas gráficos não distinguem gráficos reais de aleatórios; cabeça-e-ombros não acrescenta informação em ações. | Contexto. | 8–9 |
| C4 | **Regra** mapeia uma série de entrada numa série de posições (+1/−1 ou 0); usam-se **regras binárias de reversão** (sempre comprado ou vendido); limites podem ser fixos (entradas estacionárias) ou variáveis (média móvel, bandas/Bollinger), possivelmente com lógica de **alternância** (*flip-flop*, dois eventos). Regras de limite único geram estados mutuamente exclusivos e exaustivos. | Definir formalmente uma regra. | 16–21 |
| C5 | **Regras tradicionais e inversas**: testar também a interpretação oposta, pois a leitura tradicional pode estar errada ou a entrada pode não ter interpretação evidente. | Não pressupor o sinal de um efeito. | 21–22 |
| C6 | **Benchmark = regra sem poder preditivo** (como placebo), não zero e necessariamente não comprar e manter; para contar como evidência, a regra deve superá-lo por margem que exclua o acaso (caps. 4–6). | Escolha da comparação. | 22–23 |
| C7 | **Viés de posição × tendência do mercado**: retorno de backtest = componente preditivo + componente indesejado decorrente (1) da fração do tempo comprado/vendido e (2) da variação diária média do mercado na amostra. Retorno esperado de regra aleatória: `ER = p(L)·ADC − p(S)·ADC`. Exemplo: S&P 500, 1976–2004, ADC +0,035% ao dia (9,22% ao ano): regra aleatória comprada 90% do tempo rende cerca de 7,31% ao ano; comprada 60%, cerca de 1,78%, **sem** poder preditivo. O viés pode vir de condições assimétricas de compra/venda (condição de venda restritiva). | Regras que apenas capturam a deriva do mercado. | 23–27 |
| C8 | **Correções**: subtrair o retorno esperado de regra sem poder preditivo com o mesmo viés de posição ou, de forma equivalente (prova no apêndice), **remover a tendência** dos retornos diários do mercado subtraindo sua média amostral. Usar dados sem tendência só para calcular retornos da regra; os sinais continuam usando preços reais. Usar **retornos logarítmicos** (`ln(P_t/P_{t-1})`). | Avaliação justa. | 27–29 |
| C9 | **Antecipação e preço de execução**: se o sinal usa o fecho, a execução mais cedo é na **abertura seguinte**; retorno diário da regra = posição no fecho do dia 0 × `ln(Open_{t+2}/Open_{t+1})` menos o retorno logarítmico médio. Entradas atrasadas ou revisadas também devem ser defasadas. | Vazamento de informação. | 29–30 |
| C10 | **Custos de negociação**: necessários se a regra for usada isoladamente; o autor os omite no estudo de caso porque procura informação preditiva. | Custos versus descoberta do sinal. | 31 |

Não estão cobertos aqui: cap. 2 (psicologia das crenças subjetivas, pp. 33–102) e cap. 3 (método científico, pp. 103–164), tratados em relatórios separados.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| C2 programabilidade/regras objetivas | ✅ | Todas as estratégias são código (`strategies/domain/*`) e geram sinais; nenhuma é subjetiva. |
| C4 formalização e limites | ✅ | EMA crossover usa limite variável (cruzamento de médias); Donchian usa alternância com canais de entrada e saída. |
| C5 regras inversas | ❌ | Apenas posições compradas; não há teste sistemático da interpretação oposta. Venda a descoberto é impossível à vista; não aplicável. |
| C6 benchmark aleatório/sem habilidade | ❌ | Só há benchmark de comprar e manter (`buy_and_hold_return_pct`), sem benchmark aleatório de mesma exposição. |
| C7 viés de posição × tendência | ❌ **relevante** | Estratégia comprada exposta 60% do tempo durante forte alta pode lucrar muito sem habilidade. Métricas não mostram tempo no mercado nem benchmark ajustado à exposição. |
| C8 remoção da tendência | ❌ | Não feita. |
| C9 antecipação | ✅ | Executa na abertura do candle seguinte (`engine.py`), como recomendado. Os retornos diários diferem: o livro usa retornos `ln`, o motor acompanha patrimônio. |
| C10 custos | ✅ | Sempre incluídos (o livro os omite na descoberta do sinal, mas inclui no uso isolado, como o sistema). |

## 3. Oportunidades

### O1 — Tempo no mercado e benchmark ajustado à exposição *(livro: C6–C8, pp. 22–29 · adaptação long/flat derivada por nós)*

* **Problema:** um bot comprado reporta “+40% contra +60% de comprar e manter”; não se distingue habilidade da deriva do mercado. O livro diz que a comparação correta é o retorno de uma regra sem habilidade com a mesma exposição.
* **Proposta:** acrescentar às métricas: (a) `time_in_market` (fração de barras com posição); (b) `exposure_adjusted_benchmark_pct`: para regra comprado/neutro, retorno esperado de regra sem habilidade com exposição `p(L)` é `p(L) × retorno de mercado` (derivação nossa da fórmula do livro `ER = p(L)·ADC − p(S)·ADC`, que pressupõe regras compradas/vendidas; em comprado/neutro, `p(S)=0`); (c) `excess_vs_exposure_pct = retorno da estratégia − benchmark`. Em vários períodos, usar retornos logarítmicos e média da amostra conforme C8. A remoção da tendência do livro aplica-se a regras compradas/vendidas; a correção comprado/neutro deve ser validada por simulação Monte Carlo de posições aleatórias com mesma exposição.
* **Benefício:** correção simples e direta da ilusão de mercado em alta para cripto, complementar a comprar e manter. **Complexidade:** baixa (funções puras sobre curva patrimonial e operações).
* **Riscos:** ajuste de primeira ordem (supõe independência entre exposição e retornos, como a regra aleatória); com alta volatilidade, benchmark tem grande ruído amostral (caps. 4–5); custos não entram no benchmark e devem ser tratados consistentemente.
* **Validação:** simular posições aleatórias comprado/neutro com dada exposição numa série tendencial: excesso médio ≈ 0; reproduzir numericamente 7,31% e 1,78% com ADC 0,035%/dia e 90%/60% do tempo comprado.

### O2 — Comparação placebo (benchmark de entradas aleatórias) *(livro: C6, p. 23)*

Reutilizar o teste de entradas aleatórias proposto em [livro 2, cap. 1 O1 etapa 2](../02-algorithmic-trading-chan/ch01-backtesting-and-automated-execution.md): substituir entradas da estratégia por entradas aleatórias com mesmo número de operações e duração, e mostrar a posição do resultado nessa distribuição. É a ideia de “placebo” do livro em forma prática. Apenas referência cruzada; implementar uma vez.

### O3 — Exibir explicitamente exposição e viés comprado *(livro: C7, pp. 24–26)*

Mostrar “% de barras comprado” e “retorno de mercado durante o período” junto de cada resultado e nas varreduras, para evitar que classificações favoreçam regras que simplesmente ficam compradas mais tempo. Parte de O1; nenhuma tarefa além da exibição. **Complexidade:** muito baixa.

### O4 — Manter convenção de execução e documentar retornos logarítmicos *(livro: C8, C9, pp. 28–30)*

O motor já executa na abertura seguinte. Documentar em `docs/` que as métricas usam variação do patrimônio e decidir se novas estatísticas (O1, livro 1, cap. 2 O1) usam retorno simples ou logarítmico. Recomenda-se logarítmico para testes estatísticos e simples para apresentação. **Complexidade:** muito baixa.

### Não aplicável

Regras inversas (sem posições vendidas), análise técnica subjetiva, viés comprado/vendido com perna vendida e omissão de custos.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 tempo no mercado + benchmark por exposição | **alta** | – | – | baixa | – |
| 2 | O3 exibir viés | média | – | – | muito baixa | O1 |
| 3 | O4 nota sobre convenção | baixa | – | – | muito baixa | – |
| 4 | O2 distribuição placebo | alta | – | – | média | livro 2, cap. 1 O1 |

## 5. Arquivos afetados

`analytics/domain/metrics.py` (novos campos), `backtesting/domain/segments.py` (equivalentes por segmento), `analytics/presentation/schemas.py`, `docs/openapi.json`, cartões de métricas e tabela de varreduras no app (`components/backtests`), testes (`api/tests/unit`) e documentação.

## 6. Plano incremental

1. Funções puras para tempo no mercado, benchmark ajustado à exposição e excesso; testes unitários, inclusive os números do livro.
2. Adicionar campos de métrica (também para treino/teste) e exibi-los no app.
3. Acrescentar os mesmos campos às varreduras, para classificar por excesso em vez de retorno bruto.

## 7. Critérios de aceitação e testes

* Reproduzir os exemplos de 7,31% e 1,78% a partir do ADC e da exposição.
* Simulações de posições aleatórias com exposição fixa produzem excesso médio ≈ 0 dentro do erro amostral.
* Métricas existentes, execuções armazenadas e formatos da API permanecem compatíveis, além dos novos campos opcionais.
* Ruff, mypy e testes existentes passam.

## Ressalvas

Os números do S&P 500 são exemplos; o benchmark remove apenas o efeito de primeira ordem da tendência e não comprova habilidade por si só. Como ressalta o autor (p. 6), rentabilidade passada no backtest não prova rentabilidade futura.
