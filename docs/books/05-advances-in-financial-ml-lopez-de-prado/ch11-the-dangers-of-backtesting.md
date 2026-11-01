# Livro 5 · Capítulo 11 — Os perigos do backtesting

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 151–158 foram lidas integralmente (incluindo algoritmo PBO/CSCV e exercícios). Bibliografia não lida.

**Relevância:** capítulo mais diretamente aplicável aos módulos de backtest/varredura: **registrar todas as tentativas**, **deflacionar** resultados pelo total de tentativas e estimar **probabilidade de sobreajuste de backtest (PBO)** a partir de matriz de séries P/L. A plataforma já gera matriz desse tipo ao executar varreduras.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | “Pesquisar e fazer backtest é como beber e dirigir.” A maioria dos backtests publicados tem falhas de viés de seleção em testes múltiplos. Backtest é **hipótese, não experimento**: “não prova nada” e “não garante nada, nem atingir aquela razão Sharpe se pudéssemos voltar no tempo”; sorteios aleatórios seriam diferentes. Serve como **verificação de plausibilidade** de tamanho de aposta, giro, resiliência a custos e comportamento em cenários. | O que é um backtest. | 151–152 |
| C2 | **Sete pecados** (Luo et al., Deutsche Bank, 2014): viés de sobrevivência; **look-ahead** (timestamps, datas de divulgação, backfill); narrativa (história posterior para padrão aleatório); **data snooping** (treino no conjunto de teste); **custos de transação** (só operar revela custo real); **outliers** (estratégias apoiadas em poucos eventos extremos); venda a descoberto (disponibilidade/custo de empréstimo). Outros erros: cálculo de desempenho não padronizado (cap. 14), riscos ocultos ignorados, olhar apenas retornos, confundir correlação e causalidade, **período não representativo**, não esperar o inesperado, **ignorar limites de stop/margem**, ignorar custos de funding, esquecer fatores práticos. | Lista de erros. | 152 |
| C3 | **Mesmo backtest impecável provavelmente está errado**: tornar-se especialista exige dezenas de milhares de backtests; resultado bom pode ser acaso de testes múltiplos; “quanto melhor você fica, mais prováveis se tornam falsas descobertas”. | Testes múltiplos mesmo com mecânica correta. | 152–153 |
| C4 | **Backtesting não é ferramenta de pesquisa**: importância de atributos (cap. 8) é derivada a priori e explica padrões; backtests pouco revelam por que estratégia ganhou. Centenas de “alphas” publicados são “bilhetes de loteria vencedores da última rodada”, sem relatar milhões de simulações anteriores. **Objetivo do backtest é descartar modelos ruins, não melhorá-los**; ajustar modelo após resultados é “perda de tempo e perigoso”; só testar quando modelo estiver totalmente especificado; se falhar, recomeçar. | Papel dos backtests. | 153 |
| C5 | **Sobreajuste de backtest = viés de seleção em vários backtests.** Recomendações: (1) desenvolver modelos para **classes/universos inteiros de ativos**, não títulos específicos (erro encontrado em um só ativo provavelmente é falsa descoberta); (2) **bagging** (se desempenho se deteriorar, havia ajuste a poucas observações/outliers); (3) não testar antes de terminar pesquisa; (4) **registrar todos os backtests do conjunto de dados** para estimar PBO e **deflacionar Sharpe pelo número de tentativas**; (5) **simular cenários, não história** (história é um único caminho aleatório; milhares de “e se” são mais difíceis de sobreajustar); (6) se backtest falhar, recomeçar (Segunda Lei). | Contramedidas práticas. | 153–154 |
| C6 | **Seleção de estratégia**: CV k-fold vaza informação (cap. 7); walk-forward do scikit-learn avança o teste, mas com dependência serial longa, testar logo após treino pode não eliminar vazamento. “Há um único caminho de teste que pode ser repetido até surgir um falso positivo”; é necessária aleatorização. | Limites de walk-forward. | 155 |
| C7 | **Probabilidade de sobreajuste (PBO) por validação cruzada simétrica combinatória (CSCV)**: reunir matriz `T × N` de séries P/L para N configurações (linhas síncronas); dividir linhas em S blocos contíguos iguais (S par). Para cada combinação de S/2 blocos de treino J (complemento J̄ para teste; S=16 dá 12.780 combinações): calcular métrica R em cada tentativa sobre J, escolher melhor `n*`, calcular **posição relativa `ω_c`** entre tentativas em J̄ e logit `λ_c = ln(ω_c/(1 − ω_c))`; PBO é proporção de combinações com `λ ≤ 0` (melhor tentativa dentro da amostra tem desempenho igual/abaixo da mediana fora). Exemplo: melhor SR dentro versus fora mostra deterioração `SR_OOS = 0.87 + 0.75·SR_IS`, R² ajustado 0,17, `Prob[SR_OOS < 0] = 0.74`, **PBO = 0.74**. Blocos preservam ordem temporal; aleatorização ocorre em subconjuntos fracamente dependentes. | Probabilidade quantitativa de sobreajuste derivada da própria varredura. | 155–157 |
| C8 | Exercícios: dados ajustados sazonalmente associados ao mês errado (look-ahead); sinais de fechamento executados no próprio fechamento (look-ahead); correlações espúrias; “efeito de setembro” (data snooping/narrativa); desempenho por ranking P/E (sobrevivência/look-ahead). | Identificar o erro. | 158 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Execução na barra seguinte (sem sinal e preenchimento no mesmo fechamento) | ✅ | Motor executa na abertura do candle seguinte (`engine.py`); evita exercício 11.2. |
| Custos sempre aplicados | ✅ | `fee_rate`, `slippage_bps`. |
| Viés de sobrevivência | ⚠️ | Escolher hoje os pares/tokens principais inclui só sobreviventes (tokens removidos/colapsados ausentes); plataforma negocia pares selecionados pelo usuário, em geral principais. |
| Contagem de testes múltiplos | ❌ | Sem contador, Sharpe deflacionado ou PBO. |
| Saídas da varredura como matriz de tentativas | ⚠️ | Resultados por configuração existem; séries P/L por período (patrimônio/retornos) de cada backtest talvez existam — verificar persistência de curva de patrimônio por execução. PBO exige séries síncronas para todas configurações. |
| Simulação de cenários (em vez de um caminho histórico) | ❌ | Um único caminho histórico; sem dados sintéticos/reamostrados (caps. 12–13). |
| Backtest como descarte, não otimizador | ❌ | Interface incentiva escolha do “melhor resultado”; sem avaliação bloqueada. |
| Dependência de outliers | ❌ | Ver livro 4, cap. 21 O1/O5 (N melhores operações, choques). |
| Chamadas de margem/stop-out | n/a | Spot comprado, sem alavancagem. |
| Representatividade do período | ❌ | Sem classificação de regimes nem declaração de cobertura (fração de alta/baixa/lateral). |

