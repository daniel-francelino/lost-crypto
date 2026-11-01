# Livro 3 · Capítulo 5 — Testes de hipóteses e intervalos de confiança

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 217–253 foi lido.

## 1. Resumo do capítulo (pp. 217–253)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Dois procedimentos de inferência: **testes de hipóteses** (existe efeito?) e **estimação** (qual sua magnitude? estimativa pontual e **intervalar**). Inferência informal favorece evidências confirmatórias, que são *necessárias, mas insuficientes* (afirmar o consequente); o teste se apoia em **negar o consequente**. | Por que “funcionou no backtest” não basta. | 217–219 |
| C2 | **Hipóteses**: `H_A`, retorno esperado da regra > 0 (em dados sem tendência); `H₀`, retorno esperado ≤ 0. São mutuamente exclusivas e exaustivas; testa-se `H₀`, reduzida à afirmação retorno = 0 (rejeitar zero contradiz todos os valores inferiores). Pressupõe-se `H₀` verdadeira por **ceticismo** (ônus da prova do proponente, como presunção de inocência) e **simplicidade** (Occam: menos parâmetros ajustam-se ao acaso com menor facilidade; polinômio de dez coeficientes ajusta dez pontos quaisquer). **Rejeitar `H₀` é decisão forte; mantê-la é fraco** (ausência de evidência não prova inutilidade). | Lógica do teste. | 220–227 |
| C3 | **Mecânica**: hipótese, estatística de teste (retorno médio da regra), distribuição amostral sob `H₀` (centrada em zero). **Valor-p** = probabilidade condicional sob `H₀` de observar estatística igual ou maior que a observada; fração da distribuição amostral nessa região. Escolher limite **antes** do teste. Escala: 0,10 possivelmente significativo; **0,05** significativo; 0,01 muito significativo; 0,001 altamente significativo. Valor-p **não** é a probabilidade de `H₀` ser verdadeira. | Quantificar o quanto o resultado é surpreendente. | 227–233 |
| C4 | **Erros**: tipo I (rejeitar `H₀` verdadeira e negociar regra inútil) versus tipo II (não detectar regra boa). Para um operador, **tipo I é pior** (perda de capital versus oportunidade perdida). | Custo de errar. | 233–234 |
| C5 | **Distribuições amostrais computacionais**. *Bootstrap*: testa `H₀: retorno esperado ≤ 0`; calcula retorno diário médio em dados sem tendência; **centraliza em zero** (subtrai a média); reamostra **com reposição N vezes** (N = tamanho original), em 5.000 repetições; valor-p é a fração das médias reamostradas ≥ média observada. *Permutação Monte Carlo (MCP, Masters)*: testa `H₀` de que resultados da regra estão pareados aleatoriamente às variações de mercado; mantém sequência de sinais e pareia, **sem reposição**, com variações diárias futuras sem tendência reordenadas; calcula médias dos produtos e repete 5.000 vezes. Valor-p é a fração ≥ observado. Testam hipóteses nulas ligeiramente diferentes e geralmente concordam em dados sem tendência. Segundo o autor (pp. 235–236), **MCP é de domínio público; variante bootstrap para regras mineradas (Reality Check de White) é patenteada**. | Construir distribuição nula. | 234–243 |
| C6 | **Exemplo** (regra TT-4-91, rompimento de canal de 91 dias no Dow Jones Transportation, negociação do S&P 500, nov. 1980–jun. 2005, 6.800 observações): +4,84% ao ano em dados sem tendência; bootstrap p = 0,0692 (“possivelmente significativo”); MCP quase igual. Valor-p pressupõe que foi a *única* regra testada. | Aplicação. | 240–243 |
| C7 | **Estimação**: média amostral é estimador não enviesado, consistente, eficiente e suficiente da média populacional (para populações simétricas; erro-padrão menor que o da mediana). **Intervalo de confiança** deriva da mesma distribuição amostral, centrado na média amostral; IC de 90% cobre o valor verdadeiro em cerca de 90% das amostras independentes; maior confiança → intervalo mais largo. **Percentis bootstrap**: ordenar médias reamostradas e remover `(100 − nível)/2 %` de cada extremidade. **MCP não gera IC**, pois testa conteúdo informativo, não um parâmetro. Exemplo: IC de 80% de TT-4-91 = +0,62% a +9,06%. | Magnitude do efeito. | 243–253 |
| C8 | Teste e intervalo podem discordar quando a distribuição amostral é assimétrica; o TCL torna a **média** uma boa estatística para amostras grandes; outras estatísticas (razões) podem precisar de métodos bootstrap pivotados. | Escolha da estatística. | 250–252 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| `H₀`, valor-p, rótulos de significância | ❌ | Nada em `analytics` ou na API de backtest. |
| Bootstrap/permutação | ❌ | Não há reamostragem em `api/src`. |
| Intervalos de confiança do retorno médio | ❌ | Não calculados. |
| Pré-requisitos disponíveis | ⚠️ | O motor retorna curva patrimonial e operações; estado comprado/neutro por barra existe (`quantity`), mas não é retornado em `BacktestOutcome` (`models.py`). Retornos por barra podem ser derivados da curva. `BacktestConfig` já tem `seed`. |
| Assimetria no custo dos erros | ✅ conceitualmente | Promoção exige dias em paper, limites e aprovações, favorecendo evitar erro tipo I; nada disso está ligado à evidência. |
| Licenciamento dos métodos | n/a | Ainda não há código. |

