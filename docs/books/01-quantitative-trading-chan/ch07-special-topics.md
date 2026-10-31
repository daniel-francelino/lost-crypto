# Livro 1 · Capítulo 7 — Tópicos especiais em trading quantitativo

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

Nota de leitura: as pp. 115–156 foram lidas por inteiro. As listagens em MATLAB (Exemplos 7.4, 7.6, 7.7) e o Exemplo 7.1 de ferramenta de fornecedor foram lidos pelas suas afirmações, não reproduzidos.

## 1. Resumo do capítulo (pp. 115–156)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Estratégias só lucram se os preços forem de **reversão à média ou de tendência**; senão andam ao acaso. Ambos podem valer em horizontes diferentes. O autor acha pouco úteis as teorias gerais de qualquer um dos dois e diz que normalmente é seguro assumir reversão à média, a menos que os lucros esperados tenham mudado (opinião dele, citando Khandani–Lo como modelo simples de reversão lucrativo antes dos custos). | Escolher o tipo de vantagem. | 116–117 |
| C2 | Backtests de reversão à média são **inflados por cotações ruins** (compra-se uma cotação baixa fictícia, a cotação correta seguinte vende com lucro) e por viés de sobrevivência. Os dados devem ser limpos antes de confiar neles. | Lucros falsos. | 117 |
| C3 | Fontes de momentum: difusão lenta de informação (por exemplo, deriva pós-resultados), execução incremental de uma ordem grande, comportamento de manada. As duas últimas têm **horizontes de tempo imprevisíveis**. | Quando existem tendências e por quanto tempo. | 117–119 |
| C4 | Efeitos da concorrência: a vantagem de reversão à média encolhe para zero e sinais posteriores refletem mais frequentemente mudanças reais de valor; o **horizonte do momentum encurta** (uma posse de uma semana pode virar um dia, depois deixar de ser lucrativa). | Decaimento da vantagem. | 119, 140 |
| C5 | **Mudança de regime**: alta/baixa, volatilidade, reversão à média/tendência. Regimes de volatilidade se prestam à econometria clássica (GARCH), mas ajudam traders de opções, não de ações. Modelos de Markov ocultos assumem **probabilidades de transição constantes** e são ditos geralmente inúteis para trading; modelos de "ponto de virada" são uma abordagem de mineração de dados. Exemplo 7.1 (um perceptron numa ação de corretora): 37,93% bruto em **seis meses**, 89 operações, contra 15,77% de buy-and-hold; o próprio autor observa o período curto e que a janela de otimização não era totalmente fora da amostra. | Detectar quando as regras mudam. | 119–126 |
| C6 | **Estacionariedade/cointegração**: uma série estacionária é candidata a reversão à média; dois preços não estacionários podem combinar-se num spread estacionário (razão de hedge por regressão; testar com ADF de cointegração). **Cointegração ≠ correlação**; KO/PEP são correlacionadas (0,4849) mas não cointegradas. A estacionariedade só garante lucro enquanto persiste; séries não estacionárias ainda podem ter reversão de curto prazo. Os exemplos exigem **venda a descoberto**. | Lógica de pairs trading. | 126–133 |
| C7 | **Modelos de fatores** `R = Xb + u` (exposições, retornos de fatores, retornos específicos); três fatores de Fama–French; PCA como modelo de fatores só a partir de retornos; funciona só se os retornos dos fatores tiverem momentum; a estratégia PCA do autor em small caps perdeu dinheiro; modelos de fatores fundamentalistas sofrem drawdowns longos quando as preferências dos investidores mudam. | Explicar/prever retornos de corte transversal. | 133–139 |
| C8 | **Estratégias de saída**: período de posse fixo, preço-alvo, último sinal de entrada, preço de stop. Para reversão à média, estimar o período de posse de forma robusta pelo modelo de **Ornstein–Uhlenbeck**: regredir `dz` sobre `z`, **meia-vida = ln(2)/θ** (GLD/GDX ≈ 10 dias); sair na média ou após a meia-vida. Para momentum, o período de posse tirado de poucas operações é sujeito a erro. **Sair num novo sinal de entrada oposto funciona como um stop sem parâmetro extra**; um modelo de reversão não deve usar stop-loss (sai no pior momento), a menos que entre em regime de momentum. | Como sair das operações. | 140–143 |
| C9 | **Sazonalidade**: efeitos de calendário em ações enfraqueceram (testes dele do efeito janeiro e de um efeito ano contra ano, Exemplos 7.6–7.7); a sazonalidade de futuros de commodities persistiu porque se apoia em demanda real, mas ocorre uma vez por ano, então o snooping é difícil de descartar: variar as datas e exigir lógica econômica. | Estratégias de calendário. | 143–151 |
| C10 | **Alta frequência**: mais apostas por dia → Sharpe maior (lei dos grandes números) → mais alavancagem; o risco é mais fácil de gerir (desalavancar rápido); exige dados de bid/ask/livro, modelagem cuidadosa de custos e execução rápida; muitas vezes só o teste em tempo real é conclusivo. | Por que estratégias de curto horizonte pontuam alto. | 151–153 |
| C11 | **Alta alavancagem vs. beta alto**: o crescimento depende de Sharpe², então preferir uma carteira de beta baixo alavancada (ressalva: hipótese gaussiana, caudas gordas). | Como elevar retornos. | 153–154 |

