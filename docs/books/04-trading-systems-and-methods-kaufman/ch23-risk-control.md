# Livro 4 · Capítulo 23 — Controle de risco

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foram lidas as pp. 1027–1061 e 1070–1075 (sorte versus habilidade, preferência a risco, medidas de risco, VaR, alavancagem, volatilidade-alvo, dimensionamento de posições, stops e alvos, seleção de mercados por razão de eficiência, risco de ruína) e 1085–1093 (tendências do patrimônio, f ótimo, início da comparação esperado versus real). O conteúdo direcional/ADX/Commodity Selection Index (1062–1069), as seções sobre entrada, preço médio e capitalização de posições (1076–1084) e o final de “Comparando resultados esperados e reais” (1093–1098) foram vistos apenas pelos títulos e **não são resumidos**.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Confundir sorte com habilidade**: ganho inesperado provocado por choque é sorte; avaliar como a conta sobreviveria ao mesmo movimento na direção oposta. A LTCM racionalizou choques passados e fracassou no seguinte. A única forma de reduzir risco de choque é **ficar fora do mercado** (uma estratégia exposta 40% do tempo tem 60% de chance de evitar o choque) e **ganhar o máximo investindo o mínimo possível** (programa totalmente alavancado que rende 200% pode perder tudo após um choque; um desalavancado que rende 20% tem dez vezes mais chance de sobreviver). | Sobrevivência versus retorno. | 1027–1028 |
| C2 | **Preferência a risco e utilidade** (Bernoulli): investidores são diferentes; fronteira eficiente e ponto tangente do melhor retorno/risco. O ponto ótimo não serve a todos, pois risco absoluto ou retorno podem ser inaceitáveis. **Regras práticas**: arriscar uma pequena parte do capital por operação (nunca mais de 5%; em outra passagem, 3%); conhecer a saída de antemão; lucros grandes implicam risco grande; sair rapidamente; **não atender chamadas de margem**; liquidar primeiro a pior posição; manter coerência com a filosofia (seguidor de tendência não pode realizar lucro sempre que aparece); adequar o perfil à preferência de risco; planejar contingências. | Princípios. | 1029–1032 |
| C3 | **Custo de liquidez**: `C = K × Q × V / (Lc × Lo)` (Ginter & Richie: custo cresce com tamanho da ordem e volatilidade, cai com volume); K é maior quando a ordem acompanha o movimento do preço. Custos de transação pesam mais em sistemas que operam muito, têm lucro médio pequeno e negociam a favor da tendência; escolher o método com menos operações nos mercados mais líquidos. | Modelo de slippage. | 1033–1034 |
| C4 | **Medir retorno e risco**: critérios — lucros maiores, ordem de lucros/perdas (consecutivos ou alternados), não penalizar ganhos grandes (não olhar somente drawdown), menor tempo de recuperação e menos tempo no mercado. **Sharpe/índice de informação** atendem apenas ao primeiro critério (não mostram sequência nem saltos); dados mensais parecem melhores que diários porque são suavizados. **Treynor** (beta). **Average Maximum Retracement** (Schwager): drawdown médio sem contar dias de novas máximas. **Drawdown máximo e Calmar** (`ARORt / MaxDD`): práticos, mas o futuro terá drawdowns maiores. **Sortino** (desvio de queda versus retorno mínimo aceitável). **Ulcer Index** `sqrt(Σ D_i² / n)`, em que D é a porcentagem abaixo da máxima anterior do patrimônio. **Probabilidade de drawdown (DP)** = desvio-padrão diário dos drawdowns (somente dias em drawdown) e **semivariância** em torno da linha de regressão; **razão de drawdown** `ARORt / DPt` (atende aos três critérios). O risco aumenta com amostra pequena, poucos recuos históricos, poucos grupos de produtos e capitalização. | Quais razões apresentar. | 1034–1040 |
| C5 | **Volatilidade anualizada** como medida de risco e base da volatilidade-alvo; **VaR** (variância-covariância com correlações, histórico, Monte Carlo; 1,65σ para 95%, 2,33σ para 99%; exemplo: US$ 17.068 para duas posições, em vez da soma 11.650 + 12.475, pois a correlação é −0,27). Retornos podem ter curtose de até 25 (caudas pesadas), por isso são necessários **testes de estresse**, tratados como exceções na gestão de crise. Hindenburg Omen (amplitude de ações; ~25% de acerto; não aplicável). | Estimativas de risco da carteira. | 1040–1044 |
| C6 | **Características do risco**: sistemas de tendência têm muitas pequenas perdas e poucos grandes ganhos e não conseguem reduzir abaixo de um limite a quantidade de operações perdedoras (fases laterais); **rompimentos** trocam risco maior por operação por maior confiabilidade — **risco da operação = max(High, n) − min(Low, n)**. Comparar sistemas após ajustar retornos ao mesmo risco; medir **tempo de recuperação** e **estabilidade dos retornos** (inclinação dos retornos anuais: queda indica deterioração). “Quanto maior o risco pode ficar?”: chance de 1% de perda de 50% ao mês implica 50% de chance até o 50º mês; com 100 casos há erro de 10%. **Em um choque, correlações vão a 1** — “não são os mercados, é o dinheiro”. | Caracterização e ressalvas do risco. | 1045–1046 |
| C7 | **Alavancagem**: margem multiplica P/L; alavancagem prática depende do tamanho da conta, não da margem. Corretoras mudam margem lentamente; chamada de margem com perda de 25% da margem inicial. **Reservas e volatilidade-alvo**: registrar P/L diário; calcular desvio-padrão; escolher volatilidade-alvo (tipicamente 15%; mínimo prático 6–8%); patrimônio necessário = desvio-padrão anualizado do P/L ÷ alvo (exemplo: US$ 266.592, 135× P/L diário médio); esperar perdas de 2–2,5σ, de modo que alvo de 15% implica drawdown de ~37%, agressivo; nível máximo de risco (liquidação) costuma ser 50%, podendo chegar a 10%; alavancagem de exposição versus alavancagem baseada em risco (reguladores usam valor nominal). | Capital necessário para um alvo de risco. | 1046–1050 |
| C8 | **Dimensionamento da posição**: mesmo valor monetário por ação gera riscos diferentes. Três métodos: (1) dinheiro ÷ preço; (2) dinheiro ÷ (preço × volatilidade anualizada); (3) dinheiro ÷ (ATR × √252). Os resultados diferem muito (BAC: 62× o tamanho de AAPL no método 1, o menor no método 2 e tamanho baseado em ATR no método 3); redistribuir o valor conforme o capital disponível. Dimensionamento por ATR reduziu a volatilidade do patrimônio de BAC em 27% num teste com média móvel de 200 dias. “Risco igual dá a cada operação a mesma chance de participar; se não for possível selecionar as melhores operações, risco igual é o mais conservador”. Sem controle de tamanho, volatilidade da carteira variou de 6% a 25%; teste rigoroso precisa definir o investimento como a maior quantia necessária. | Dimensionamento por volatilidade. | 1050–1054 |
| C9 | **Risco inicial da posição**: sistemas de tendência aceitam pequenas perdas; a perda em rompimentos é a amplitude (reduzi-la contraria o método); reversão à média aceita grandes perdas por alta confiabilidade, e stops a reduzem. **Stops** dimensionados pelo sistema, timing, volatilidade ou padrão gráfico (não fração fixa do capital); opções: parabólico, pontos de oscilação, máxima/mínima de n períodos, KAMA, **3 × ATR de 10 dias**. **Stop inicial** fixado na entrada, sem mover. **Trailing**: percentual fixo (3%), baseado em volatilidade (ATR/volatilidade; ISAM sugere 12 × ATR(252)), **percentual do lucro** (50%, somente após lucro-gatilho; usar o mais próximo entre esse stop e o inicial). **Dev-stop de Kase** (ATR da amplitude verdadeira de 2 dias + f × desvio-padrão; f = 1, 2,06–2,25, 3,20–3,50; aplicado desde o extremo da operação; acionado somente no fechamento). | Tipos de stop. | 1054–1056 |
| C10 | **Alvos de lucro**: essenciais em operações curtas (ruído), mais difíceis no seguimento de tendência (cauda longa; exige reentrada); `E + f × V` a partir do **ponto de entrada do sistema, não do preço efetivamente executado**. Teste de futuros de euro em 60 min (médias de 80 e 5 barras, alvos de 0,5–10 × ATR(20), 2002–2010): sistema lento de 80 barras foi melhor **sem** realização de lucro (líquido 121.655 versus 94.405 com alvo 10×, caindo com alvos menores); sistema rápido de 5 barras passou de −3.278 a +19.098 com 7,5× e foi negativo na maioria dos outros fatores. Fatores costumam ser escolhidos por mineração de dados. **Saídas parciais em três alvos** reduzem risco quando a distância do alvo é incerta. | Alvos conforme o estilo. | 1057–1059 |
| C11 | **Kaufman sobre stops**: stops e alvos são um duelo com o ruído; stops no fechamento e alvos em picos intradiários; stops “funcionam, exceto quando mais precisamos” (gaps, execução no extremo). Os mais propensos a funcionar **adaptam-se à volatilidade**; **trailing stops são mais práticos que stops iniciais**. Mapa de calor (títulos de 30 anos, 2000–2011, médias 10–100 × fator de stop por desvio-padrão 2–10): quase todos os stops superaram a média sem stop, mas foi apenas um mercado/período. **Frequência versus distância do stop**: em dados aleatórios, (número de acionamentos) × (distância) é constante. **Risco de proximidade** (agrupamentos de stops; grandes programas de tendência levam até 3 dias para entrar). **Gestão sem stops**: reduzir tamanho conforme a volatilidade aumenta (incluindo custos de troca). **Overlay de risco**: stops como percentual da margem ou da conta (1–2,5%). | Evidência de stops e alternativas. | 1059–1061 |
| C12 | **Seleção de mercado pelo ruído**: `ER = |C_t − C_{t−n}| / Σ|C_i − C_{i−1}|` (n = 65). Em futuros e ações, 1990–2011, o fator de lucro de uma média móvel de 65 dias tende a subir com ER médio (Eurodólares 0,1816 → 2,43; S&P 0,1203 → 1,16; MSFT, GE, trigo, soja, ouro, MRK e IBM abaixo ou perto de 1). Mercados com ER baixo/fator de lucro < 1 servem melhor à reversão à média; “não é necessário incluir mercados incompatíveis com a natureza da estratégia”. | Escolher ativos pelo ruído. | 1070–1072 |
| C13 | **Probabilidade de ruína**: vitórias/perdas de mesmo tamanho: `R = ((1 − A)/(1 + A))^c`, `A = P − (1 − P)`, c = capital em unidades (60% de acerto, c = 1 → 33%; c = 2 → 11%). Com uma meta G, a fórmula muda. **Ganhos e perdas desiguais** (Gehm): usa E (P/L esperado por operação), E2 (P/L ao quadrado esperado), `D = CA / E2`, `P = 0.5 + E / (2 √E2)`, `R = ((1 − P)/P)^D`; Vince derivou resultado semelhante. Exige muitas operações e o histórico pode subestimar o risco. | Capital versus ruína. | 1072–1075 |
| C14 | **Tendências do patrimônio e capitalização**: aumentar o tamanho junto com o patrimônio deixa a conta totalmente exposta no topo do ciclo; sequência +100%/−50% não rende nada quando capitalizada. Alternativa: manter exposição constante e deixar **reservas** acumularem; redistribuir margem/reservas somente depois de estabilizado o drawdown. **Negociar a curva de patrimônio** (parar quando média de 10 ou 60 dias do patrimônio da estratégia cair; S&P e ouro melhoraram, títulos pioraram; sem custos de troca e patrimônio hipotético otimista): resultados inconsistentes; primeiro verificar autocorrelação dos retornos. | Dimensionamento dinâmico pelo patrimônio. | 1085–1088 |
| C15 | **f ótimo**: `G(f) = P ln(1 + B f) + (1 − P) ln(1 − f)` (Kelly); `f = [p (PLR + 1) − 1] / PLR` (p = 0,5, PLR = 2 → 25%). Com frações do patrimônio atual, três perdas seguidas custam 57,81%, não 75%. f ótimo calculado pelo histórico muda a cada operação; apostar demais leva à ruína, de menos reduz lucro geometricamente. Lições de Elder: nunca fazer preço médio para baixo, nunca atender chamada de margem, liquidar primeiro a pior posição. Drawdown dentro da operação pode exceder muito o resultado final. Aproximação de Markowitz: alavancagem ótima `= μ/σ²`. **“Considere esses métodos apenas para reduzir a alavancagem, não para aumentá-la.”** | Kelly/f ótimo e ressalvas. | 1088–1092 |
| C16 | **Comparar esperado e real**: com 33% de acerto e recompensa/risco 4:1, deve-se parar após 10 perdas? Usar a **distribuição binomial** `B(l; p, n) = n!/(l!(n−l)!) p^l (1−p)^(n−l)` para calcular a probabilidade de l perdas em n operações; fórmula da sequência `(1/2)^(n+2)`. (Conclusões e tabelas das pp. 1093–1098 não foram lidas.) | O sistema está quebrado? | 1092–1093 |