## 3. Oportunidades

### O1 — Teste de permutação Monte Carlo sobre posições por barra *(livro: C5, pp. 238–243 · comprado/neutro é adaptação nossa)*

* **Problema:** não é possível associar afirmação probabilística ao resultado.
* **Proposta:** função pura `permutation_test(position, bar_returns, n=5000, seed)`, mantendo a sequência original de posições por barra (1 no mercado, 0 fora; generalização nossa do ±1 do livro), pareando-a sem reposição com permutações dos retornos por barra sem tendência, calculando a média ponderada pela posição e retornando valor-p. Essa sequência é a saída da regra no vocabulário do livro. Retornar resumo da distribuição nula (média, quantis) para o gráfico.
* **Vantagem:** **não exige executar a estratégia novamente**; trabalha sobre vetores, com baixo custo e determinismo por semente. A hipótese nula mantém a mesma exposição, refletindo o benchmark ajustado à exposição do livro 3, cap. 1.
* **Benefício:** valor-p justificável por backtest e segmentos treino/teste; varreduras podem mostrar valor-p por célula (ver correção por multiplicidade no cap. 6).
* **Complexidade:** baixa a média: `BacktestOutcome` precisa carregar posição por barra; remover tendência subtraindo retorno médio amostral (livro 3, cap. 1); ordenar percentis; O(5.000 × barras) é aceitável.
* **Riscos:** (a) permutação destrói autocorrelação dos retornos, como pretende o livro, mas pode favorecer rompimentos em relação a uma hipótese nula com agrupamento de volatilidade; (b) hipótese nula com custos deve incluir custos do padrão de operações original (posições não mudam, portanto custos são iguais) e valor-p deve usar retorno líquido; (c) exemplos do livro usam posições ±1 e dados diários; períodos neutros e candles intradiários 24/7 mudam a estatística; (d) a dependência da posição em retornos passados é justamente o que se testa, mas longos períodos na mesma posição reduzem graus de liberdade efetivos; exibir número de sequências de posição junto ao valor-p.
* **Validação:** posições construídas com retornos futuros (trapaça) devem dar p≈0; série aleatória produz valores-p uniformes; conferir a fórmula de retorno esperado do livro 3, cap. 1 O1; mesma semente deve repetir o resultado.

### O2 — Valor-p bootstrap centralizado em zero e intervalo percentil da média *(livro: C5, C7, pp. 235–238, 248–250)*

Reamostrar com reposição N retornos por barra (ou, melhor para dependência, retornos por operação ou **blocos**) em 5.000 repetições: (a) centralizar em zero para valor-p; (b) não centralizar para intervalo percentil. Exibir ambos e tamanho da amostra. Reamostragem em blocos é adaptação nossa à dependência serial; o método do livro reamostra retornos diários individuais.

**Benefício:** intervalo sem pressupor normalidade, complementar a O1 (teste de conteúdo informativo versus estimação do tamanho). **Complexidade:** baixa a média. **Riscos:** bootstrap iid do livro subestima incerteza com autocorrelação; centralizar preserva assimetria/curtose, mas supõe amostra representativa; retornos por barra são esparsos (muitos zeros). **Validação:** dados sintéticos com média conhecida; cobertura simulada: cerca de 90% dos IC de 90% contêm a média verdadeira.

