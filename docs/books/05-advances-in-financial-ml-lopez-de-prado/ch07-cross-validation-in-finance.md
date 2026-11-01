# Livro 5 · Capítulo 7 — Validação cruzada em finanças

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 103–111 foram lidas (objetivo da CV, por que k-fold falha, purge e embargo, classe `PurgedKFold`, problemas do sklearn e exercícios). Trechos de código foram consultados superficialmente.

**Relevância:** capítulo de validação que qualquer componente aprendido (seleção de parâmetros via walk-forward, meta-rotulagem ML) deve respeitar; conceito subjacente — **vazamento por informação sobreposta entre treino e teste** — também se aplica à divisão treino/teste e seleção por varredura atuais.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | CV estima erro de generalização; testar nos próprios dados de treino é como compressão com perda: “resumir dados com fidelidade extrema e, ainda assim, sem poder de previsão”. CV k-fold (dividir em k subconjuntos, treinar em k−1, testar no restante) dá k métricas; em classificador binário, aprendizado é indicado por acurácia > 1/2. Em finanças, CV serve ao desenvolvimento (ex.: hiperparâmetros) e backtesting. | Finalidade da CV. | 103–104 |
| C2 | **Por que k-fold falha em finanças**: (1) observações não são IID (autocorrelação, rótulos sobrepostos), então **vazamento** leva informação de teste ao treino; com atributos irrelevantes, gera **falsas descobertas**; (2) o teste é reutilizado no desenvolvimento → **testes múltiplos e viés de seleção** (caps. 11–13). Vazamento exige `(X_i, Y_i) ≈ (X_j, Y_j)`, não apenas `X_i ≈ X_j` ou `Y_i ≈ Y_j`. Mitigações: remover do treino observações cujos rótulos dependem do teste; evitar sobreajuste (parada antecipada, bagging com `max_samples ≈ unicidade média`, bootstrap sequencial). | Vazamento. | 104–105 |
| C3 | **Purge (expurgo)**: retirar do treino qualquer observação cujo intervalo de rótulo se sobreponha aos intervalos dos rótulos de teste (três condições de sobreposição entre `[t_{j,0}, t_{j,1}]` e `[t_{i,0}, t_{i,1}]`). Para teste contíguo, pode-se usar intervalo único. Diagnóstico: se desempenho continuar crescendo quando `k → T`, o backtest está lucrando com vazamentos; após purge, deve estabilizar. | Remover rótulos sobrepostos. | 105–107 |
| C4 | **Embargo**: além do purge, retirar do treino observações que vêm imediatamente **depois** do teste (autocorrelação), ampliando o fim do rótulo de teste por `h`; `h ≈ 0.01 T` costuma bastar. Não é necessário embargo antes do teste: rótulos de treino encerrados antes do início do teste só contêm informação disponível naquele início. | Dependência serial residual. | 107–108 |
| C5 | Classe **`PurgedKFold`**: folds de teste contíguos (sem embaralhar), treino com purge e embargo usando tempos finais dos rótulos `t1`. “Em geral, é necessário expurgar e aplicar embargo a observações sobrepostas sempre que se divide treino/teste”, seja para ajuste de hiperparâmetros, backtest ou avaliação. | Implementação. | 108–109 |
| C6 | **Problemas de CV no scikit-learn**: funções de pontuação desconhecem `classes_`; `cross_val_score` não passa pesos de amostra ao avaliador log-loss; usar `cvScore` do livro. “Leia sempre todo o código que executar.” | Armadilhas das ferramentas. | 109–110 |
| C7 | Exercícios: por que embaralhar antes de k-fold invalida CV financeira; comparar k-fold embaralhado, k-fold e k-fold purgado em conjunto de dados. | Prática. | 110–111 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Divisão treino/teste respeita ordem temporal | ✅ | `backtesting/domain/segments.py`: uma divisão cronológica (sem embaralhamento). |
| Purge de informação sobreposta na fronteira | ❌ | Operações/estado de indicador abertos na fronteira podem atravessar segmentos; indicador calculado na série completa usa aquecimento pré-teste (passado, aceitável), mas operação aberta no treino e fechada no teste contamina ambos. Verificar tratamento de posições em `segments.py`. |
| Embargo | ❌ | Nenhum. |
| Testes múltiplos ao selecionar pelo conjunto de teste | ❌ | Varreduras escolhem melhor execução em treino/teste e usuário pode iterar; sem contagem (livro 4, cap. 21 O2/O3). |
| k-fold ou outra CV | ❌ | Nenhuma; parâmetros não são aprendidos. |
| Testes de vazamento | ❌ | Não há teste de truncamento (livro 1, cap. 3 O2). |

## 3. Oportunidades

### O1 — Higiene da fronteira da divisão atual: expurgar operações que cruzam corte e incluir embargo *(livro: C3, C4, pp. 105–108)*