As observações sobre cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Limite de risco por operação | ✅ | `assess_signal` (risk_management/domain): limite de fração da posição, risco por operação calculado a partir da distância do stop, `max_candle_range_pct`, limites de valor nominal; há limites ao vivo e kill switch. |
| Dimensionamento pela distância do stop | ✅ (ao vivo) | Risco por operação ÷ distância do stop; distância percentual fixa, portanto não considera volatilidade (cap. 20, O2). |
| Dimensionamento no backtest | ⚠️ | Dimensionamento trivial “all-in” difere do módulo de risco ao vivo; backtest não reproduz o dimensionamento com gestão de risco (lacuna conhecida). |
| Meta de volatilidade | ❌ | Nenhuma. |
| Métricas: Sharpe, Sortino, Calmar, Ulcer, DP, razão de drawdown, recuperação | ❌ | `Metrics` possui PnL líquido, retorno, buy-and-hold, drawdown máximo, taxas, taxa de acerto, fator de lucro e PnL médio por operação. |
| Tipos de stop | ⚠️ | Stop percentual fixo e take profit opcional; sem trailing/ATR/dev stop; ao vivo usa stop nativo da corretora. |
| Semântica do alvo de lucro (desde a entrada do sistema) | ✅ (por construção) | Alvos calculados desde o preço de entrada (verificar em `stops.py`). |
| Risco de ruína / Kelly | ❌ | Nenhum. |
| VaR | ❌ | Um bot = um ativo; sem agregação de carteira. |
| Seleção de mercado por ruído | ❌ | Sem razão de eficiência. |
| Margem e alavancagem | n/a | Spot comprado, sem margem ou empréstimo. |
| Negociar a curva de patrimônio | ❌ | Nenhum. |
| Modelo de custo de liquidez | ❌ | `slippage_bps` fixo. |
| Esperado versus real (binomial) | ❌ | Nenhum. |

