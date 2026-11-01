# Livro 3 · Capítulo 4 — Análise estatística

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 165–175, 186–189 e 202–216 foram lidas na íntegra. A parte intermediária, em estilo de livro didático (pp. 176–185, experimentos com caixas de contas; pp. 190–201, estatística descritiva, probabilidade e distribuições), foi percorrida pelos títulos e lida por alto; não encontrei conteúdo técnico específico de trading além do retomado nas seções seguintes.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | A essência da análise técnica é **inferência estatística**: generalizar amostras históricas para o futuro. Começar pela **hipótese nula**: a regra não tem poder preditivo e seu retorno esperado é zero **em dados sem tendência**; um backtest lucrativo é “acaso” até prova em contrário. | Ceticismo como padrão. | 165–167 |
| C2 | **Como ler evidências**: valor-p é a fração da densidade de probabilidade nula igual ou mais extrema que o desempenho observado; expressa a *probabilidade da evidência sob a hipótese nula*, não a probabilidade de a hipótese ser verdadeira. Convenção: **0,05**. Afirmar o consequente é inválido; negar o consequente é válido. | Interpretar significância. | 167–171 |
| C3 | **Seleção de dados eleva o padrão**: ao escolher a melhor dentre muitas regras, distribuição nula adequada é a da *melhor entre 1.000* regras, mais larga que a de uma regra isolada; um ótimo resultado individual é medíocre como melhor de 1.000 (Figura 4.4; cap. 6). | Testes múltiplos. | 171–172 |
| C4 | **Seis componentes de um problema de inferência**: população, amostra, parâmetro populacional, estatística amostral, inferência e declaração de confiabilidade. Para uma regra: a **população** são todos os retornos diários que obteria no *futuro prático imediato* (horizonte finito em que se supõe que a rentabilidade de uma regra útil persistirá, embora mercados não sejam estacionários); a **amostra** é um único backtest; o **parâmetro** é retorno esperado (o livro usa retorno diário médio anualizado sobre dados sem tendência; Sharpe e fator de lucro são alternativas); a **estatística** é o retorno médio observado. Sem alguma persistência do poder preditivo, análise técnica não faz sentido. | O que se está inferindo exatamente. | 186–189 |
| C5 | **Distribuição amostral**: distribuição dos valores de uma estatística em todas as amostras possíveis; sua **dispersão quantifica a incerteza**. Como há uma amostra, é preciso estimá-la. Para a média amostral: amostras maiores aproximam a média populacional (Lei dos Grandes Números); dispersão cai com `√n` (amostra 10× maior → intervalo 3,16× mais estreito); maior variação nos dados amplia a distribuição; sua forma tende à normal (Teorema do Limite Central), com convergência dependente da distribuição original (cinco observações bastam em alguns casos, 30 no pior exemplo); razões podem ser muito não normais. | Incerteza pelo tamanho da amostra. | 202–213 |
| C6 | **Erro-padrão da média** = `σ̂ / √n`, com `σ̂` estimado na amostra usando divisor `n − 1`. Junto à normalidade, produz a distribuição amostral clássica. Limitação: pressupõe forma normal; se incorreta, as conclusões também serão. | Teste clássico. | 213–215 |
| C7 | **Alternativa computacional intensiva**: reamostrar a amostra única muitas vezes para aproximar a distribuição amostral: **bootstrap** e **permutação Monte Carlo** (próximo capítulo). No estudo de caso, constrói-se a distribuição amostral do retorno médio de uma regra *sem poder preditivo* como benchmark. A mesma distribuição gera intervalos de confiança. | Inferência sem supor uma distribuição específica. | 215–216 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Hipótese nula/valor-p | ❌ | Não é produzido (coerente com livro 2, cap. 1 O1). |
| Erro-padrão, estatística t e intervalo de confiança do retorno médio | ❌ | Não existem em `Metrics`. |
| Tamanho de amostra visível junto às estatísticas | ⚠️ | `round_trips` e `fills` são apresentados; número de observações de retorno (barras) não integra `Metrics`. |
| Correção de melhor entre N | ❌ | Varreduras ordenam por resultado bruto; `MAX_SWEEP_RUNS` limita a grade, mas não há ajuste (livro 1, cap. 3 O7). |
| Definição do “futuro prático imediato” | ❌ | Não se declara o horizonte de validade esperada; treino/teste só tem divisão cronológica. |
| Reamostragem (bootstrap/permutação) | ❌ | Não implementada (ver livro 3, cap. 3 O1 e cap. 5 para os métodos). |
| Retorno esperado nulo em dados sem tendência | ❌ | Não implementado (livro 3, cap. 1 O1). |

## 3. Oportunidades

### O1 — Retorno médio por barra com erro-padrão, estatística t e intervalo de confiança *(livro: C5, C6, pp. 209–215)*