* **Proposta:** (a) ao avaliar segmento de **teste**, começar sem posição e ignorar operação cuja entrada esteja no treino; (b) ao selecionar parâmetros no **treino**, fechar à força ou descartar posição que atravessaria o corte, para resultados de treino não dependerem de preços de teste; (c) deixar **intervalo de embargo** de `h` candles (padrão ~1% do segmento ou maior entre lookback/permanência máximos) entre treino e teste para evitar atravessar a fronteira com autocorrelação e memória de indicadores; (d) informar se segmentos passaram por purge/embargo.
* **Motivo:** há possibilidade pequena, mas real, de vazamento por operações abertas e indicadores lentos na fronteira (EMA longa tem memória de centenas de candles; Donchian usa janelas). Diagnóstico do livro (“desempenho continua crescendo com k”) vira verificação de mudança nos resultados quando se amplia embargo. **Complexidade:** baixa–média (lógica de segmentos/contabilização de métricas). **Riscos:** reduz dados úteis e muda resultados existentes (versionar avaliação e manter comportamento antigo sob flag para reprodutibilidade). **Validação:** série sintética com dependência futura inserida através do corte detectada; vazamento some com embargo; resultados de treino invariantes a preços do segmento de teste (teste de propriedade).

### O2 — Validação cruzada cronológica nas varreduras em vez de uma única divisão (“CV em blocos com purge”) *(livro: C3–C5, pp. 105–109)*

Substituir ou complementar divisão única por **k blocos contíguos de teste**; para cada bloco, selecionar parâmetros nos demais dados com purge e embargo; informar distribuição de resultados fora da amostra entre blocos e estabilidade dos parâmetros selecionados. É variante não sequencial do walk-forward (livro 4, cap. 21 O4) e etapa para CV purgada combinatória (cap. 12). Ressalvas: em estratégia de tendência num ativo com deriva, bloco em mercado de baixa testa regime diferente (útil); preferir k pequeno (5), pois “particionamento excessivo volta a pôr no teste amostras muito parecidas às do treino” (cap. 6). **Complexidade:** média–alta (reutilizar motor; computação cresce com k). **Validação:** observação de treino não se sobrepõe a nenhum intervalo de teste/embargo; determinístico; k = 1 equivale à divisão atual.

### O3 — Suíte de testes de vazamento como parte do CI *(livro: C2, C3, pp. 104–107)*

Testes automáticos para (1) comparar embaralhado versus ordenado em série sem sinal (passeio aleatório): k-fold embaralhado deve mostrar desempenho significativamente melhor que k-fold purgado para atributo dependente, demonstrando vazamento; e (2) teste de truncamento por estratégia. São proteções de regressão a mudanças em segmentação/código de atributos. **Complexidade:** baixa–média. **Validação:** por construção.

### O4 — Se houver componente ML/aprendido, usar PurgedKFold com embargo como único método de CV *(livro: C5, C6, pp. 108–110)*

Mesma conclusão de O1 do cap. 6: não usar k-fold embaralhado nem acurácia OOB como estimativa; implementar k-fold purgado com pesos de amostra enviados à função de pontuação; manter código próprio de avaliação (falhas de bibliotecas). **Complexidade:** parte da linha de ML.

### Não aplicável

Detalhes da subclasse `KFold` do sklearn e bugs listados (até escolha de biblioteca).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Testes de vazamento O3 | alta | – | alta | baixa–média | – |
| 2 | Purge de fronteira + embargo O1 | alta | – | – | baixa–média | segmentos |
| 3 | CV purgada em blocos O2 | alta | – | – | média–alta | O1 |
| 4 | Regras de CV para ML O4 | alta (futuro) | – | – | linha ML | aprovação ML |

## 5. Arquivos afetados

`backtesting/domain/segments.py`, `backtesting/domain/engine.py` (começar teste sem posição, fechamento forçado no corte do treino), `backtesting/application/service.py` (parâmetro de embargo, relatório), `docs/openapi.json`, formulário de backtest no app (opções de segmento), testes.

## 6. Plano incremental

1. Testes de vazamento e truncamento.
2. Purge/embargo de fronteira atrás de opção; registrar no resultado.
3. CV purgada em blocos para varreduras.

## 7. Critérios de aceitação e testes

* Teste dependente de dados na fronteira falha antes e passa depois; comportamento padrão não muda sem opção ativada; hash de reprodutibilidade inclui opções de segmentação; ruff, mypy e testes existentes aprovados.

## Ressalvas

“h ≈ 0,01 T” é regra prática baseada na experiência do autor, não derivada. Trocas entre k pequeno/grande são discutidas qualitativamente. O capítulo não prova generalização de nenhuma estratégia específica; controla uma fonte de otimismo (vazamento) e reconhece que testes múltiplos são problema separado (caps. 11–14).