## 3. Oportunidades

### O1 — Métricas ampliadas de risco: Sortino, Calmar, Ulcer, razão de drawdown e recuperação *(livro: C4, pp. 1034–1040)*

Adicionar fórmulas documentadas (anualização de 365 dias para cripto): `Calmar = retorno anualizado / drawdown máximo`, Sortino com MAR explícito (padrão 0), Ulcer Index, **DP e razão de drawdown**, **maior duração do drawdown e tempo de recuperação**, **tempo no mercado** e Sharpe, ressalvando que não revela ordem de retornos nem grandes saltos. Mostrar tamanho da amostra (quantidade de operações e dias) e alertar quando for pequeno (poucos drawdowns, amostra pequena ou histórico curto aumentam risco). Mesma família de O1/O2 do cap. 2 e O7 do cap. 21; implementar uma vez. **Complexidade:** baixa. **Validação:** fixtures de fórmula fechada (curvas monotônicas, um drawdown); invariância a escala constante do patrimônio.

### O2 — Dimensionamento por volatilidade na avaliação de risco e no backtester *(livro: C8, pp. 1050–1054)*

* **Proposta:** (a) adicionar ao módulo de risco modo de dimensionamento `risk_per_trade / (k × ATR)` (a distância do stop passa a ser múltiplo de ATR, cap. 20, O2) — “risco igual por operação”; (b) fazer o **backtester usar a mesma função de dimensionamento que a negociação ao vivo**, fechando a lacuna conhecida; (c) manter o dimensionamento all-in como opção explícita de comparação.
* **Motivo:** a lição central é igualar risco, não dinheiro (método 3, baseado em ATR, considerado melhor; reduziu volatilidade do patrimônio em 27% no exemplo BAC). Para um bot de ativo único, dimensionar pela volatilidade significa posições menores em regimes voláteis, estabilizando a volatilidade.
* **Ressalvas:** evidência do livro é de uma ação e estratégia; tamanhos ajustados à volatilidade mudam no tempo, portanto o investimento necessário é o maior valor histórico; há custos de troca ao rebalancear; quantidade fracionária e mínimos da corretora (lote, `minNotional`) restringem contas pequenas.
* **Complexidade:** média (função compartilhada, motor de backtest e testes). **Riscos:** resultados de backtests existentes mudam; manter o modo antigo como padrão, atrás de parâmetro explícito, e registrar sua versão no resultado/hash de reprodutibilidade. **Validação:** resultados idênticos entre backtest, paper e dimensionamento ao vivo para as mesmas entradas (teste de propriedade); respeitar limites.

