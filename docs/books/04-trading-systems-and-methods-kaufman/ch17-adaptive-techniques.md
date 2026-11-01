# Livro 4 · Capítulo 17 — Técnicas adaptativas

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foram lidas as pp. 779–791 e 797–798. O sistema adaptativo intradiário de rompimento (793–797) foi consultado superficialmente. Os detalhes de McGinley Dynamics, variantes de momentum adaptativo e a seção final “Considerando métodos adaptativos” (790–796, 798–800) foram lidos em parte ou não foram lidos. O autor do capítulo é também o autor do livro: KAMA é **um método próprio dele** (*Smarter Trading*, 1995), algo importante ao interpretar a tabela de desempenho.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Uma **técnica adaptativa** muda conforme as condições do mercado, principalmente alterando automaticamente o período de cálculo de uma tendência ou indicador: lenta em mercados laterais/ruidosos e rápida em tendências nítidas. O autor reconhece que **identificar um mercado lateral é muito difícil** (o preço pode terminar onde começou depois de uma semana violenta). | Uma única velocidade não serve para todas as condições. | 779 |
| C2 | **KAMA (média móvel adaptativa de Kaufman)**: `KAMA_t = KAMA_{t−1} + sc_t × (p_t − KAMA_{t−1})`, `sc_t = [ER_t × (fastest − slowest) + slowest]²`, `fastest = 2/(2+1)`, `slowest = 2/(30+1)` por padrão; `ER_t = |p_t − p_{t−n}| / Σ|p_i − p_{i−1}|` (a **razão de eficiência** do cap. 1; `n` ≈ 8–10, limitado pela quantidade de fechamentos consecutivos na mesma direção). Elevar ao quadrado torna a ponta lenta extremamente lenta (equivalente a cerca de 900 períodos) e a ponta rápida equivale a uma tendência de 4–5 períodos. Ruído não é volatilidade (analogia do passeio do marinheiro bêbado). **Regras práticas**: `ER = 1` pode ocorrer com pequenas derivações; acrescentar um filtro pequeno para uma variação média mínima. Como a linha exponencial de tendência inverte a direção sempre que o preço a cruza, acrescentar um **filtro pequeno às mudanças de direção** (por exemplo, 0,1 desvio-padrão das variações da linha); negociar a **direção da linha de tendência**; manter `n` abaixo de 14; manter o limite superior em 30 (para reduzir sensibilidade, elevar o limite inferior acima de 2). | Velocidade da tendência ajustada pelo ruído. | 779–783 |
| C3 | **Outras médias adaptativas**: **MA fractal adaptativa** de Ehlers (dimensão fractal); **VIDYA** de Chande (constante fixa 0,20 escalada por `k = stdev_n/stdev_m` dos fechamentos; o livro observa que retornos talvez sejam melhores que preços); média adaptativa por **correlação (r²)**; **MAMA/FAMA** de Ehlers (variação da taxa de fase; FAMA como linha de sinal). | Variedade de medidas de adaptação. | 783–786 |
| C4 | **Comparação, 1990–julho de 2011, 15 mercados futuros (Tabela 17.1), antes de custos**: fator de lucro médio **KAMA 1,53**, MAMA 1,36, correlação 1,22, VIDYA 1,17; menos operações por mercado acompanham melhores resultados (KAMA ~159 operações, VIDYA ~443); todos os métodos foram lucrativos em média; **resultados do índice S&P são fracos** (KAMA 1,11, outros < 1). É difícil comparar de forma justa com uma média móvel fixa porque KAMA abrange períodos de 5² a 30² (25–900): amostrar os períodos fixos com distribuição progressiva (logarítmica ou exponencial). | Evidências e limitações. | 786–788 |
| C5 | **Tornar o momentum adaptativo**: mapear qualquer oscilador limitado para uma constante de suavização entre 0 e 1 (`sc = M`, `|M|`, `M/100`, `|M/100|`); o RSI adaptativo é mais sensível em períodos laterais que KAMA, a menos que seja elevado ao quadrado; **estocástico adaptativo** (retrospectiva definida pela razão de eficiência); **McGinley Dynamics** (`MD_t = MD_{t−1} + (p_t − MD_{t−1}) / (k·n·(p_t/MD_{t−1})^4)`, `k = 0.6`). | Ampliar a ideia. | 788–790 |
| C6 | **Processo adaptativo**: testar o sistema novamente de forma regular com dados recentes (comprimento fixo ou após mudança de regime); o problema é a **falta de dados**: “quanto mais rápido você reage, menos dados tem para decidir”; **exemplo de desenvolvimento**: média móvel de comprimento variável, cujo período interpola entre 30 e 5 dias conforme o z-score da variação do preço esteja entre 0,25 e 1,75 desvios-padrão (Arrington). | Adaptar por reestimação ou volatilidade. | 797–798 |

Os exemplos são de futuros. As observações sobre cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Médias móveis adaptativas | ❌ | `ema_crossover` usa EMAs de períodos fixos. |
| Razão de eficiência | ❌ | Não é calculada em lugar algum (cap. 1, O1 do livro 4). |
| Filtro de direção da linha de tendência contra microinversões | ❌ | Ainda não aplicável. |
| Grades de parâmetros com períodos fixos amostrados progressivamente | ❌ | Ver O1 do cap. 7. |
| Reestimação periódica de parâmetros | ❌ | B-WALK-FORWARD. |

## 3. Oportunidades

### O1 — Estratégia `kama_trend` (experimento) *(livro: C2, C4, pp. 779–788)*

