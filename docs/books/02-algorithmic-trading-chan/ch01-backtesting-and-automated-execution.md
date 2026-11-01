# Livro 2 · Capítulo 1 — Backtesting e execução automatizada

*Algorithmic Trading: Winning Strategies and Their Rationale*, Ernest P. Chan (Wiley, 2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

Nota de leitura: foram lidas as pp. 1–38. O levantamento de plataformas de software (pp. 25–36: Deltix, Apama, integrações com MATLAB, IDEs de código aberto, colocalização, multithreading e CEP) foi considerado apenas quanto aos princípios.

## 1. Resumo do capítulo (pp. 1–38)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Faça o backtest de cada estratégia por conta própria**: os resultados dependem dos detalhes de implementação (tipo de ordem, preço que a aciona); o mesmo programa deve ser usado na execução. Uma estratégia publicada oferece um período genuinamente fora da amostra **após a publicação**. Siga o método científico: hipótese → backtest → refinamento. | Afirmações difíceis de reproduzir ou sensíveis aos detalhes. | 1–3 |
| C2 | O **viés de antecipação** (*look-ahead bias*) é um erro de programação que só pode existir no backtest; se o backtest e a operação real usam o *mesmo programa* com dados diferentes, ele não ocorre. | Vazamento de informação futura. | 4 |
| C3 | **Viés de seleção de dados** (*data-snooping bias*): excesso de parâmetros livres. Detecte-o com dados fora da amostra; ajustar a estratégia após um resultado ruim fora da amostra transforma esses dados em dados de treino. Use **validação cruzada** (vários subconjuntos); prefira Sharpe alto e duração máxima de drawdown curta, pois essas características tendem a sobreviver à validação cruzada. Use poucos parâmetros **e poucas regras**; **modelos lineares são menos sujeitos à seleção de dados** que os não lineares (um modelo não linear tem uma aproximação linear; justifique por que ela não serve). A parcimônia de Occam também se aplica às distribuições: suponha normalidade, salvo forte motivo em contrário (argumento do autor). A combinação de fatores com pesos iguais (escores z ou postos com sinal) é citada como robusta (citação de Kahneman; a “fórmula mágica” de Greenblatt, 30,8% contra 12,4% de retorno anual entre 1988 e 2004, é um exemplo do autor). | Sobreajuste. | 4–7 |
| C4 | O **teste walk-forward** é a verificação final fora da amostra: negociação em paper ou, de preferência, negociação real com alavancagem mínima; **pela experiência do autor, a maioria dos traders ficaria satisfeita se o Sharpe real superasse metade do Sharpe do backtest**. | Validação final. | 7 |
| C5 | **Armadilhas nos dados**: desdobramentos e dividendos (ajustar o histórico e os dados em tempo real); viés de sobrevivência (afeta sobretudo a reversão à média comprada, menos o momentum; exemplo de comprar o maior perdedor); **preços primários e consolidados** (preços de leilão de abertura/fecho versus transações em outras bolsas; máximas e mínimas consolidadas são exageradas e podem inflar os resultados de reversão à média); **dependência da bolsa nas cotações cambiais** (usar dados da bolsa em que se negocia; os spreads variam); **restrições a vendas a descoberto** (ativos difíceis de tomar emprestados, proibições e regras de uptick); **contratos contínuos de futuros** (lacunas na rolagem criam P&L falso; ajustes retroativos por preço e por retorno não podem ser ambos corretos; preços negativos); **preço de liquidação versus último preço**; **preços assíncronos em spreads**. | Backtests inflados ou pouco realistas. | 7–16 |
| C6 | **Significância estatística por teste de hipóteses**: hipótese nula = retorno médio verdadeiro igual a zero; estatística de teste = retorno diário médio; valor-p. Três formas de construir a distribuição nula: (1) supor normalidade: estatística = `média/desvio-padrão × √n` (equivalente a Sharpe diário × √n), com valores críticos 1,282 / 1,645 / 2,326 / 3,091 para p = 0,10 / 0,05 / 0,01 / 0,001; (2) **Monte Carlo** sobre preços simulados com os quatro primeiros momentos da série real (no exemplo, 1.166 de 10.000 simulações tiveram resultado igual ou melhor, ou seja, confiança de apenas 88%); (3) **datas de entrada aleatórias**, mantendo o número de operações e a duração das posições (Lo et al.; no exemplo, 0 de 100.000 tiveram resultado igual ou melhor). Os métodos podem discordar porque cada um define aleatoriedade de forma diferente. Ressalva: valores-p indicam P(R | H0), não P(H0 | R). Mais operações completas implicam maior significância. | “Este backtest pode ser acaso?” | 15–22 |
| C7 | **Quando não fazer backtest** (sinais de alerta): retorno alto, mas Sharpe 0,3 e drawdown de dois anos; estratégia comprada que não supera comprar e manter pelo **índice de informação**; “comprar as ações mais baratas” sem dados livres de viés de sobrevivência; rede neural com cerca de 100 nós; backtests de alta frequência cujos resultados dependem da reação dos demais participantes. | Evitar esforço desperdiçado. | 22–24 |
| C8 | **O backtest prevê o futuro?** Ele pressupõe propriedades estatísticas constantes; mudanças de regime (decimalização em 2001, crise de 2008, Reg NMS em 2007, alterações na regra de uptick) podem tornar inúteis os dados anteriores; dados recentes também não oferecem garantia. | Estabilidade da vantagem estatística. | 24–25 |
| C9 | **Escolha da plataforma**: uma plataforma que usa o mesmo programa no backtest e na operação real evita erros de transcrição e viés de antecipação; processamento orientado a eventos (ticks) versus barras; a latência vem principalmente dos dados e da confirmação da corretora (confirmações de varejo podem levar segundos); colocalizar num servidor em nuvem pode sobretudo proteger contra falhas de energia e Internet, sem necessariamente reduzir a latência (verificar com ping); multithreading, CEP e feeds de notícias. | Operação do sistema. | 25–36 |
| C10 | Recapitulação dos pontos principais: o teste walk-forward supera outras defesas contra seleção de dados; prefira modelos simples; valide com o benchmark adequado. | – | 37–38 |

As observações sobre ações, futuros e moedas aplicam-se especificamente a esses mercados. As observações sobre criptoativos são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| C1 mesmo código de estratégia no backtest e na operação real | ✅ | Há uma classe `Strategy` por tipo, usada por `run_backtest` e pelo trader; a lógica de execução e stops é compartilhada (`execution/domain/fills.py`, `risk_management/domain/stops.py`). Os *loops* do motor são diferentes (`backtesting/domain/engine.py` e `trading/application/trader.py`), e o dimensionamento de risco existe apenas na operação real (livro 1, cap. 5). |
| C2 viés de antecipação | ✅ por projeto, ❌ sem teste | A estratégia vê apenas o candle fechado; a execução ocorre na abertura seguinte. Não há teste automatizado de truncamento (livro 1, cap. 3 O5). |
| C3 validação cruzada | ❌ | Existe apenas uma divisão fixa entre treino e teste (`segments.py`). |
| C3 simplicidade | ✅ | No máximo quatro parâmetros por estratégia. |
| C4 walk-forward/operação real com alavancagem mínima | ✅ parcialmente | A etapa paper é obrigatória (`live_min_paper_days`) e há limites para a operação real, mas não se compara o Sharpe real com o do backtest. |
| C5 consistência da bolsa | ✅ | Os candles vêm do mesmo adaptador da corretora usado para executar (`ExchangeRegistry.market_data(cfg.exchange`); os dados são armazenados por bolsa. |
| C5 sobrevivência | ❌ | Não há tratamento de ativos removidos da listagem (livro 1, cap. 3). |
| C5 desdobramentos/dividendos/futuros/vendas a descoberto | n/a | Cripto à vista, apenas posições compradas. |
| C5 preços consolidados versus primários | n/a | Uma única bolsa; não são usados índices agregados. |
| C6 testes de significância | ❌ | Não há valor-p, Monte Carlo, teste de entradas aleatórias nem teste de significância do Sharpe. |
| C6 número de operações completas | ✅ | `round_trips` é exposto, mas não está ligado à confiança estatística. |
| C7 triagem de sinais de alerta | ❌ | Não há alertas automáticos para Sharpe baixo com drawdown longo ou desempenho inferior a comprar e manter. Existe `buy_and_hold_return_pct`. |
| C8 mudanças de regime | ❌ | Não são monitoradas; a divisão cronológica treino/teste retém dados recentes e ajuda parcialmente. |
| C9 mesmo programa | ⚠️ | A estratégia é a mesma; a orquestração é diferente. |
| C9 resiliência/hospedagem | ⚠️ | Ver livro 1, cap. 4 (runbook de continuidade). |
| C9 latência | ✅ | As barras têm duração de 1 minuto ou mais; latência de segundos é irrelevante nesses horizontes. |

## 3. Oportunidades

### O1 — Significância estatística do backtest *(livro: C6, pp. 15–22)*

* **Problema:** o retorno positivo do backtest é apresentado sem indicar se pode ser acaso; buscas de parâmetros agravam o problema.
* **Proposta (em etapas):**
  1. *Estatística de teste gaussiana*: `Sharpe diário × √n` (n = número de observações de retorno), comparada aos valores críticos do livro; apresentar valor-p aproximado. É simples e tem forma fechada.
  2. *Teste de entradas aleatórias*: reposicionar aleatoriamente o mesmo número de entradas, com a mesma distribuição de duração das posições, na série de preços observada; informar a fração de simulações cujo retorno médio é igual ou superior ao observado. Requer gerador determinístico com semente (a configuração já contém `seed`).
  3. *Monte Carlo sobre preços simulados* (compatíveis com os quatro momentos): deixar para depois; exige um gerador de distribuições (sistema de Pearson) e muito processamento.
* **Benefício:** quantifica a possibilidade de acaso. O exemplo do próprio livro mostra que os testes discordam; por isso, suas definições devem ser apresentadas. **Complexidade:** baixa na etapa 1; média na etapa 2. **Riscos:** retornos de cripto têm autocorrelação e caudas pesadas, então a aproximação gaussiana pode ser otimista; muitos testes numa busca aumentam falsos positivos (testes múltiplos, tratados nos livros seguintes); valor-p não é a probabilidade de a estratégia funcionar (o livro ressalta isso, p. 22). **Validação:** séries sintéticas conhecidas, com e sem vantagem; reproduzir os valores críticos do livro; garantir determinismo com semente fixa.

### O2 — Estrutura de walk-forward e validação cruzada *(livro: C3, C4, pp. 4–7)*

* **Proposta:** substituir a divisão única por *k* intervalos cronológicos (para uma estratégia de tendência, escolher parâmetros na janela anterior e avaliar na seguinte) e apresentar a dispersão dos resultados entre os intervalos. A validação temporal não deve embaralhar os dados. Relaciona-se ao livro 1, cap. 3 O8 (backlog B-WALK-FORWARD) e ao livro 5 (validação cruzada com purga), que trata corretamente o vazamento entre intervalos; **não implementar antes da análise do livro 5**.
* **Complexidade:** alta.

### O3 — Sinalizadores de triagem dos resultados *(livro: C7, pp. 22–24)*

* **Proposta:** bloco de “sinais de alerta” em cada backtest: Sharpe abaixo de um limite com duração longa de drawdown; retorno inferior ao de comprar e manter (estilo índice de informação, usando o benchmark existente); poucas operações completas para sustentar significância; muitos parâmetros em relação ao tamanho da amostra (livro 1, cap. 3 O6). Exibir avisos, sem bloquear. **Complexidade:** baixa quando Sharpe e duração do drawdown estiverem disponíveis. **Validação:** testes unitários para cada alerta. Os limites dos exemplos do autor devem ser configuráveis.

### O4 — Monitor de Sharpe real versus backtest *(livro: C4, p. 7)*

* **Proposta:** para um bot com histórico suficiente em paper ou real, calcular o Sharpe realizado a partir das amostras de patrimônio e compará-lo com o Sharpe do backtest; exibir a razão e a observação de que, pela experiência do autor — não por uma norma —, um valor ≥ 0,5 é aceitável. **Complexidade:** baixa a média. **Riscos:** amostras reais curtas são ruidosas; exibir o tamanho da amostra. **Dependências:** métrica de Sharpe (livro 1, cap. 2 O1) e relatório de paridade (livro 1, cap. 5 O1).

### O5 — Registro transparente das avaliações fora da amostra *(livro: C1, C3, pp. 3–4 · adaptação)*

* **Problema:** alterar repetidamente os parâmetros após observar o segmento de teste transforma esse segmento em dados de treino (alerta central do livro).
* **Proposta:** registrar, em cada execução, quais segmentos o operador consultou ao escolher parâmetros e contar quantas execuções usam a mesma janela de dados; avisar quando o segmento de teste já tiver sido usado muitas vezes. Versão prática: mostrar junto ao resultado o número de execuções para o mesmo par, intervalo e janela. **Complexidade:** baixa. **Validação:** teste da API.

### O6 — Índice de informação com benchmark adequado *(livro: C7, pp. 22–23)*

* **Proposta:** para estratégias compradas, calcular os retornos excedentes em relação à estratégia de comprar e manter o mesmo par e apresentar seu índice de informação (a fórmula consta no livro 1, cap. 2). Já há suporte parcial por `buy_and_hold_return_pct`. **Complexidade:** baixa.

### Não aplicável ou adiado

Desdobramentos e dividendos, preços primários e consolidados, dependência da bolsa nas cotações cambiais, regras de venda a descoberto, contratos contínuos de futuros, preços de liquidação, escolha da plataforma (a plataforma já existe), CEP, feeds de notícias e multithreading. A colocalização para **resiliência** é abordada no livro 1, cap. 4.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O6 índice de informação | média | – | – | baixa | livro 1, cap. 2 O1 |
| 2 | O3 sinais de alerta | alta | média | – | baixa | Sharpe, duração do drawdown |
| 3 | O1 etapa 1: significância gaussiana | alta | – | – | baixa | Sharpe |
| 4 | O5 contador de reutilização do teste | média | – | – | baixa | – |
| 5 | O1 etapa 2: entradas aleatórias | alta | – | – | média | O1 etapa 1 |
| 6 | O4 monitor da operação real versus backtest | – | média | média | baixa–média | relatório de paridade |
| 7 | O2 walk-forward/validação cruzada | alta | – | – | alta | livro 5 |

## 5. Arquivos afetados

`analytics/domain/` (funções de significância e índice de informação), `backtesting/application/service.py` e `router.py` (campos aditivos de resultado e contadores de execuções), `backtesting/domain/` (simulação de entradas aleatórias com semente), testes em `api/tests/unit`, `docs/openapi.json` e página de detalhes do backtest no app.

## 6. Plano incremental

1. Implementar os pré-requisitos das métricas no livro 1, cap. 2 (Sharpe e duração do drawdown).
2. Adicionar índice de informação e significância gaussiana aos resultados.
3. Incluir o bloco de sinais de alerta.
4. Implementar teste de entradas aleatórias com semente.
5. Acrescentar contador de reutilização e monitor da operação real versus backtest.
6. Implementar walk-forward após analisar o livro 5.

## 7. Critérios de aceitação e testes

* Os valores críticos reproduzem a Tabela 1.1; uma série com vantagem inserida tem valor-p pequeno e uma série de puro ruído não.
* O teste de entradas aleatórias é determinístico para uma semente fixa e tem tempo de execução limitado.
* Execuções antigas, sem os novos campos, continuam sendo exibidas; Ruff, mypy e os testes existentes passam.
* O texto da interface deixa claro que valor-p não é garantia.

## Ressalvas

Todos os limites (exceto os valores críticos) são heurísticas práticas de Chan. Os exemplos de Monte Carlo e entradas aleatórias referem-se a uma estratégia de momentum em futuros e não são generalizáveis. A significância estatística do backtest não garante retornos futuros; mudanças de regime podem anulá-la (p. 24).