* **Problema:** P&L líquido é exibido sem quantificar a incerteza.
* **Proposta:** derivar da curva patrimonial os retornos por barra (ou operação) `r_t`, quantidade `n`, média, desvio-padrão amostral com divisor `n − 1`, **erro-padrão `s/√n`**, estatística t `média/EP` e intervalo de confiança aproximado. Apresentar `n` junto dos resultados e sinalizar amostras abaixo do mínimo.
* **Benefício:** quantifica incerteza no resultado principal; mesmo cálculo da significância do Sharpe diário no livro 2, cap. 1 (`Sharpe × √n`). **Complexidade:** baixa.
* **Riscos (adaptação nossa, não discutida neste capítulo):** fórmula clássica pressupõe observações independentes e formato do TCL; retornos da curva patrimonial com posições mantidas têm autocorrelação positiva; barras sem posição são zeros que subestimam `s` e superestimam a estatística t; retornos cripto têm caudas pesadas. Mostrar números clássicos como otimistas e preferir reamostragem (O2). Apresentar também retornos **por operação**, possivelmente mais próximos de independência.
* **Validação:** série calculada manualmente; variância zero → `None`; comparação com intervalo bootstrap de dados conhecidos.

### O2 — Inferência por bootstrap e permutação *(livro: C7, pp. 215–216; métodos continuam no cap. 5)*

Usar reamostragem para construir a distribuição amostral nula em vez de supor normalidade. Detalhes de implementação ficam no relatório seguinte; referências cruzadas: executor placebo/retornos embaralhados (livro 3, cap. 3 O1) e teste de entradas aleatórias (livro 2, cap. 1 O1). **Complexidade:** média. Implementar uma vez.

### O3 — Explicitar alvo da inferência: horizonte e parâmetro *(livro: C4, pp. 186–189)*

Declarar em cada resultado o que está sendo inferido: retorno esperado desta regra para este símbolo/intervalo num horizonte futuro definido (por exemplo, “próximos N dias”), medido por estatística nomeada (retorno líquido sem tendência ou Sharpe). Relacionar ao pré-registro (livro 3, cap. 2 O3). **Complexidade:** baixa (rótulos e campos). Documenta também o pressuposto de persistência (sem persistência, não há análise técnica).

### O4 — Considerar a distribuição do melhor entre N nas varreduras *(livro: C3, pp. 171–172)*

Mostrar junto ao melhor resultado da varredura a **distribuição do melhor resultado sob a hipótese nula** (por permutação/bootstrap de O2), avaliando o vencedor contra o “melhor de N regras aleatórias”, não contra uma regra isolada. É a correção por seleção de dados em linhas gerais; o método está no cap. 6. Apenas referência cruzada. **Complexidade:** média (depende de O2).

### O5 — Tamanho mínimo de amostra na interface *(livro: C5, pp. 209–213)*

Exibir `n` (barras e operações) com cada estatística e avisar se for pequeno demais para o pressuposto do TCL, cujo pior caso o livro situa em 30. Amplia livro 1, cap. 3 O6 e livro 2, cap. 6 O4. **Complexidade:** muito baixa.

### Não aplicável

Experimentos didáticos de lançamentos de moeda e contas; tutoriais de estatística descritiva.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O5 exibir tamanho da amostra | média | – | – | muito baixa | – |
| 2 | O1 EP/estatística t/IC com ressalvas | alta | – | – | baixa | série de retornos |
| 3 | O3 explicitar alvo da inferência | média | – | – | baixa | – |
| 4 | O2 inferência por reamostragem | **alta** | – | – | média | reutilizar motor |
| 5 | O4 referência de melhor entre N | alta | – | – | média | O2, livro 3, cap. 6 |

## 5. Arquivos afetados

`analytics/domain/metrics.py` e novo `analytics/domain/inference.py` (funções puras), `backtesting/application/service.py`, schemas de varredura, `docs/openapi.json`, páginas de detalhes/varredura do app e testes.

## 6. Plano incremental

1. Exibir `n` em todo lugar (barras e operações).
2. Funções puras para média, EP, t e IC, por barra e por operação, com testes unitários.
3. Inferência por reamostragem (cap. 5), seguida da referência do melhor entre N (cap. 6).

## 7. Critérios de aceitação e testes

* Reproduzir `EP = s/√n` com divisor `n−1` em séries calculadas manualmente; numa simulação, largura do IC cai com `√n`.
* Para poucas observações, estatísticas retornam `None` com motivo.
* Nenhuma mudança no comportamento de negociação; Ruff, mypy e testes existentes passam.
* Interface explica que valor-p é probabilidade da evidência sob a hipótese nula, não probabilidade da hipótese (p. 169).

## Ressalvas

O capítulo explica conceitos e deixa os procedimentos de teste para os caps. 5 e 6. Independência e normalidade da fórmula clássica são pressupostos questionáveis para retornos de estratégias; trate os resultados O1 como limites inferiores da incerteza.