A maioria dos exemplos são pares de ações, ETFs, futuros de commodities e venda a descoberto. As observações sobre cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Catálogo de estratégias vs. C1 | ⚠️ só tendência | Ambas as estratégias são de tendência/rompimento, long-only (`ema_crossover`, `donchian_breakout`). Não há estratégia de reversão à média; nenhuma usa regimes de volatilidade. |
| C2 cotações ruins | ⚠️ | Apenas o filtro de entrada `max_candle_range_pct` no módulo de risco; sem limpeza de dados (ver capítulo 3 O3). Relevante para qualquer estratégia futura de reversão à média. |
| C5 detecção de regime | ❌ | Nenhuma medida de regime de qualquer tipo. |
| C6 pares/cointegração | ❌ e **inviável como está** | Exige venda a descoberto ou uma perna de hedge; o sistema é spot long-only, um ativo por bot. |
| C7 modelos de fatores | ❌ | Bots de ativo único; sem universo de corte transversal. |
| C8 saída por sinal oposto | ✅ | Ambas as estratégias saem no sinal oposto (cruzamento de EMA de volta; fechamento abaixo da mínima mais baixa de `exit_period`); o livro chama isso de o stop com princípios para modelos de momentum. |
| C8 stop/alvo opcional | ✅ | Parâmetros `stop_loss_pct`/`take_profit_pct` em ambas as estratégias, mais o dimensionamento do módulo de risco a partir do stop. |
| C8 período de posse fixo / stop por tempo | ❌ | Sem saída baseada em tempo (busquei `max_hold|holding` em `strategies/domain`: nada). |
| C8 estimativa de meia-vida | ❌ | Não se aplica até existir uma estratégia de reversão à média. |
| C9 sazonalidade | ❌ | Nenhuma; atributos de calendário não estão disponíveis às estratégias. |
| C10 alta frequência | ❌ | O menor timeframe é de candles de 1 minuto; sem dados de livro/bid-ask; o modelo de fill usa a abertura do candle. Não serve para HFT. |
| C11 alavancagem vs. beta | n/a | Sem alavancagem. |

## 3. Oportunidades

### O1 — Adicionar uma família de estratégias de reversão à média *(livro: C1, C8, pp. 116–117, 140–143 · a aplicabilidade a cripto é adaptação)*
* **Problema:** o catálogo cobre apenas mercados em tendência; o livro diz que a reversão à média é o regime mais prevalente em ações. Se isso vale para cripto **não é estabelecido pelo livro**; precisa ser testado nos nossos dados.
* **Proposta:** uma estratégia long-only de reversão à média (por exemplo um z-score do preço contra uma média móvel, entrando quando muito abaixo e saindo na média ou após um limite de posse), implementada exatamente como as outras (uma classe, registrada no catálogo, parâmetros validados).
* **Benefício:** diversifica o tipo de vantagem; permite uso significativo das regras de saída do livro. **Complexidade:** média.
* **Riscos:** alta exposição aos erros de dados de C2 e a "pegar facas caindo" em crashes de cripto; um stop-loss é errado para esta família (C8), mas ainda é preciso um teto rígido de risco. O spot long-only perde metade da lógica do livro (o lado vendido).
* **Validação:** backtest com e sem custos; teste de truncamento (capítulo 3 O5); resultados no segmento de teste; sensibilidade do limiar de entrada.

### O2 — Saída por tempo (limite de período de posse) *(livro: C8, p. 140)*
* **Proposta:** `max_holding_candles` opcional em estratégias/bots que sai após N candles; para estratégias do tipo momentum escolher N por backtests ciente dos avisos do livro sobre erro e decaimento; para reversão à média usar a meia-vida (O3). **Complexidade:** baixa. **Risco:** mais um parâmetro (orçamento de snooping, capítulo 3 O6). **Validação:** teste do motor de que uma posição é fechada no candle certo.