### O3 — Dimensionamento por volatilidade-alvo do bot (modo de pesquisa) *(livro: C7, pp. 1048–1049)*

Calcular, a partir da série de P/L do backtest, o capital necessário para determinada volatilidade anualizada-alvo (tabela do livro: `investment = annualised stdev of P/L / target`) e o drawdown esperado de 2–2,5σ (o livro mostra que alvo de 15% implica drawdown de ~37%). Oferecer como **calculadora informativa** junto ao backtest (“com este perfil de P/L, volatilidade de 15% exige X; perda de 2,5σ equivale a Y% disso”); alvos práticos mínimos de 6–8% como referência. **Complexidade:** baixa. Não redimensionar posições ao vivo automaticamente.

### O4 — Família de trailing stops (percentual, ATR, percentual do lucro com gatilho) *(livro: C9, C11, pp. 1054–1056, 1059)*

Na mesma linha de O2 do cap. 19 e O2 do cap. 20: (a) trailing percentual fixo desde o maior fechamento; (b) trailing ATR abaixo da maior máxima; (c) **stop por percentual de lucro, ativado somente após lucro-gatilho**, usando o mais próximo entre ele e o stop inicial; (d) acionamento opcional **somente no fechamento** (no livro, stops no fechamento exploram ruído). Em cripto, a variante por fechamento expõe a gaps/flash crashes entre fechamentos; permitir apenas para pesquisa de backtest ou manter stop nativo da corretora como piso rígido. Lições de Kaufman: stops devem se adaptar à volatilidade; trailing é mais prático que o inicial; usar mapas de calor (cap. 21, O1); evidência de apenas um mercado no livro. **Complexidade:** média (lógica de substituição de ordem ao vivo). **Validação:** testes determinísticos do trailing; paridade backtest/paper.

