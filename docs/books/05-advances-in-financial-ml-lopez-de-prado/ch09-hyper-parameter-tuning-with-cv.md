# Livro 5 · Capítulo 9 — Ajuste de hiperparâmetros com validação cruzada

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 129–134 foram lidas (busca em grade com CV purgada, pontuação F1 para meta-rotulagem, classe de pipeline aprimorada, busca aleatória, distribuição log-uniforme e início da discussão de pontuação). Pp. 135–137 (por que `neg_log_loss` é preferível à acurácia em estratégias, exercícios) **não foram lidas**.

**Compatibilidade com a plataforma:** varreduras atuais são grades sobre parâmetros de estratégia. Duas ideias concretas — **busca aleatória com orçamento computacional** e **amostragem log-uniforme** para parâmetros de escala — transferem-se diretamente; CV aplica-se quando existir componente aprendido.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Ajuste de hiperparâmetros é essencial e fonte comum de sobreajuste; CV financeira deve usar purge e embargo (cap. 7). | Sobreajuste no ajuste. | 129 |
| C2 | **CV por busca em grade** percorre combinações de parâmetros e calcula pontuação por CV; exige gerador k-fold purgado, pesos de amostra enviados ao estimador e, opcionalmente, bagging do estimador ajustado. | Ajuste de referência. | 129–131 |
| C3 | **Pontuação**: usar **F1** em meta-rotulagem (modelo que prevê “nunca agir” pode ter alta acurácia/log-loss, mas recall zero); acurácia ou log-loss negativo servem quando todas as classes importam; reclassificar rótulos não afeta acurácia/log-loss, mas afeta F1. | Escolher a métrica correta. | 130 |
| C4 | **CV por busca aleatória**: muitas grades são impraticáveis; amostrar cada parâmetro de uma distribuição (Bergstra et al.) (1) controla **orçamento computacional** independentemente da dimensionalidade; (2) parâmetros irrelevantes não ampliam tempo como na grade. | Busca com orçamento. | 131 |
| C5 | **Distribuição log-uniforme**: para parâmetros não negativos com efeito multiplicativo (SVC `C`, `gamma`), amostrar valores de modo que `log x` seja uniforme em `[log a, log b]`; amostragem uniforme em `[0, 100]` põe 99% dos sorteios acima de 1 e desperdiça esforço. | Amostragem adequada à escala. | 132–133 |
| C6 | Início do argumento para pontuar hiperparâmetros de estratégias de investimento por log-loss negativo, em vez de acurácia (restante não lido). | Escolha de pontuação. | 134 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Varredura em grade | ✅ | Varreduras com `MAX_SWEEP_RUNS`; usuário fornece valores. |
| Busca aleatória com orçamento/semente | ❌ | Somente grade. |
| Amostragem logarítmica | ❌ | Sem helper (também livro 4, cap. 7 O1, cap. 17 O3, cap. 21 O2). |
| CV purgada/com embargo para ajuste | ❌ | Ver cap. 7. |
| Pontuação adequada para filtros | ❌ | Classificação por métricas isoladas (PnL líquido etc.); sem precisão/recall de filtro. |

## 3. Oportunidades

### O1 — Varreduras aleatórias com orçamento, semente e distribuições log-uniformes para inteiros/reais *(livro: C4, C5, pp. 131–133)*

* **Proposta:** modo de varredura `random` com `n_trials`, `seed` e distribuição por parâmetro (`uniform`, `int_uniform`, `log_uniform`, `choice`), registrada na especificação e resultado para reprodutibilidade; combinar com **registro/faixas predefinidas** (livro 4, cap. 21 O2) e análise de vizinhança (livro 4, cap. 21 O1 exige vizinhos para pontos irregulares: usar distância no espaço log-paramétrico normalizado). Log-uniforme combina com parâmetros de período (EMA rápida/lenta, janelas Donchian) e múltiplos de stop/ATR.
* **Motivo:** orçamento independente da quantidade de parâmetros; parâmetros irrelevantes (ex.: limite de filtro sem efeito) não multiplicam a grade; compatível com orientação do livro 4 (espaçamento geométrico, Monte Carlo), com referência publicada.
* **Complexidade:** baixa–média (amostragem, armazenamento, vizinhança logarítmica). **Riscos:** aleatoriedade pode perder ótimos estreitos (aceitável para buscar robustez); resultados dependem da semente (armazená-la); reprodutibilidade exige código de amostragem estável entre versões. **Validação:** sementes reproduzem mesmos pontos; amostras uniformes em espaço log (teste KS como no trecho do livro); `n_trials` respeitado; arredondamento inteiro identifica duplicatas e conta configurações distintas.

### O2 — Pontuar filtros por F1/precisão/recall além de P/L ao ajustar limites *(livro: C3, p. 130)*

Conectar a O4 do cap. 3: ao ajustar limite de filtro (volatilidade, força de tendência), configuração degenerada que “nunca age” pode parecer boa em acurácia ou até Sharpe em amostra curta; informar F1, recall e número de operações junto e exigir mínimo de operações. **Complexidade:** baixa.

### O3 — Se houver ajuste de ML: k-fold purgado + busca aleatória + estimador ajustado em bagging *(livro: C1–C3)*

Parte do registro de decisão ML (cap. 3 O3, cap. 6 O1, cap. 7 O4): não usar `GridSearchCV` sem purge; passar pesos de amostra; pontuação definida por uso (F1 em meta-rotulagem). **Complexidade:** linha ML.

### Não aplicável

Falhas e soluções de pipeline do sklearn (até escolher biblioteca), parâmetros específicos de SVC/RBF.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Varreduras aleatórias (log-uniforme) O1 | média–alta | – | – | baixa–média | especificação/registro de varredura |
| 2 | Pontuação de filtros O2 | média | – | – | baixa | cap. 3 O4 |
| 3 | Regras de ajuste ML O3 | – | – | – | linha ML | aprovação |

## 5. Arquivos afetados

Especificação/serviço de varredura em `backtesting/application`, módulo de amostragem em `backtesting/domain` (puro, com semente), `docs/openapi.json`, formulário de varredura do app (opções de distribuição), testes.

## 6. Plano incremental

1. Amostradores com semente e testes unitários; registrar especificação.
2. Modo de varredura aleatória.
3. Análise de vizinhança no espaço logarítmico (livro 4, cap. 21 O1).

## 7. Critérios de aceitação e testes

* Amostragem com semente reproduzível bit a bit; log-uniforme passa teste KS nos valores em log; configurações distintas contabilizadas; sem modo novo, varreduras funcionam como hoje; ruff, mypy e testes aprovados.

## Ressalvas

Busca aleatória tem boas propriedades para hiperparâmetros de ML (Bergstra et al.), mas grade completa com espaçamento geométrico é viável e mais interpretável para 2–3 parâmetros de regras de negociação; busca aleatória é mais útil quando aumenta a quantidade de parâmetros. Distribuição log-uniforme é apresentada pelo autor como definição própria (hoje existe em scipy como `loguniform`). Pp. 134–137 não foram lidas.
