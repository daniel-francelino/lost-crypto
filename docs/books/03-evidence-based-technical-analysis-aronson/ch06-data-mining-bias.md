# Livro 3 · Capítulo 6 — Viés de seleção de dados: o ouro de tolo da análise técnica objetiva

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 255–293 e 318–330 foram lidas na íntegra. Os resultados da simulação de regras artificiais (pp. 294–317; curvas de viés por fator) foram lidos somente pelo resumo das pp. 318–320, que reapresenta as conclusões; os gráficos individuais não foram examinados. Este é o capítulo mais relevante do livro para o recurso de varredura.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Seleção de dados é comparação múltipla**: definir problema, universo de regras candidatas e métrica; escolher o melhor resultado observado. A regra escolhida tende a ser a melhor no futuro (White demonstrou isso quando a amostra cresce), **mas seu desempenho observado é uma estimativa enviesada para cima do desempenho esperado**. Anedotas (macacos, códigos bíblicos, manteiga de Bangladesh com correlação 0,70 em centenas de séries) ilustram como eventos raros parecem prováveis depois de observados. | Por que o vencedor decepciona. | 255–264, 281–282 |
| C2 | **Definições**: viés de seleção = diferença esperada entre desempenho observado e esperado da melhor regra; universo de regras e seu tamanho; dentro/fora da amostra. Tipos de busca: **otimização de parâmetros** (mais restrita), **busca de regras** (formas diferentes), **indução de regras** (complexidade variável; aprendizado de máquina). Todas sofrem viés. | Escopo do problema. | 255–256, 264–267 |
| C3 | **Backtest de regra única**: média observada é estimativa *não enviesada*. **Seleção de dados**: desempenho observado serve para selecionar; usá-lo também como estimativa é o “erro do minerador de dados”. Piora fora da amostra decorre em grande parte da regressão de uma escolha sortuda à média, não necessariamente de mudança de mercado. | Dois usos distintos do mesmo número. | 268–272, 262–264 |
| C4 | **Média versus máximo**: pesquisador observa a *maior média entre N médias*; hipótese nula correta é a distribuição do máximo entre N, centrada acima de zero (para 50 regras inúteis, distribuição de máximas médias se centra em +33%; resultado observado +37% tem p≈0,45, não <0,05). | Uso da distribuição amostral errada. | 275–278 |
| C5 | **Duas causas do viés**: aleatoriedade e necessidade de selecionar. **Quanto maior a sorte em relação ao mérito (situação comum nos mercados), maior o viés.** | Por que mercados são o pior caso. | 278–284 |
| C6 | **Cinco fatores determinam o viés** da média de retornos: (1) **número de regras testadas** (viés cresce com log de N); (2) **número de observações** (mais observações reduzem viés); (3) **correlação entre retornos das regras** (mais correlação reduz viés, porque diminui o número efetivo); (4) **valores extremos positivos** (aumentam viés, efeito diluído por mais observações); (5) **variação do mérito verdadeiro entre regras** (mérito semelhante aumenta viés). Experimentos concordam que seleção funciona com amostra grande e falha com amostra pequena. Essas relações referem-se à média; outras métricas (Sharpe) podem se comportar de outro modo. | Prever a magnitude do viés. | 287–291, 318–320 |
| C7 | **Soluções**: (a) **teste fora da amostra** (não enviesado, mas dados perdem seu caráter “virgem” depois de usados; reduz dados para pesquisa; partição pode ser arbitrária. Esquemas: divisão inicial/final, tabuleiro, **walk-forward** com janelas móveis e segmentos de teste sem sobreposição, produzindo estimativas independentes e intervalo de confiança); (b) **correção Markowitz–Xu** (reduzir desempenho máximo em direção à média de todas as regras: `H' = R + B(H − R)`, requer retornos por intervalo de todas; “pode funcionar surpreendentemente bem, mas também falhar muito”; apenas orientação aproximada); (c) **aleatorização** que testa o melhor de N. | Corrigir o viés. | 320–324 |
| C8 | **Reality Check de White (bootstrap)**: conservar retornos por intervalo de todas as regras; reamostrar datas com reposição (mesma quantidade da amostra e mesmas datas em todas as regras); subtrair média própria de cada regra (centralizar em zero); tomar **maior média** por reamostragem; repetir ≥500 vezes; valor-p = fração dos máximos ≥ melhor observado. **Patenteado** (Halbert White; software Quantmetrics). **Permutação Monte Carlo (MC, Masters)**: manter sequência de saída de cada regra e pareá-la com as *mesmas variações de mercado embaralhadas* para todas (preserva correlação entre regras); tomar maior média e repetir. Não precisa centralizar em zero, não produz intervalos de confiança; versão aperfeiçoada (Romano e Wolf) será de domínio público, segundo o autor. Ambos perdem poder se o universo inclui regras **piores que inúteis** (Hansen), como regras inversas. | Teste correto do melhor entre N. | 324–330 |
| C9 | Requisito prático: **guardar retornos (ou saídas) por intervalo de cada regra testada**; “poucos mineradores de dados guardam essa informação”. | Dados necessários. | 327 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Existe universo de regras | ✅ | Varreduras enfileiram um backtest por combinação de parâmetros sobre os mesmos candles (`BacktestService.create_sweep`), até `MAX_SWEEP_RUNS`; grades de parâmetros são explícitas. |
| Seleção pelo melhor resultado observado | ✅ sem controle | API/interface lista métricas; operador escolhe o melhor. Nada corrige o viés ou o explica. |
| Retenção de retornos/posições por barra | ⚠️ | Cada execução armazena `equity_curve` e `fills`, permitindo recalcular retornos por barra; posições não são armazenadas como série, mas deriváveis das operações. Combinações ignoradas/inválidas ficam em `skipped`. |
| Tamanho acumulado do universo de pesquisa | ❌ | Não se acompanha entre varreduras, execuções manuais, estratégias ou pares. N verdadeiro supera qualquer varredura isolada. |
| Correlação entre regras/N efetivo | ❌ | Não calculados. |
| Fora da amostra | ⚠️ | Uma divisão cronológica por execução; todas as combinações de uma varredura podem ser avaliadas no mesmo teste, **reutilizando-o** em cada seleção e perdendo seu caráter “virgem”. |
| Walk-forward com testes independentes | ❌ | Não existe. |
| Correção Markowitz–Xu/aleatorização | ❌ | Nenhuma. |
| Número de parâmetros por estratégia | ✅ baixo | 2–4 parâmetros cada. |