### O5 — Não usar alvos de lucro por padrão em estratégias de tendência; oferecer saída parcial como experimento *(livro: C10, pp. 1057–1059)*

O teste com euro mostra realização de lucro prejudicando o sistema lento de tendência e ajudando um sistema muito rápido e ruidoso. Documentar que o comportamento padrão de `ema_crossover`/`donchian_breakout` é **sem alvos fixos** (mantém posição até sinal de saída) e permitir comparação com alvos na ferramenta de ablação (cap. 8, O7). **Saída parcial** (três realizações parciais) poderia ser configuração experimental de risco; exige suporte a preenchimento parcial no modelo de posição (posição, operações e contabilização por lote) — mudança maior, não recomendada antes do básico. **Complexidade:** documentação agora; alta para saída parcial.

### O6 — Consciência de gaps nos stops: eles falham quando mais precisamos *(livro: C11, p. 1060 · regras de choque no cap. 22, O5)*

Manter o stop nativo atual da corretora e acrescentar **estimativa de risco sensível a gaps**: informar no backtest a pior perda relativa à distância do stop (razão de slippage do stop) e dimensionar posições para que a perda por gap além do stop (por exemplo, maior gap de candle observado ou movimento de 5×ATR) fique abaixo da perda máxima aceitável. `max_candle_range_pct` trata parcialmente apenas o candle do sinal. **Complexidade:** média. **Validação:** fixtures sintéticas com gaps.