## 3. Oportunidades

### O1 — Registro de tentativas: guardar todos os backtests e membros de varredura por conjunto e família *(livro: C5 item 4, p. 154)*

Mesma proposta do livro 5, cap. 1 O3 e cap. 8 O1, e livro 4, cap. 21 O2. Criar tabela de primeira classe (`trials`: hash/ativo/timeframe/faixa do conjunto, família, parâmetros, métricas, `created_at`, flag `research_or_evaluation`), preenchida automaticamente em cada backtest/varredura (inclusive descartes e falhas de qualidade). Denominador da deflação (O2/O3). **Complexidade:** baixa–média (migração + integração no serviço). **Riscos:** contar repetidamente parâmetros idênticos (deduplicar por hash de configuração, mas manter contagem bruta); conjuntos separados têm registros próprios (por projeto, tentativas do livro são por conjunto). **Validação:** cada execução cria uma entrada; varredura cria N; duplicatas contam uma vez em “tentativas efetivas”, mas entram na contagem bruta.

### O2 — Relatório PBO (CSCV) para cada varredura *(livro: C7, pp. 155–157)*

* **Proposta:** implementar CSCV como função pura sobre matriz `T × N` de retornos por período (retornos diários/timeframe da curva de patrimônio de cada configuração, alinhados; padrão S entre 8 e 16, S=16 para 12.780 combinações; amostrar combinações se houver demais). Produzir **distribuição de logits**, **PBO**, **regressão da deterioração de desempenho IS versus OOS** (inclinação, intercepto, R², probabilidade da métrica OOS do melhor IS ser negativa) e **posição da configuração selecionada**. Mostrar junto à varredura: “Probabilidade de sobreajuste do backtest: 74%”, com explicação/gráfico. Usar Sharpe, Sortino ou retorno líquido como estatística (deve ser computável em subconjuntos).
* **Motivo:** ferramenta do livro que transforma varredura existente (maior fonte de viés de seleção) em alerta quantitativo, sem novos dados. Responde qualitativamente à questão do cap. 21 do livro 4 (“melhor resultado é robusto?”).
* **Complexidade:** média (combinatória, implementação vetorizada, armazenar retornos por execução). **Riscos:** cada bloco (T/S) precisa de observações suficientes para métrica significativa; Sharpe em subamostras presume blocos aproximadamente IID; tentativas quase duplicadas (parâmetros vizinhos) são altamente correlacionadas e mudam interpretação (PBO baixo pode refletir platô amplo, coerente com robustez); não considera tentativas anteriores à varredura (registro as rastreia); estratégias de memória longa têm blocos sem operações. **Validação:** (a) estratégias de puro ruído em passeio aleatório dão PBO próximo/maior que 0,5; (b) vantagem real inserida dá PBO baixo; (c) invariância à permutação de colunas; (d) determinístico com conjunto fixo de combinações; (e) reproduz valores publicados em matriz manual pequena.

### O3 — Deflacionar resultado de destaque pelo total de tentativas (Sharpe deflacionado, cap. 14) *(livro: C5 item 4, p. 154)*