### O3 — Apresentar vocabulário de significância e ressalvas *(livro: C3, C4, pp. 231–234)*

Exibir valor-p, rótulo (possivelmente/significativo/muito/altamente significativo) e frase fixa: valor-p é probabilidade deste resultado **se a estratégia não tiver habilidade**, não probabilidade de ela ter habilidade. Indicar se houve 1 ou N testes (livro 3, cap. 6). **Complexidade:** muito baixa.

### O4 — Critério de evidência para promoção à operação real (erro tipo I é pior) *(livro: C4, p. 234 · adaptação)*

Ampliar verificações de prontidão (`bots/application/live.py`) com critério opcional explícito: valor-p de permutação do backtest abaixo de limite escolhido pelo operador **e** correção para número de configurações testadas (livro 3, cap. 6). Desligado por padrão. Motivação: o livro considera mais custoso adotar regra inútil do que perder uma boa oportunidade. **Complexidade:** baixa após O1 e cap. 6. **Risco:** falso sentimento de segurança após aprovação; manter dias em paper, limites e aprovações atuais.

### O5 — Licenciamento e escolha do método *(livro: C5, pp. 235–236)*

O autor afirma que a variante bootstrap para regras mineradas (Reality Check de White) é **patenteada** (Halbert White; software Quantmetrics) e que permutação Monte Carlo é de domínio público. Antes de implementar correção de seleção de dados (cap. 6), verificar status legal do algoritmo escolhido (tarefa de verificação do proprietário, não aconselhamento jurídico deste relatório) e preferir métodos com status claro. Bootstrap simples e testes de permutação são estatística padrão. **Complexidade:** nenhuma no código; requer decisão.

### Não aplicável

Propriedades didáticas de estimadores, analogia do tênis e experimentos com contas.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 teste de permutação | **alta** | – | – | baixa–média | posição por barra em `BacktestOutcome` |
| 2 | O3 vocabulário e ressalvas | média | – | – | muito baixa | O1 |
| 3 | O2 valor-p e IC bootstrap | alta | – | – | baixa–média | – |
| 4 | O5 verificação de licença | – | – | – | nenhuma | antes do cap. 6 |
| 5 | O4 critério de promoção | – | média | média | baixa | O1, cap. 6 |

## 5. Arquivos afetados

`backtesting/domain/models.py` (posições em `BacktestOutcome`), `backtesting/domain/engine.py` (produzi-las), novo `analytics/domain/inference.py` (permutação/bootstrap), `backtesting/application/service.py` e `router.py` (campos de resultado), `docs/openapi.json`, `bots/application/live.py` (O4), páginas de backtest/varredura e testes do app.

## 6. Plano incremental

1. Incluir posições por barra no resultado (aditivo; hashes e execuções armazenadas não mudam).
2. Funções puras de permutação/bootstrap com testes sintéticos.
3. Expor valor-p/intervalo como campos opcionais do resultado geral e de cada segmento.
4. Interface com distribuição, valor-p rotulado e texto O3.
5. Mais tarde, correção de multiplicidade (cap. 6) e critério opcional de promoção.

## 7. Critérios de aceitação e testes

* Estratégia com antecipação deliberada (posições derivadas de retornos futuros) obtém p próximo de 0; posição alternada aleatória produz p aproximadamente uniforme em várias sementes.
* Em simulação, o intervalo bootstrap cobre a média verdadeira aproximadamente na proporção nominal.
* Determinismo: mesma semente e entradas → valor-p idêntico.
* Execução de 5.000 permutações em casos típicos cabe no orçamento acordado; pode rodar assincronamente como outras tarefas.
* Nenhuma mudança na negociação ou resultados armazenados sem solicitação dos campos opcionais; Ruff, mypy e testes existentes passam.

## Ressalvas

Valores-p são condicionais a `H₀`, à estatística escolhida e a um único teste (p. 242). A regra do estudo foi “possivelmente significativa” com p = 0,069, portanto não significativa a 0,05, antes de considerar milhares de regras testadas (próximo capítulo). Significância em dados passados não implica lucro futuro.
