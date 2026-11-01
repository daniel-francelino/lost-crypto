# Livro 5 · Capítulo 4 — Pesos das amostras

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 59–70 foram lidas (resultados sobrepostos, rótulos concorrentes, unicidade média, bagging e bootstrap sequencial, incluindo experimento Monte Carlo, pesos por atribuição de retorno e início de decaimento temporal). Restante sobre decaimento temporal, “pesos de classe” (pp. 70–73) e exercícios não foram lidos.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Resultados sobrepostos**: rótulos que abrangem `[t_{i,0}, t_{i,1}]` (por exemplo, barreira tripla) dependem dos mesmos retornos sempre que `t_{i,1} > t_{i+1,0}`; portanto, não são **IID**. Limitar o horizonte para evitar sobreposição é “uma solução terrível”. Analogia: sangue de um tubo derramado nos nove seguintes. A maior parte da teoria de ML presume IID. | Dependência entre rótulos. | 59–60 |
| C2 | **Concorrência**: `c_t = Σ_i 1_{t,i}` é a quantidade de rótulos que dependem do retorno `r_{t−1,t}`; **unicidade** do rótulo i em t é `u_{t,i} = 1_{t,i}/c_t`; **unicidade média** `ū_i` é a média de `u_{t,i}` durante sua duração, equivalente ao inverso da média harmônica de `c_t`. Usa informação futura (`t_{i,1}`), mas somente no conjunto de treino com rótulos, não como atributo preditivo; “portanto não há vazamento de informação”. | Quantificar sobreposição. | 60–62 |
| C3 | **Bagging e unicidade**: amostragem bootstrap obtém cerca de `1 − 1/e ≈ 2/3` itens únicos de I. Se o máximo de resultados não sobrepostos é `K << I`, fração única esperada é `1 − e^(−K/I)`; presumir IID gera **sobreamostragem**: observações in-bag são redundantes e parecidas com as out-of-bag, então (1) floresta aleatória vira cópias de uma árvore sobreajustada e (2) **acurácia out-of-bag fica muito inflada**. Soluções: não descartar observações sobrepostas (perde muito); definir `max_samples` ≈ unicidade média; ou usar **bootstrap sequencial**. | Por que bagging padrão falha. | 62–63 |
| C4 | **Bootstrap sequencial**: sortear observações uma a uma, com probabilidade proporcional à unicidade média que cada candidata teria se fosse adicionada ao conjunto já sorteado; redundância é penalizada, não proibida. Exemplo numérico com três rótulos (`p = {5/14, 3/14, 6/14}` no segundo sorteio). **Experimento Monte Carlo** (t1 aleatório): mediana da unicidade média 0,6 para bootstrap padrão versus 0,7 para sequencial (ANOVA p ≈ 0). | Amostras mais próximas de IID. | 63–68 |
| C5 | **Pesos por atribuição de retorno**: `w̃_i = |Σ_{t=t_{i,0}}^{t_{i,1}} r_{t−1,t}/c_t|`, reescalado para `Σ w_i = I`; o peso depende da unicidade e do retorno absoluto atribuível ao rótulo. Inadequado com rótulos “neutros”: “em geral eu recomendaria descartar casos neutros”. | Ponderação de treino. | 68–69 |
| C6 | **Decaimento temporal**: mercados são sistemas adaptativos (Lo), então observações antigas devem pesar menos; fator `d[x] ∈ [0, 1]` multiplica os pesos das amostras por unicidade acumulada (detalhes além das primeiras linhas não lidos). | Não estacionariedade. | 70 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Avaliação que considera sobreposição | ❌ | Backtester avalia operações individualmente sem ajuste; operações de uma estratégia são sequenciais e não sobrepostas (uma posição por vez), então série de P/L não tem resultados sobrepostos. Haveria sobreposição em **resultados no nível do sinal** (cap. 3, O1) e análise de vários bots/ativos. |
| Rótulos concorrentes/unicidade | ❌ | Não há. |
| Bagging/florestas | ❌ | Sem ML. |
| Pesos de amostra/decaimento temporal | ❌ | Não existem. |
| Tamanho efetivo da amostra | ❌ | Informa quantidade de operações; em sinais sobrepostos, número efetivo é menor. |

## 3. Oportunidades

### O1 — Tamanho efetivo da amostra para estatísticas de sinais *(livro: C1, C2, pp. 59–62)*