### O7 — Visão da razão de eficiência dos ativos e adequação da estratégia *(livro: C12, pp. 1070–1072)*

Calcular ER médio em uma janela por ativo/timeframe importado e exibi-lo junto à escolha de estratégia: ER baixo → mais ruído → menor adequação a estratégias de tendência. O gráfico de dispersão do livro mostra relação positiva entre fator de lucro e ER, mas com exceções grandes (IBM, AMZN, ouro): é **orientação, não regra**. Combinar O1 do cap. 1 (diagnósticos ER) e O2 do cap. 17 (helper compartilhado). **Complexidade:** baixa. **Validação:** ER = 1 em linha reta; fixtures conhecidas.

### O8 — Calculadora informativa de risco de ruína e probabilidade de drawdown *(livro: C13, pp. 1072–1075 · C16, p. 1092)*

Calculadora informativa com estatísticas de operações da plataforma: (a) risco de ruína com ganhos/perdas desiguais (Gehm: E, E2, D, P, R), limiar de ruína declarado (por exemplo, drawdown de 50%) e leitura conservadora; sinalizar amostra insuficiente; (b) **bootstrap** Monte Carlo da ordem das operações — o livro critica embaralhar blocos em estratégias tendenciais por separar uma sequência lucrativa da reversão; apresentar como cenário de estresse, não estimativa de risco, e preferir bootstrap estacionário/em blocos que preserve estrutura local (adaptação nossa, identificar como tal); (c) expectativa binomial de perdas consecutivas (`P(l perdas em n operações)`; por exemplo, chance de 10 perdas nas primeiras 10 operações com taxa de perda de 67% = 0,67^10 ≈ 1,8%) para responder objetivamente “devo parar o bot após k perdas?”. **Complexidade:** baixa–média. **Riscos:** fórmulas pressupõem operações independentes com distribuição estável; cripto tem mudanças de regime, portanto rotular resultados como “indicativos”. **Validação:** verificar fórmulas fechadas e concordância da simulação dentro da tolerância.

### O9 — Kelly/f ótimo apenas como orientação fracionária *(livro: C15, pp. 1088–1092)*

Exibir Kelly (equivalente a `f = p − (1−p)/PLR`) e meio-Kelly calculados com estatísticas do backtest validado junto da fração de posição configurada, com rótulo “limite superior, não recomendação”. O próprio livro recomenda usar apenas para reduzir alavancagem, nunca aumentá-la; f ótimo depende da maior perda e muda a cada operação; o perigo está em apostar demais. **Complexidade:** baixa. **Riscos:** usuários podem tratar como alvo; a interface deve mostrar como verificação de teto (“sua fração de posição supera meio-Kelly da vantagem testada”). **Validação:** exemplos conhecidos (p = 0,5, PLR = 2 → 25%).

### O10 — Filtro da curva de patrimônio como experimento de pesquisa, não recurso *(livro: C14, pp. 1085–1088)*

Testar somente no backtester “pausar o bot quando a média móvel do próprio patrimônio estiver caindo”. O livro encontrou resultados inconsistentes (S&P e ouro melhoraram, títulos pioraram), sem custos de troca; alerta que autocorrelação dos retornos precisa ser verificada e patrimônio hipotético é otimista. **H-EQUITY-FILTER**; passar pelo pipeline; **complexidade:** média; não recomendado ao vivo.

### O11 — Modelo de custo de liquidez calibrado com execuções registradas *(livro: C3, pp. 1033–1034)*

`custo ∝ tamanho da ordem × volatilidade / volume do mercado`, com fator dependente da direção (mais alto ao comprar em preço ascendente). Candles têm volume; combinar com O2 do cap. 16 e O5 do cap. 20 (limite de volume). Para contas pequenas, efeito é insignificante; modelo importa quando `capital` cresce. **Complexidade:** média; calibrar somente quando houver execuções suficientes.

### O12 — Política de reservas para capitalização (informativa) *(livro: C14, pp. 1085–1086)*

