# Livro 5 · Capítulo 8 — Importância de atributos

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 113–121 e início da p. 121 (importância paralelizada versus empilhada) foram lidas. Pp. 122–127 (importância empilhada, experimentos com dados sintéticos e atributos informativos/redundantes/ruído, resultados e exercícios) **não foram lidas**.

**Compatibilidade com a plataforma:** a ideia central — “backtesting não é ferramenta de pesquisa; importância de atributos é” — é princípio de pesquisa aplicável mesmo sem ML (o que causa os resultados de uma estratégia?). Métodos MDI, MDA, SFI e ortogonalização PCA aplicam-se quando existir modelo.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Ciclo de backtest e repetição é o erro mais disseminado**: executar dados num algoritmo, fazer backtest e repetir até obter resultado atraente “provavelmente leva a descoberta falsa”; estatísticos consideram fraude científica (diretrizes ASA). “Em geral, são necessárias cerca de 20 iterações para descobrir uma estratégia de investimento (falsa) no nível de significância padrão de 5%.” | Pesquisa por backtest. | 113 |
| C2 | **Importância da importância de atributos**: antes de qualquer backtest, ajustar classificador em `(X, y)`, avaliar com **CV k-fold purgada** (cap. 7) e perguntar quais atributos sustentam o desempenho. Depois estudar quando importam (regimes), se importam para outros instrumentos/classes de ativos e quais são consistentes no universo. **“Backtesting não é ferramenta de pesquisa. Importância de atributos é.”** | Metodologia de pesquisa. | 113–114 |
| C3 | **Efeitos de substituição** (multicolinearidade) diluem/ocultam importância de atributos relacionados. **MDI (redução média de impureza)**: rápida, dentro da amostra, específica a árvores; soma 1; efeitos de mascaramento (usar subconjuntos aleatórios e tratar zeros como NaN); enviesada a certos preditores; dois atributos idênticos recebem metade cada. **MDA (redução média de acurácia)**: lenta, fora da amostra, qualquer classificador; permutar uma coluna por vez e medir perda de pontuação fora (acurácia, log-loss negativo ou F1); com dois atributos idênticos, MDA considera **ambos** sem importância; pode concluir que **todos** são irrelevantes; exige CV purgada e embargo. | Métodos com efeitos de substituição. | 114–117 |
| C4 | **SFI (importância de atributo único)**: pontuação fora da amostra de cada atributo isolado; sem substituição; também pode concluir que todos não importam; perde efeitos conjuntos/hierárquicos. **Atributos ortogonais** por PCA de atributos padronizados (manter componentes que expliquem ≥95% da variância) como solução parcial de substituição linear. PCA classifica atributos sem rótulos; portanto, **concordância da ordenação PCA com importância baseada em rótulos (tau de Kendall ponderado; exemplo 0,82) sugere que padrão não é totalmente sobreajustado**. | Métodos sem substituição e verificação de plausibilidade. | 117–121 |
| C5 | **Paralelizada versus empilhada**: calcular importância por instrumento e agregar no universo; atributos importantes em vários instrumentos e critérios têm maior chance de refletir fenômeno real (rápido, paralelo; substituição ainda pode ocultar atributos importantes num instrumento individual). | Pesquisa no universo de ativos. | 121 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Análise de importância de atributos | ❌ | Não há atributos/modelo. |
| Proteção contra pesquisa por backtest (contagem de iterações) | ❌ | Usuários refazem backtests/varreduras sem limite; nada conta ou desconta iterações (livro 4, cap. 21 O2). |
| Atribuir resultados a componentes de regra | ❌ | Sem ferramenta de ablação (livro 4, cap. 8 O7). |
| Visão de consistência entre ativos | ❌ | Ver livro 4, cap. 21 O10. |
| Dependência de regime | ❌ | Sem desempenho condicional por regime de volatilidade/tendência. |

## 3. Oportunidades

### O1 — Exibir contagem de iterações: “N backtests/varreduras executados nestes dados” e alerta das 20 iterações *(livro: C1, p. 113)*