Exibir junto ao melhor resultado da varredura a *probabilidade de o Sharpe ser genuíno dado N tentativas* (Sharpe deflacionado, cap. 14 O1), usando contador do registro. Sem isso, “melhor entre 200” é apresentado como se fosse teste único. **Complexidade:** baixa após fórmulas do cap. 14.

### O4 — “Backtest serve para descartar”: separar fluxo do produto em Pesquisa exploratória e Avaliação bloqueada, executada uma vez *(livro: C4, C5, pp. 153–154)*

Mesma recomendação do cap. 1 O4, livro 3 cap. 6 O5 e livro 4 cap. 21 O3; justificativa: ajustar modelo após observar backtest é perigoso. Mudanças: marcar resultados exploratórios como “exploratório — não é evidência”, mostrar total de tentativas e exigir **avaliação** (configuração/conjunto de dados congelado, tentativa única) antes de promover bot a paper (gates do cap. 1 O1). **Complexidade:** média.

### O5 — Lista de plausibilidade do backtest na interface (sete pecados + cripto) *(livro: C2, p. 152)*

Checklist junto a cada resultado: look-ahead (execução na próxima abertura ✔), custos (✔ taxa/slippage e valores), sobrevivência (⚠ seleção de ativos), outliers (parcela das maiores operações, choques), representatividade do período (fração por regime; primeiras/últimas datas), liquidez (limite de volume), qualidade dos dados (relatório validador; livro 4 cap. 22 O1). Adaptação cripto nossa: indisponibilidade e remoções de corretoras (sobrevivência), desancoragem de stablecoin, custos de funding em perpétuos (não aplicável a spot), níveis de taxa maker/taker. **Complexidade:** baixa–média (agregados já propostos em outros itens).

### O6 — Verificações no universo: exigir resultado em mais de um ativo antes de considerar uma descoberta *(livro: C5 item 1, p. 154)*

Igual a livro 4, cap. 21 O10. Regra do livro: erro encontrado em um único título provavelmente é falsa descoberta. Ressalva: correlações cripto são altas, então passar em BTC e ETH é evidência mais fraca que em ativos não relacionados. **Complexidade:** média.

### O7 — Avaliação baseada em cenários, não em caminho único *(livro: C5 item 5, p. 154 → caps. 12–13)*

Detalhes nos caps. 12 e 13 (CV purgada combinatória, dados sintéticos). Placeholder para manter a cadeia: PBO (O2) recombina blocos históricos; cenários sintéticos (cap. 13) vão além.

### Não aplicável

Vendas a descoberto/custo de empréstimo (spot comprado); stop-out/chamada de margem; datas de divulgação fundamental (a menos que feed seja adicionado); sobrevivência de ações (adaptar à sobrevivência de tokens por O5).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Registro de tentativas O1 | muito alta | – | – | baixa–média | armazenamento de execuções |
| 2 | PBO via CSCV O2 | muito alta | – | – | média | séries de retorno por execução; O1 |
| 3 | Deflação O3 (exige cap. 14) | muito alta | – | – | baixa | O1, cap. 14 |
| 4 | Checklist O5 | alta | – | – | baixa–média | demais itens |
| 5 | Fluxo pesquisa versus avaliação O4 | alta | média | – | média | O1 |
| 6 | Checagem multiativo O6 | média | – | – | média | importação de dados |
| 7 | Cenários O7 | alta | – | – | alta | caps. 12–13 |

## 5. Arquivos afetados

`backtesting` (tabela de tentativas, hooks de serviço/varredura, persistência de retornos por execução), `analytics/domain` (função CSCV/PBO, regressão de deterioração), `docs/openapi.json`, página de resultados de varredura (cartão PBO, histograma logit, dispersão da deterioração), rótulos pesquisa/avaliação, testes.

## 6. Plano incremental

1. Registro de tentativas e contagens visíveis.
2. Persistir retornos por período dos membros da varredura (ou recalcular sob demanda com sementes guardadas).
3. Calculadora PBO e cartão na varredura.
4. Ligar ao Sharpe deflacionado (cap. 14) e gates de promoção (cap. 1 O1).

## 7. Critérios de aceitação e testes

* CSCV: numa matriz 8×4 manual, combinações, posições e logits coincidem com cálculo manual; matrizes só de ruído produzem PBO ≈ 0,5 em média entre sementes; matriz com coluna claramente superior dá PBO ≈ 0; determinístico; ordem das colunas irrelevante.
* Registro coincide com execuções realizadas; endpoints existentes mantidos, salvo campos adicionados; ruff, mypy e testes existentes aprovados.

## Ressalvas

Exemplo PBO (0,74) e regressão de deterioração ilustram o livro, não são validação exaustiva (artigo original apresenta experimentos). PBO mede tendência do melhor dentro da amostra a ter desempenho pior fora **no conjunto de tentativas fornecido**; não considera tentativas não registradas. Usa blocos em ordem, mas presume alguma estabilidade entre eles; com mudanças fortes de regime, PBO baixo pode refletir apenas domínio do mesmo regime. “Backtest não prova nada” é posição do autor; o livro ainda usa backtests nas métricas seguintes.