* **Proposta:** estratégia de tendência somente comprada, que mantém a posição quando a linha KAMA aponta para cima e sai quando aponta para baixo, com parâmetros `er_period` (padrão 10), `fast_period` (2), `slow_period` (30) e `direction_filter` (variação mínima da linha de tendência, em desvios-padrão das variações recentes da própria linha). Dimensionamento e risco passam pelo módulo existente. A implementação precisa da razão de eficiência, constante de suavização ao quadrado e desvio-padrão amostral; tudo pode ser expresso em `Decimal`, com uma fronteira `float` documentada para o desvio-padrão, se necessário.
* **Motivo:** KAMA é o método adaptativo de tendência com justificativa direta baseada em ruído (cap. 1 do livro 4) e, na tabela do próprio autor, apresenta o maior fator de lucro e o menor número de operações entre os quatro; uma linha de tendência adaptativa reduz falsos sinais em fases ruidosas, comuns em cripto. **Ressalvas:** o autor desenvolveu KAMA, então a comparação o favorece; os resultados são anteriores a custos, em futuros, e foram fracos no índice S&P, o mercado mais ruidoso. É preciso medir se ajuda em cripto.
* **Complexidade:** média (novo arquivo de estratégia, registro, formulários e testes). **Riscos:** mais parâmetros (5), correlação com outras regras de tendência (N efetivo); a constante elevada ao quadrado deixa a ponta lenta extremamente lenta (equivalente a 900 períodos), podendo atrasar saídas após reversões; casos-limite quando a linha fica plana. **Validação:** teste de truncamento; casos-limite de ER; comparação com conjunto de períodos EMA **amostrados progressivamente** (não apenas uma EMA), pelo pipeline varredura → melhor de N → validação; sensibilidade a custos; estabilidade entre épocas.

### O2 — Helper compartilhado da razão de eficiência *(livro: C2, p. 781)*

Usado pelos diagnósticos (cap. 1, O1 do livro 4), pelo filtro de qualidade de tendência (cap. 6, O1) e por KAMA. Uma única implementação. **Complexidade:** baixa.

### O3 — Regra para comparação justa entre adaptativo e fixo *(livro: C4, p. 788)*

Acrescentar às diretrizes de pesquisa: ao comparar um método adaptativo com um de período fixo, amostrar os períodos fixos em escala logarítmica ao longo da faixa coberta pelo método adaptativo e apresentar a distribuição dos resultados fixos, não apenas um período. Isso evita escolher uma referência fixa excepcionalmente boa ou ruim. **Complexidade:** documentação + helper de varredura (O1 do cap. 7).

### O4 — Processo adaptativo = reestimação periódica: conexão com walk-forward *(livro: C6, p. 797)*

O alerta do livro (poucos dados quando se reage rapidamente) é a mesma troca envolvida no projeto walk-forward (cap. 6, O5 do livro 3). Não exige trabalho separado; o projeto B-WALK-FORWARD deve registrar quantos dados são usados em cada reestimação.

### O5 — Não adicionar VIDYA, r², MAMA/FAMA ou McGinley sem evidência *(livro: C3, C5)*

São medidas de adaptação alternativas com o mesmo propósito de KAMA; adicioná-las multiplica o universo de regras e a carga de testes múltiplos com métodos quase duplicados. Preferir um método adaptativo (KAMA) e compará-lo a regras fixas; adicionar outro somente se houver hipótese documentada de comportamento diferente. **Complexidade:** nenhuma.

### Não aplicável

Dimensão fractal e métodos de fase MESA/Hilbert (baseados em ciclos; cap. 11 não foi considerado), otimização do rompimento intradiário adaptativo, média móvel de comprimento variável de Arrington (KAMA a substitui para nosso propósito).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Helper ER O2 | – | – | – | baixa | – |
| 2 | Regra de comparação O3 | alta | – | – | doc. | O1 do cap. 7 |
| 3 | Estratégia KAMA O1 | média | – | – | média | O2; pipeline do livro 3 |
| 4 | Não duplicar métodos próximos O5 | – | – | – | nenhuma | – |
| 5 | Conexão com walk-forward O4 | – | – | – | – | B-WALK-FORWARD |

## 5. Arquivos afetados

`strategies/domain/` (helper e novo arquivo de estratégia), registro, `strategies/catalog.py`, formulários e rótulos de estratégia do app, testes incluindo teste de truncamento, `check:consistency`.

## 6. Plano incremental

1. Helper ER com os casos-limite do livro.
2. Estratégia KAMA submetida ao pipeline completo de validação (teste de truncamento, varredura de custos, melhor de N, bloqueio de validação).
3. Comparação com amostra progressiva de períodos EMA fixos.

## 7. Critérios de aceitação e testes

* ER = 1 para uma linha reta e ≈ 0 para uma série alternada; com `ER ≡ 1`, KAMA equivale a uma EMA de período `fast`; com `ER ≡ 0`, acompanha a constante lenta ao quadrado; inversões da linha são filtradas pelo limite.
* Nenhuma alteração nas estratégias existentes; ruff, mypy e todos os testes aprovados.

## Ressalvas

A tabela de desempenho (fatores de lucro médios entre 1,17 e 1,53) é anterior a custos, cobre mercados futuros distintos — inclusive mercados muito tendenciais, como Eurodólares — e foi produzida pelo autor de KAMA. As constantes de suavização ao quadrado tornam KAMA muito mais lenta em ambientes ruidosos do que a indicação nominal de “30 períodos” sugere.