Exibir, por conjunto (ativo, timeframe, intervalo) e família de estratégias, número acumulado de backtests e membros de varredura, com nota simples: em nível de significância de 5%, cerca de 20 tentativas independentes tornam esperada uma falsa “descoberta” (alegação do livro; cálculo `1 − 0.95^20 ≈ 64%`, e 20 corresponde ao número esperado de um falso positivo a 5%). Alimenta Sharpe deflacionado (cap. 14). Igual a O2 do cap. 21 do livro 4 e O3 deste livro, cap. 1. **Complexidade:** baixa. **Validação:** contadores coincidem com execuções armazenadas.

### O2 — Atribuir componentes em vez de “otimizar tudo”: ablação/permutação em estratégias de regras *(livro: C2, C3, pp. 113–117 · adaptação nossa)*

Análogo baseado em regras à MDA/SFI: (a) **ablação**: executar estratégia removendo/neutralizando cada componente (desligar filtro, stop, substituir saída por saída temporal) e informar mudança nas métricas por resultado; (b) **teste de permutação de entradas**: para atributos/filtros da série (volatilidade, volume), embaralhar no tempo preservando distribuição e medir perda de desempenho — se nada mudar, componente não contribui; (c) relatar usando **tabela de resultados dos sinais** (livro 5, cap. 3 O1), para atribuição ser independente de saída dependente do caminho. Assim se aplica “pesquisar por importância de atributos, não por backtests”. **Complexidade:** média. **Riscos:** interações (componente só funciona com outro, limitação SFI); amostra pequena. **Validação:** recuperar componente com efeito conhecido inserido; componente de ruído sem efeito.

### O3 — Consistência da importância de componentes entre ativos/regimes *(livro: C2, C5, pp. 114, 121 · conexão com livro 4, cap. 21 O10)*

Repetir O2 entre ativos (BTC, ETH, SOL…) e segmentos de regime (volatilidade alta/baixa, alta/baixa de preços, definidos sem rótulos) e mostrar componentes consistentemente importantes; os consistentes merecem investigação do mecanismo (livro 5, cap. 1 O3). **Complexidade:** média. **Ressalvas:** ativos cripto têm alta correlação; regimes definidos dentro da amostra podem estar sobreajustados.

### O4 — Se houver modelo ML: usar MDI + MDA + SFI com CV purgada e verificação de concordância PCA *(livro: C3, C4, pp. 114–121)*

Diretriz para registro de decisão ML (cap. 3 O3): calcular os três tipos de importância, esperar substituição entre atributos técnicos correlacionados (muitos indicadores são transformações monotônicas), ortogonalizar antes de MDI/MDA, informar tau de Kendall ponderado entre importância e classificação PCA e aceitar resultado “todos os atributos não importam” (não seguir para backtest). **Complexidade:** parte da linha ML.

### Não aplicável

Detalhes de código para sklearn `RandomForest`/`BaggingClassifier`, cálculos de importância empilhada (não lidos), experimentos com dados sintéticos (não lidos).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Contador + alerta de iterações O1 | alta | – | – | baixa | armazenamento de execuções |
| 2 | Atribuição de componente (ablação/permutação) O2 | alta | – | – | média | cap. 3 O1; livro 4 cap. 8 O7 |
| 3 | Consistência entre ativos/regimes O3 | média | – | – | média | O2 |
| 4 | Diretriz de importância ML O4 | – | – | – | linha ML | aprovação ML |

## 5. Arquivos afetados

Consultas de armazenamento de execuções e endpoint analytics de contagens; `analytics/domain/` (mecanismo de ablação/permutação); página de pesquisa do app; documentação.

## 6. Plano incremental

1. Contadores e texto de alerta.
2. Mecanismo de ablação sobre tabela de resultados de sinais.
3. Visões entre ativos/regimes.

## 7. Critérios de aceitação e testes

* Contadores iguais a total de execuções armazenadas; ablação recupera efeito inserido e ≈0 para ruído em dados sintéticos; permutação preserva distribuição marginal do atributo; determinística com semente; ruff, mypy e testes existentes aprovados.

## Ressalvas

“Cerca de 20 iterações” é ilustração aproximada (falsos positivos esperados a 5%), não medida empírica. “Backtesting não é ferramenta de pesquisa” é posição do autor: o livro depois desenvolve metodologia de backtest (caps. 10–16), ou seja, backtests devem vir depois da análise dos fatores que geram previsões, não substituí-la. Pp. 122–127 não foram lidas.