### O3 — Meia-vida da reversão à média como ferramenta de análise *(livro: C8, pp. 140–142)*
* **Proposta:** um endpoint/função de pesquisa que ajusta `dz = θ(z − μ)dt + ruído` por regressão sobre uma série de preço ou spread e devolve `meia-vida = ln(2)/θ`, para orientar períodos de posse e escolhas de lookback. Só tem sentido se θ for negativo e significativo; devolver `None` caso contrário. **Complexidade:** baixa–média (OLS em `Decimal` ou uma fronteira float documentada, ver regras de dinheiro). **Risco:** preços de cripto raramente são estacionários; uma meia-vida espúria de uma série com tendência engana. **Validação:** série sintética de Ornstein–Uhlenbeck com θ conhecido; um passeio aleatório não deve produzir resultado.

### O4 — Indicador de regime de volatilidade (simples, descritivo) *(livro: C5, pp. 119–120 · adaptação)*
* **Proposta:** reportar o percentil da volatilidade realizada e sinalizadores de tendência/lateralidade por segmento de backtest para que os resultados possam ser lidos por regime; **não** operar com previsões de regime ainda (o próprio livro é cético quanto a HMMs e o exemplo dele é um teste de seis meses). **Complexidade:** baixa. **Validação:** série sintética com um degrau de volatilidade.

### O5 — Limpeza de dados antes do trabalho de reversão à média *(livro: C2, p. 117)*
Dependência de O1: implementar antes o capítulo 3 O3 (integridade dos candles e relatório de outliers).

### O6 — Sazonalidade / atributos de calendário *(livro: C9, pp. 143–151 · baixa prioridade)*
Cripto tem padrões de dia da semana e de horário de funding que o livro não discute; a única lição do livro é a disciplina: lógica econômica, variar as datas e esperar decaimento. Adiar até as métricas centrais existirem.

### Não recomendado agora
* **Pares/cointegração, modelos de fatores, PCA** (C6, C7): exigem venda a descoberto e um universo multiativo; revisitar só se futuros/margem ou um motor de carteira multiativo forem introduzidos.
* **Previsão de regime por HMM ou perceptron** (C5): a evidência do próprio livro é um exemplo de seis meses, bruto de custos, de uma ferramenta de fornecedor.
* **Alta frequência** (C10): exige dados de livro de ordens e execução de baixa latência.
* **Alavancagem vs. beta** (C11): sem alavancagem.

## 4. Prioridade

| # | Item | Qualidade do backtest | Confiabilidade | Gestão de risco | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O5 limpeza de dados | alta | alta | – | baixa–média | capítulo 3 O3 |
| 2 | O2 saída por tempo | baixa | – | média | baixa | – |
| 3 | O3 ferramenta de meia-vida | média | – | – | baixa–média | – |
| 4 | O4 descritores de regime | média | – | – | baixa | métricas do capítulo 2 |
| 5 | O1 estratégia de reversão à média | média | – | média | média | O5, capítulo 3 O5/O7 |
| 6 | O6 sazonalidade | baixa | – | – | baixa | – |

## 5. Arquivos afetados
`strategies/domain/` (novo arquivo de estratégia, entrada no registro, parâmetro opcional de saída em `base.py`), `strategies/catalog.py`, `backtesting/domain/engine.py` (saída por tempo), `analytics/domain/` (meia-vida, regime de volatilidade), formulários de estratégia do app (`lib/shared/strategies/params.ts`), `check:consistency`, testes.

## 6. Plano incremental
1. Primeiro a integridade dos dados (capítulo 3 O3).
2. Parâmetro de saída por tempo + testes.
3. Ferramentas de análise: meia-vida e descritores de regime.
4. Estratégia de reversão à média, condicionada ao teste de truncamento, à contagem de tentativas e à sensibilidade a custos dos capítulos anteriores.

## 7. Critérios de aceite e testes
* Qualquer estratégia nova passa no teste de truncamento e tem validação de parâmetros como as existentes.
* A meia-vida devolve o valor conhecido numa série sintética e `None` num passeio aleatório.
* A saída por tempo fecha no candle especificado e é coberta por testes do motor.
* Nenhuma mudança no comportamento das estratégias existentes; ruff, mypy, todos os testes verdes.

## Ressalvas
Toda cifra de desempenho neste capítulo é um exemplo de ações ou futuros da era de 2008, na maioria brutos de custos e vários com viés de sobrevivência que o próprio autor declara. A afirmação de que a reversão à média é mais prevalente que o momentum é a visão do autor para ações e **não deve ser assumida para cripto**. Nada aqui é evidência de lucratividade futura.