## 3. Oportunidades

### O1 — Teste de permutação Monte Carlo do melhor entre N para varreduras *(livro: C8, pp. 327–330; baseia-se no livro 3, cap. 5 O1)*

* **Problema:** melhor configuração da varredura é mostrada com resultado bruto, que o livro considera enviesado para cima; seu valor-p de teste único é inválido (p≈0,45 em vez de <0,05 no exemplo de 50 regras).
* **Proposta:** numa varredura concluída, obter a série de **posições por barra de cada execução**, alinhada nos mesmos candles; gerar `M` permutações aleatórias dos retornos por barra sem tendência, **usando a mesma permutação em todas as execuções** (para preservar correlações); calcular o retorno médio de cada execução sob esse pareamento, registrar o **máximo** entre elas e calcular valor-p do melhor observado contra essa distribuição. Acrescentar mediana e percentil 95 da distribuição nula para mostrar “quanto renderia normalmente a melhor entre N regras inúteis”.
* **Benefício:** resposta justificável a “o vencedor supera o acaso?” e desincentivo a escolher o topo da grade; não exige reexecutar estratégias.
* **Complexidade:** média: depende de armazenar/derivar posições por barra, rotina numérica em lote e tarefa assíncrona para varreduras grandes.
* **Riscos:** (a) como no cap. 5 O1, permutar retornos destrói agrupamento de volatilidade e autocorrelação; (b) o livro informa redução de **poder** se o universo contiver regras piores que inúteis (regras inversas; para nós, combinações claramente ruins): considerar restringir universo às opções plausíveis definidas antes (O2), em vez de acrescentar opções irrelevantes; (c) corrige uma varredura, não todo o histórico de tentativas (O2); (d) M=500–5.000 permutações dá resolução de 1/M; (e) versão aprimorada Romano–Wolf é descrita pelo autor como disponível no site evidencebasedta.com, não no livro; versão MC básica será a referência.
* **Situação do método:** autor chama MC de **domínio público** e Reality Check de White de **patenteado**. Implementar permutação; não implementar WRC sem verificação jurídica pelo proprietário.
* **Validação:** varredura de regras aleatórias dá p aproximadamente uniforme; detectar uma regra realmente lucrativa inserida entre ruído; N=1 reduz ao teste individual do cap. 5; pareamentos idênticos entre execuções (execuções duplicadas correlacionadas não devem inflar o máximo).

### O2 — Contabilizar o universo: contar cada configuração já testada *(livro: C1, C4, C6, pp. 255–256, 275–278, 287–288)*

* **Problema:** N multiplica o viés; N oculto (varreduras anteriores, execuções manuais, outras estratégias, pares e intervalos) é forma comum de ilusão.
* **Proposta:** registrar cada configuração de backtest/varredura num **universo de pesquisa**, indexado por (corretora, símbolo, intervalo, janela de dados, família de estratégia), e mostrar a contagem cumulativa de configurações distintas testadas sobre os mesmos dados junto a cada resultado, usando N da varredura como limite inferior para O1. Amplia livro 2, cap. 1 O5 e livro 1, cap. 3 O7. Permitir ao operador definir universo explicitamente (estudo nomeado) antes da execução, como pré-registro (livro 3, cap. 2 O3).
* **Complexidade:** baixa a média. **Risco:** contagem ainda pode ser manipulada apagando execuções; auditar exclusões. **Validação:** teste da API para garantir contagem monotônica.

