# Livro 5 · Capítulo 16 — Alocação de ativos com aprendizado de máquina (paridade hierárquica de risco)

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 221–227 foram lidas integralmente (motivação, maldição de Markowitz, relações hierárquicas e agrupamento em árvore). Etapas 2–3 e exemplo numérico/Monte Carlo (pp. 228–245) foram vistos somente por títulos/frases-chave; apêndices (provas, código) e exercícios não foram lidos.

**Compatibilidade:** alocação entre múltiplos ativos/estratégias. Plataforma negocia um ativo por bot com capital independente; é assunto **futuro** (mesmo status do livro 4, cap. 24). Registrado por ser resposta do livro a alocação robusta e pelo alerta contra otimizar covariâncias, aplicável a qualquer alocador.

## 1. Resumo do capítulo

| ID | Conceito | Páginas |
|---|---|---|
| C1 | **Paridade Hierárquica de Risco (HRP)** aborda três problemas de otimizadores quadráticos (CLA de Markowitz): **instabilidade, concentração e desempenho inferior**; não precisa inverter matriz de covariância e funciona com matrizes singulares/mal condicionadas. Alegação: Monte Carlo mostra variância fora da amostra menor que CLA (embora CLA minimize variância) e paridade de risco tradicional. Aplicável à alocação entre estratégias ML. | 221 |
| C2 | **Maldição de Markowitz**: maior correlação entre investimentos aumenta número de condição da covariância e instabilidade da inversa; erros de estimação podem anular diversificação. São necessárias pelo menos `N(N+1)/2` observações IID para covariância não singular (50 ativos ≈ 5 anos de dados diários IID, hipótese irrealista de estacionariedade). Até carteira ingênua com pesos iguais superou otimização média-variância e baseada em risco fora da amostra (De Miguel et al. 2009); CLA é muito sensível a pequenas mudanças nos retornos esperados (Michaud). | 222–223 |
| C3 | **Hierarquia em vez de grafo completo**: matriz de correlação trata cada investimento como substituto de qualquer outro (1.225 arestas para 50 ativos); árvore tem `N−1` arestas, então pesos são rebalanceados entre pares, de cima para baixo. Etapas HRP: **(1) agrupamento em árvore** (distância `d_{i,j} = sqrt((1 − ρ_{i,j})/2)`, métrica válida; distância entre distâncias; ligação aglomerativa, ex. ponto mais próximo; exemplo com 3 ativos); **(2) quase-diagonalização** (reordenar linhas/colunas para itens semelhantes ficarem adjacentes); **(3) bisseção recursiva** (dividir pesos de cima para baixo usando variâncias inversas das variâncias dos grupos; alocação por variância inversa é ótima para covariância diagonal). | 223–229 |
| C4 | **Exemplo numérico** (10 ativos, dados aleatórios com colunas correlacionadas): CLA concentra 92,66% nos 5 maiores e dá peso zero a 3 investimentos; HRP concentra 62,57% nos 5 maiores; variância inversa (IVP) distribui ~10% cada. Desvio-padrão dentro da amostra parecido (HRP 0,4640, CLA um pouco menor). **Monte Carlo fora da amostra** (choques e saltos aleatórios): variância carteira CLA 0,1157, IVP 0,0928, **HRP 0,0671** — variância CLA é 72,47% maior que HRP. Retornos médios ≈ 0. Autor conclui que HRP melhora Sharpe fora da amostra. (Simulação em dados sintéticos criados pelo autor.) | 229–234 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Alocação multiativo | ❌ | Bots independentes; sem alocador/módulo de carteira (diagnóstico livro 4, cap. 24). |
| Estimação correlação/covariância | ❌ | — |
| Agrupamento de ativos | ❌ | — |

## 3. Oportunidades

### O1 — Se houver alocador para vários bots, começar por **pesos de risco igual (volatilidade inversa)** e considerar HRP somente com ≥ ~8–10 ativos/estratégias suficientemente diferentes *(livro: C2–C4)*

Com base na própria evidência do livro (carteiras ingênuas e paridade de risco são difíceis de superar fora da amostra; CLA é instável), padrão robusto mais simples é alocação por volatilidade inversa entre bots (livro 4 caps. 23/24); HRP é etapa seguinte se correlação importar. Observação nossa para cripto: com poucos ativos líquidos muito correlacionados (um fator dominante), agrupamento acrescenta pouco; estratégias (tendência versus reversão) podem ser folhas mais significativas. **Complexidade:** nenhuma agora.

### O2 — HRP como função pura de pesquisa (opcional) *(livro: C3, pp. 224–229)*

Implementar distância de correlação, agrupamento de ligação única (é possível sem scipy), quase-diagonalização e bisseção recursiva sobre matriz de covariância. Testar exemplo de 3 ativos do livro (`D = [[0, .3873, .6325], [.3873, 0, .7746], [.6325, .7746, 0]]`, distância euclidiana entre distâncias `[[0, .5659, .9747], [.5659, 0, 1.1225], [.9747, 1.1225, 0]]`, primeiro grupo `(1,2)`). Usar na visão de carteira (livro 4 cap. 24 O1) como peso **informativo**, nunca automático. **Complexidade:** média. **Validação:** exemplos do livro; pesos somam 1; invariância à ordem dos ativos; funciona com covariância singular.

### O3 — Comparar alocadores por Monte Carlo em dados sintéticos e bootstrap antes de adotar um *(livro: C4, pp. 233–234 · conexão com cap. 13 O1)*

Reexecutar comparação fora da amostra do livro (pesos iguais, IVP, HRP, variância mínima) no gerador sintético da plataforma e em retornos reais reamostrados por bootstrap; adotar método somente se vencer de forma consistente fora da amostra e sobreviver a custos/rebalanceamento. **Complexidade:** média. **Validação:** sementes reproduzíveis.

### Não aplicável

Detalhes internos/implementação Python da CLA, apêndices matemáticos (não lidos), aplicações a universos grandes.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Peso padrão de volatilidade inversa O1 (registro de decisão) | – | média | – | doc. | visão de carteira multi-bot |
| 2 | Comparação de alocadores em sintéticos O3 | média | média | – | média | cap. 13 O1 |
| 3 | Função HRP O2 | – | baixa | – | média | — |

## 5. Arquivos afetados

Documentação; futuro `analytics/domain/portfolio` (HRP, IVP) e testes.

## 6. Plano incremental

Adiar até haver visão de carteira e segunda família de estratégia.

## 7. Critérios de aceitação e testes

Exemplos do livro reproduzidos; pesos não negativos, somam um e são invariantes à permutação; nenhuma alteração automática no capital dos bots.

## Ressalvas

Toda evidência lida é simulação em dados gerados pelo autor; o livro menciona confirmação histórica por outros (Kolanovic et al., Raffinot) sem reproduzi-la aqui. Vantagem de variância OOS é sobre risco, não retorno, e ignora custos de rebalanceamento. Pp. 235–245 não foram lidas em detalhe.
