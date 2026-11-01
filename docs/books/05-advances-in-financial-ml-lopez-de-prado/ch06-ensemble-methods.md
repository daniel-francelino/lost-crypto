# Livro 5 · Capítulo 6 — Métodos de conjunto

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 93–102 foram lidas integralmente (viés/variância/ruído, bagging, floresta aleatória, boosting, comparação em finanças, bagging para escalabilidade e exercícios). Trechos de código foram consultados superficialmente.

**Compatibilidade com a plataforma:** relevante somente se um modelo ML for aprovado (cap. 3 O3). Fornece regras de projeto (preferir bagging a boosting, evitar redundância, por que acurácia out-of-bag engana), não recursos para o sistema atual baseado em regras. Nada deve ser implementado antes dos pré-requisitos de avaliação (caps. 7, 12, 14).

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Três fontes de erro**: viés (pressupostos irreais, subajuste), variância (sensibilidade a pequenas mudanças no treino, sobreajuste; “confundir ruído com sinal”) e ruído (irredutível). Erro quadrático médio = viés² + variância + ruído. Conjuntos de aprendizes fracos reduzem viés e/ou variância. | Diagnóstico de erro do modelo. | 93–94 |
| C2 | **Bagging**: ajustar `N` estimadores em amostras bootstrap (independentes e paralelizáveis), calcular média ou voto majoritário. Variância da previsão agregada `= σ̄²(ρ̄ + (1 − ρ̄)/N)`; bagging ajuda **somente se a correlação média `ρ̄ < 1`**. Quantidade suficiente de estimadores torna voto majoritário mais preciso que estimadores individuais **somente se cada um for melhor que o acaso** (`p > 1/k`); bagging não recupera classificadores ruins e reduz variância mais que viés. | Reduzir variância. | 94–97 |
| C3 | **Redundância das observações** (rótulos não IID, cap. 4) causa dois danos: (1) amostras bootstrap quase idênticas, `ρ̄ ≈ 1`, então bagging não reduz variância independentemente de `N` (por exemplo, rótulos que abrangem 100 barras: amostrar ~1% das observações por estimador); (2) **acurácia out-of-bag inflada**, pois amostras de treino e OOB são quase iguais. Preferir CV k-fold adequada, sem embaralhar (cap. 7), e k pequeno. | Uso incorreto de bagging em finanças. | 97–98 |
| C4 | **Floresta aleatória**: bagging + subconjuntos aleatórios de atributos por divisão (reduz correlação); fornece importância dos atributos (cap. 8) e acurácia OOB (inflada em finanças). Com amostras redundantes, ainda sobreajusta (árvores quase idênticas). Correções: reduzir `max_features`; parada antecipada com `min_weight_fraction_leaf` (ex.: 5%) para aproximar acurácia OOB da CV fora da amostra; bagging de árvores de decisão (ou florestas de uma árvore) com `max_samples = unicidade média`; substituir bootstrap por bootstrap sequencial; ajustar sobre PCA dos atributos; usar `class_weight='balanced_subsample'`. | Controlar sobreajuste em RF. | 98–99 |
| C5 | **Boosting** (AdaBoost): ajustar aprendizes fracos sequencialmente, aumentar peso das observações classificadas incorretamente e manter estimadores melhores que o acaso; reduz variância e viés. | Alternativa de conjunto. | 99–100 |
| C6 | **Bagging versus boosting em finanças**: boosting combate subajuste, mas eleva risco de sobreajuste. Como dados financeiros têm baixa razão sinal/ruído, “sobreajuste costuma ser preocupação maior que subajuste”; por isso, **bagging tende a ser preferível** e pode ser paralelizado. | Escolha do conjunto. | 100–101 |
| C7 | **Bagging para escalabilidade**: agrupar aprendizes-base que não escalam (SVM), com parada antecipada rigorosa (`max_iter`, `tol`, `max_depth`); perda de qualidade individual é compensada pela redução da variância, obtendo estimativas rápidas e robustas em conjuntos enormes. | Custo computacional. | 101 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Modelos ML e conjuntos | ❌ | Não existem na base. |
| Controle de sobreajuste em componentes aprendidos | ⚠️ | Busca de parâmetros em grade com divisão treino/teste; sem tratamento de correlação/variância. |
| Conjunto de parâmetros (“bagging de regras”) | ❌ | Um conjunto de parâmetros por bot. |