Na tabela de resultados de sinais proposta em O1 do cap. 3, calcular **concorrência** `c_t` e **unicidade média** por sinal, e informar **N efetivo = Σ ū_i** (ou N × unicidade média) junto a cada estatística (taxa de acerto, retorno médio, frequência de toque das barreiras), para intervalos de confiança usarem contagem efetiva, não nominal. Exemplo: 300 sinais diários com resultados de 20 dias se sobrepõem muito; evidência efetiva pode ser fração disso. Também é útil para operações consecutivas do próprio bot se saídas atrasarem e nova entrada ocorrer antes da saída anterior (impossível com uma posição por vez, possível em vários bots no mesmo ativo). **Complexidade:** baixa. **Riscos:** unicidade é definida somente na duração do rótulo; correção de primeira ordem, não modelo completo de dependência. **Validação:** exemplo do livro (rótulos `[0,3]`, `[2,4]`, `[4,6]`) reproduz `p = {5/14, 3/14, 6/14}` no segundo sorteio e a matriz indicadora; rótulos sem sobreposição dão `ū = 1`.

### O2 — Usar unicidade média ao chamar resultado de sinal de “significativo” *(livro: C3, pp. 62–63; conexão com livro 3)*

No pipeline de evidências (livros 3 e 4, cap. 21), testes t, bootstrap e permutação em resultados de sinais devem usar unidades independentes: bootstrap em blocos ou testes com N efetivo. Constatação do livro: semelhança in-bag/out-of-bag infla acurácia; é o mesmo problema de dependência visto pelo lado da validação (cap. 7). **Complexidade:** baixa–média (regra e N efetivo de O1). **Validação:** em resultados sobrepostos sintéticos sem vantagem, taxa de falso positivo do teste a 5% fica perto de 5% com N efetivo e excede esse valor com N nominal.

### O3 — Bootstrap sequencial e pesos de unicidade (somente se houver ML) *(livro: C4, C5, pp. 63–69)*

Implementar matriz indicadora, unicidade média, bootstrap sequencial e pesos por atribuição de retorno como funções puras, com exemplo numérico do livro em teste unitário. Não construir antes de haver modelo que os exija (meta-rotulagem, cap. 3 O3). Custo: bootstrap sequencial é `O(I²)` na forma ingênua; Monte Carlo do livro exigiu multiprocessamento (6 horas em 24 núcleos para 10⁶ iterações de 10 observações). Preferir subconjuntos ou atalho `max_samples ≈ ū`. **Complexidade:** média; adiar.

### O4 — Decaimento temporal como opção na reestimação móvel/walk-forward *(livro: C6, p. 70)*

Quando houver walk-forward ou reestimação periódica de parâmetros (livro 4, cap. 21 O4), permitir ponderação opcional por recência (janelas antigas contam menos) e relatar sensibilidade. O livro argumenta que mercados se adaptam; custo é menor quantidade efetiva de dados, já escassa em cripto. Parte do projeto walk-forward. **Complexidade:** baixa depois de disponível.

### Não aplicável

Detalhes internos de bagging de floresta aleatória, opções de `BaggingClassifier`, detalhes de motor multiprocessado (cap. 20), balanceamento de pesos de classe (não lido).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | N efetivo para resultados de sinais O1 | alta | – | – | baixa | cap. 3 O1 |
| 2 | Significância com N efetivo O2 | alta | – | – | baixa–média | O1 |
| 3 | Opção de decaimento temporal O4 | baixa | – | – | baixa | walk-forward |
| 4 | Bootstrap sequencial + pesos O3 | média (com ML) | – | – | média | aprovação da linha ML |

## 5. Arquivos afetados

`analytics/domain/` (concorrência, unicidade, N efetivo, bootstrap opcional), testes com exemplo numérico do livro; telas do app exibindo N efetivo.

## 6. Plano incremental

1. Funções de concorrência/unicidade com exemplo numérico em teste.
2. Mostrar N efetivo junto a toda estatística no nível do sinal.
3. Usá-lo em testes de significância.
4. Bootstrap sequencial somente se houver ML.

## 7. Critérios de aceitação e testes

* Matriz indicadora e unicidade média correspondem a cálculos manuais do exemplo de três rótulos; rótulos sem sobreposição dão 1; N efetivo ≤ N nominal.
* Se implementado, bootstrap sequencial tem maior unicidade média que o padrão em t1 aleatório com sementes fixas; determinístico dada uma semente.
* ruff, mypy e testes existentes aprovados.

## Ressalvas

Evidência Monte Carlo é simulação de sobreposições sintéticas (unicidade mediana 0,6 versus 0,7), não dados de mercado. Peso por retorno absoluto dá mais importância a movimentos grandes, podendo concentrar o modelo em crashes cripto raros; é uma escolha de projeto, não um resultado comprovado. Detalhes de decaimento temporal não foram lidos.