Documentar e simular três políticas de capital: capitalização total; tamanho fixo com reserva acumulada; tamanho fixo com redistribuição após estabilização do drawdown (exemplos do livro). Comparação de “política de capital” no backtester (fração da posição aplicada ao capital inicial ou ao patrimônio atual) mostra como a capitalização amplia drawdowns. A `position fraction` da plataforma usa patrimônio atual (verificar). **Complexidade:** baixa (parametrizar base patrimonial do dimensionamento). **Validação:** exemplos determinísticos do livro (ciclos +100%/−50%).

### Não aplicável

Margem de futuros, regras de margem de corretoras e exchanges, limites europeus de alavancagem, Hindenburg Omen, teoria da curva de utilidade (usar apenas na divulgação de risco ao usuário), VaR de variância-covariância para carteira multiativo (retomar quando houver posições simultâneas, cap. 24), hedgers comerciais, razão de Treynor (beta ao S&P).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Métricas de risco ampliadas O1 | alta | alta | – | baixa | – |
| 2 | Dimensionamento por volatilidade e paridade backtest/ao vivo O2 | muito alta | muito alta | alta | média | helper ATR (cap. 20, O1) |
| 3 | Calculadora de ruína/drawdown/binomial O8 | média | alta | – | baixa–média | O1 |
| 4 | Verificação de teto Kelly O9 | – | alta | – | baixa | O1 |
| 5 | Visão ER O7 | média | – | – | baixa | helper ER |
| 6 | Calculadora de volatilidade-alvo O3 | – | média | – | baixa | O1 |
| 7 | Trailing stops O4 | – | alta | média | média | helper ATR; projeto ao vivo |
| 8 | Dimensionamento sensível a gaps O6 | – | alta | – | média | O2 |
| 9 | Comparação de política de capital O12 | média | média | – | baixa | motor |
| 10 | Sem alvos padrão/saída parcial O5 | – | média | – | documentação / alta | – |
| 11 | Modelo de custo de liquidez O11 | média | – | – | média | registros de execução |
| 12 | Filtro de patrimônio O10 | baixa | – | – | média | pipeline |

## 5. Arquivos afetados

`analytics/domain/metrics.py` (e novos módulos analytics), `risk_management/domain/` (modos de dimensionamento, stops), `backtesting/domain/engine.py` (função de dimensionamento compartilhada; política de capital), `trading/application/trader.py` (substituição de stop), `execution/domain/fills.py` (modelo de custos), `docs/openapi.json`, resultados de backtest e formulários de bot do app (painéis informativos), testes.

## 6. Plano incremental

1. Métricas (O1), recomendações informativas (O8, O9, O3) e visão ER (O7) — somente leitura.
2. Função compartilhada de dimensionamento e paridade com backtest (O2), atrás de opção explícita e versão de reprodutibilidade.
3. Trailing stops no backtest/paper (O4), dimensionamento sensível a gaps (O6).
4. Comparação de política de capital (O12); depois, experimentos O10/O11.

## 7. Critérios de aceitação e testes

* Todas as fórmulas correspondem a fixtures calculadas manualmente (Calmar, Sortino, Ulcer, DP, ruína e exemplos Kelly do livro: p = 0,5, PLR = 2 → 0,25; ruína com 60% de acerto, c = 1 → 0,333, c = 2 → 0,111).
* Backtest e negociação ao vivo produzem quantidades idênticas para entradas idênticas; limites de risco nunca são excedidos; padrões inalterados.
* Recomendações informativas exibem o tamanho da amostra e o rótulo “somente indicativo”; nenhum comportamento ao vivo muda.
* ruff, mypy e testes existentes aprovados.

## Ressalvas

A maioria das tabelas numéricas usa futuros ou ações dos EUA e antecede custos específicos de cripto; volatilidade-alvo de 15% e limites de 5%/3% do capital por operação são práticas da indústria citadas pelo livro, não ótimos comprovados. VaR pressupõe retornos normais, embora o próprio livro mencione curtose de até 25; fórmulas de ruína pressupõem operações independentes; as desvantagens de f ótimo citadas pelo autor foram mantidas. As passagens sobre adicionar a posições, capitalizar por piramidação, seleção de mercados por movimento direcional e tabelas finais de esperado versus real não foram lidas.