## 3. Oportunidades

### O1 — Se ML for adicionado: bagging de aprendizes rasos com parada antecipada e `max_samples ≈ unicidade média`; rejeitar boosting por padrão *(livro: C2–C6, pp. 94–101)*

Registrar restrições de projeto na decisão de linha ML (cap. 3 O3): árvores em bagging com baixa profundidade, parada antecipada, `max_samples` ligado à unicidade média (cap. 4 O1), pesos de classe balanceados e saídas probabilísticas; medir `ρ̄` entre previsões das árvores (se `ρ̄ ≈ 1`, conjunto não agrega); nunca usar acurácia OOB como estimativa de desempenho; avaliar por CV purgada (cap. 7) e no nível do sistema (cap. 14). Boosting somente como experimento documentado com prova fora da amostra. **Complexidade:** nenhuma agora (diretriz); alta quando ML chegar.

### O2 — Experimento de “conjunto de regras”: agrupar parâmetros, sem aprender modelo *(livro: C2, pp. 94–96 · adaptação nossa)*

A fórmula de variância sugere análogo para estratégias por regras: em vez de escolher um parâmetro “melhor” (viés de seleção), executar **conjunto de parâmetros vizinhos** (por exemplo, vários pares rápido/lento de EMA em grade logarítmica) e combinar sinais por voto ou posições médias. Se correlação entre membros for menor que 1, conjunto reduz variância dos resultados em relação a um membro; se platô for real (livro 4, cap. 21), reduz dependência da escolha exata. Exige pipeline de evidências; plataforma tem um conjunto de parâmetros por bot, então seria novo tipo “estratégia de conjunto”. **H-PARAM-ENSEMBLE.** **Complexidade:** média. **Riscos:** membros muito correlacionados (regras de tendência nos mesmos preços), portanto ganhos pequenos; execução mais complexa (posição líquida por votos); mais operações se membros discordarem. **Validação:** comparar ao melhor individual, membro aleatório e centro do platô fora da amostra; calcular correlação média dos membros.

### O3 — Verificação de Condorcet/voto majoritário para sinais combinados *(livro: C2, p. 96 · somente ideia)*

Ganho de acurácia por voto majoritário exige que cada votante supere o acaso e seja razoavelmente independente. Antes de combinar sinais (tendência + rompimento + reversão à média), medir taxa de acerto individual e correlação entre eles. Parte da visão de diversificação/carteira (livro 4, cap. 24 O1/O5). **Complexidade:** baixa.

### Não aplicável

Problemas e opções específicos do sklearn, escalabilidade de SVM, detalhes internos do AdaBoost, PCA de atributos (até existir ML).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Restrições de projeto O1 (registro de decisão ML) | alta (futuro) | – | – | doc. | – |
| 2 | Verificação de votação O3 | baixa | – | – | baixa | diagnósticos |
| 3 | Experimento conjunto de parâmetros O2 | média | baixa | – | média | varredura + pipeline |

## 5. Arquivos afetados

Documentação (`docs/books`, registro de decisões); para O2, `strategies/domain/` (estratégia de conjunto), registro, catálogo; analytics para correlação entre membros.

## 6. Plano incremental

Manter O1 como diretriz; avaliar O2 somente após haver análise de platô (livro 4, cap. 21 O1).

## 7. Critérios de aceitação e testes

Para O2: sinal combinado determinístico a partir dos membros; correlação informada; padrões inalterados; teste de truncamento para cada membro; ruff, mypy e testes aprovados.

## Ressalvas

Fórmulas de variância e acurácia de bagging pressupõem estimadores independentes no cálculo de acurácia e correlação média entre pares na fórmula de variância. Nestas páginas não há comparação empírica de bagging versus boosting em finanças; preferência por bagging é argumento, não resultado medido.