### O3 — Deixar de apresentar métrica bruta do vencedor como estimativa *(livro: C3, pp. 270–272)*

Nas varreduras, rotular melhor resultado como “resultado selecionado (enviesado para cima)” e mostrar também (a) mediana da grade, (b) nulo de melhor entre N de O1, (c) resultado de teste **apenas para configuração selecionada**, marcado como consumido após consulta. **Complexidade:** muito baixa (texto e layout). Incluir explicação curta do viés.

### O4 — Número efetivo de regras independentes *(livro: C6 fator 3, pp. 288, 318 · cálculo é adaptação nossa)*

Calcular correlação par a par dos retornos por barra entre execuções e informar um **N efetivo** (por exemplo, a partir dos autovalores da matriz de correlação). Parâmetros vizinhos (EMA 9/21 versus 10/21) são correlacionados, então N efetivo pode ser muito menor que o tamanho da grade. O livro explica a direção (correlação reduz viés), mas não dá fórmula de N efetivo; a nossa é descritiva. **Complexidade:** baixa a média. **Validação:** duplicatas dão N efetivo ≈1; ruído independente, ≈N.

### O5 — Janelas walk-forward não sobrepostas e intervalo *(livro: C7, pp. 322–323)*

Já consta como B-WALK-FORWARD (livro 1, cap. 3 O8; livro 2, cap. 1 O2). Este capítulo especifica: janela móvel dividida em treino e teste; testes **não sobrepostos** entre intervalos para estimativas independentes; intervalo de confiança da dispersão dos resultados por intervalo; reconhecer que cada segmento reservado é consumido pela seleção. Combinar com O1 dentro de cada janela de treino. **Complexidade:** alta; planejar após O1–O3.

### O6 — Guardar dados por barra de cada execução da varredura *(livro: C9, p. 327)*

Pré-requisito de O1/O4: armazenar para cada execução vetor compacto por barra (posição e retorno líquido) ou garantir reconstrução determinística por candles e configuração (`seed` e hash já existem). Limitar armazenamento (vetores pequenos e/ou compactados). **Complexidade:** baixa a média.

### O7 — Contração Markowitz–Xu como orientação aproximada opcional *(livro: C7, pp. 323–324)*

O próprio livro considera o método aproximado e às vezes muito errado; não fornece fórmula do fator de contração (remete a De La Maza). Adiar; considerar só após obter a fórmula na fonte citada e validá-la em universos sintéticos. **Complexidade:** média; prioridade baixa.

### Não aplicável

Códigos bíblicos e anedotas; indução de regras e aprendizado de máquina (livro 5).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O3 rotular/explicar viés do vencedor | alta | – | – | muito baixa | – |
| 2 | O2 contabilizar universo | alta | – | – | baixa–média | – |
| 3 | O6 guardar dados por barra | – | – | média | baixa–média | – |
| 4 | O1 permutação MC do melhor entre N | **alta** | – | – | média | O6, livro 3, cap. 5 O1 |
| 5 | O4 N efetivo | média | – | – | baixa–média | O6 |
| 6 | O5 walk-forward | alta | – | – | alta | O1 |
| 7 | O7 Markowitz–Xu | baixa | – | – | média | fórmula da fonte |

## 5. Arquivos afetados

`backtesting/application/service.py` (pós-processamento de varredura), `backtesting/domain/` (permutação do melhor entre N e séries por barra), `backtesting/infrastructure/orm.py` e repositório (registros de universo e vetores compactos), `analytics/domain/`, `docs/openapi.json`, páginas de varredura (`routes/backtests/sweeps/$sweepId`) e testes unitários/de integração em `api/tests`.

## 6. Plano incremental

1. Ajustar texto/layout e rotular vencedor como enviesado (O3).
2. Contabilizar universo (O2).
3. Guardar ou recalcular vetores por barra (O6).
4. Teste de permutação individual (livro 3, cap. 5 O1) e depois do melhor entre N (O1), com permutação compartilhada.
5. Indicador descritivo de N efetivo (O4).
6. Walk-forward após as etapas acima.

## 7. Critérios de aceitação e testes

* Em varredura de regras com posições aleatórias, valor-p do melhor entre N é aproximadamente uniforme; com efeito verdadeiro inserido, ele é detectado.
* A mesma permutação é usada para todas as regras (assertiva em teste unitário).
* Melhor retorno observado nunca aparece sem referência de melhor entre N e o valor de N.
* Nenhuma mudança na negociação; execuções e API existentes continuam compatíveis; Ruff, mypy e testes passam.
* Status de licença do método usado é registrado em `docs/` antes da publicação.

## Ressalvas

Experimentos do capítulo usam regras artificiais em dados mensais do S&P 500 e estatística de retorno médio; dependência dos cinco fatores pode ser diferente para classificação por Sharpe ou drawdown. Aprovação no teste de melhor entre N é evidência sobre **esta amostra**, não promessa futura; também não informa o número desconhecido de tentativas fora do universo registrado.
