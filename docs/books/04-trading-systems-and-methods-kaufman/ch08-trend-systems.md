# Livro 4 · Capítulo 8 — Sistemas de tendência

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** lidas pp. 309–323 (por que tendências funcionam, sinais básicos, perfil tendencial e bandas), 336–347 (comparação de seis sistemas) e 359–361 (média única versus múltiplas e escolha de velocidade). Aplicações de uma tendência, técnicas com duas linhas e sequências de várias médias (pp. 323–335, 348–358, 362–368), incluindo saídas antecipadas e cruzamentos projetados, **não** foram lidas em detalhe nem são resumidas. É o capítulo mais próximo de `ema_crossover` e `donchian_breakout`.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Por que sistemas tendenciais funcionam**: tendências longas vêm de fundamentos lentos e persistentes (política de juros); preços têm **sequências de cauda pesada** (mais sequências longas que num modelo de cara/coroa: 100 lançamentos produzem ~6 sequências de quatro e 1–2 de seis); “fluxos de dinheiro movem mercados”. **Não funcionam sem tendência**; métodos tendenciais têm retornos semelhantes no tempo, mas diferem em **perfil de risco e frequência de negociação**. Tendência depende do horizonte e ruído tolerado; “há tendência se for possível lucrar com estratégia tendencial”. | Premissas e limites. | 309–311 |
| C2 | **Cauda pesada nos lucros**: histogramas dos resultados por operação de MA de 40 dias em títulos, S&P, euro, petróleo e ouro têm cauda longa à direita e curta à esquerda; um ganho grande pode compensar 30+ perdas pequenas (“S&P tem caudas relativamente menores que outros mercados”). | Distribuição de resultados tendenciais. | 311–312 |
| C3 | Tendências são mais claras em frequências menores; **tendências rápidas são menos estáveis**; juros e câmbio têm tendências mais limpas que ações individuais; liquidez ajuda; mercados emergentes são tendenciais até a participação do público trazer ruído. Escolher mercados e intervalos compatíveis com operador (períodos longos, baixa frequência e vínculo mais próximo a fundamentos têm melhor resultado). | Onde seguir tendências funciona. | 313 |
| C4 | **Sinais básicos**: preço cruza linha de tendência versus direção da linha; confirmação pelo fecho. Sinal pela direção da linha gera **26–37% menos operações** e sobretudo melhores resultados na Amazon (janelas 80, 40, 20, 10, 5; períodos **dobram** para manter mudança percentual). Na janela mais rápida (5 dias), sinal por penetração do preço perdeu menos (atraso da linha é um peso). | Definir sinal. | 314–316 |
| C5 | **Consistência entre teste e negociação**: sinal calculado no fecho implica entrada no fecho; aguardar próxima abertura é negociar diferente do teste. Solução prática: calcular pouco antes do fecho ou prever preço que acionaria sinal (para MA, novo valor sobe se preço de hoje superar preço que sai da janela) e colocar stop antecipado. **Estudo de atraso na entrada** (Eurodólar versus S&P, 10 anos): Eurodólar (pouco ruído) tem melhor entrada no fecho do sinal e piora com atraso; S&P (ruidoso) melhora entrando na abertura ou fecho seguinte, exceto em 5 dias. | Momento de entrada e latência. | 316–318 |
| C6 | **Perfil típico de tendência** (futuros NASDAQ 100, direção de MA 40 dias, dez anos, sem custos): 150 operações, **34,7% vencedoras**, relação ganho/perda citada de 2,22 (texto extraído da tabela dá ganho médio 1.424,71 e perda média 41,28, incompatíveis; OCR está corrompido, então só se usa a razão citada), ganhos mantidos **31,65 barras contra 6,64** nas perdas, **10 perdas seguidas** contra 6 ganhos. Perfil geral: frequentemente menos de 30% de acertos; ganhos devem superar muito as perdas; vencedoras duram mais; sequências longas de perdas. Realizar lucro ou pôr stop “reduz ou elimina possibilidade de capturar cauda pesada” (alerta do autor sobre alterar perfil). | Como deve parecer um sistema tendencial saudável. | 317–320 |
| C7 | **Bandas e canais** reduzem operações sem sacrificar maiores ganhos: faixas de máximas/mínimas, Keltner (média central ± média da amplitude H/L/C), bandas percentuais, pontos absolutos, bandas de volatilidade escaladas por `s` (percentual da linha/preço, ATR ou desvio-padrão). Em **Eurodólar tendencial**, entrar ao atravessar banda piora; no **S&P ruidoso**, esperar melhora resultado (torna lucrativo o sistema de 40 dias). Bandas percentuais não servem a futuros ajustados retroativamente que ficam negativos. | Reduzir falsos sinais. | 320–323 |
| C8 | **Comparação de seis sistemas** (momentum, MA simples, suavização exponencial, rompimento N dias, rompimento swing e inclinação de regressão), sempre no mercado, sem stops, entrada no fecho, custos de US$20/operação de futuro e US$0,01/ação, vinte anos, períodos 5…160 (autor diz que duplicar 5, 10, 20, 40, 80, 160 daria amostra melhor). Achados: tendência de longo prazo é lucrativa; **todos sistemas básicos lucram se mercado tem tendência**; fator de lucro melhora com período; MA frequentemente melhor; **rompimento faz menos da metade das operações**, maior proporção vencedora (~pouco menos de 50%, contra ~34% MA/momentum e ~43% inclinação/EMA), maior lucro médio por operação e também maior risco. Períodos curtos geram mais operações, menor lucro por operação e maior sensibilidade a custo: **períodos com mais de 200 operações em vinte anos foram piores**. Diferenças de retorno líquido entre métodos são pequenas; diferenças reais são frequência, tamanho do retorno e risco por operação. | Concessões entre métodos. | 336–347, 360 |
| C9 | **Escolher velocidade** depende do usuário (fundo que entra mensalmente versus operador ativo); busca computacional pode sobreajustar (3 versus 20 dias, custos dominam); “melhor” período de seis meses ou mais pode só indicar que movimento sazonal foi perdido. Regra prática: marcar oscilações que se quer capturar, calcular duração média e usar período de cálculo de **cerca de um quarto da oscilação** (IBM: oscilação de 3 meses → MA de 16 dias; 36 operações, 20 lucrativas, sem custos). Exemplo de médias múltiplas (Eurobund): MA 80 dias PF 1,88; cruzamento 40/80 1,45; 20/40/80 PF 2,80 (tabela de um mercado). | Escolher parâmetros com critério. | 359–361 |

Resultados são de testes com futuros/ações, muitos sem custos. Referências a cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Duas regras de tendência | ✅ | `ema_crossover` (duas linhas exponenciais) e `donchian_breakout` (canal de N barras e canal de saída distinto). |
| Direção de linha única/preço versus linha | ❌ | Não oferecido. |
| Bandas ATR/percentuais/desvio em linha tendencial | ❌ | Não existem. |
| Estatísticas de perfil (duração de vencedoras/perdedoras, ganho/perda, sequência máxima) | ⚠️ | Há `win_rate`, `profit_factor`, `avg_trade_pnl`, mas não duração média por resultado, razão ganho/perda ou sequências (também livro 4, cap. 3 O1). |
| Consistência de horário entre teste e execução | ✅ | Motor preenche na abertura seguinte e trader real age sobre candles fechados; teste e operação são consistentes (livro 1, cap. 5 C1). |
| Sensibilidade a atraso de execução | ❌ | Não calculada. |
| Precalcular gatilho e deixar stop de entrada na corretora | ❌ | Trader reage após o fecho; não há ordens de entrada pendentes. |
| Ajuda para escolher velocidade | ❌ | Não existe. |
| Grades dobrando períodos | ❌ | Não oferecidas (livro 3, cap. 8 O1; livro 4, cap. 7 O1). |
| Atenção ao número de operações | ⚠️ | `fills`/`round_trips` são exibidos, sem orientação (>200 em vinte anos no cenário do livro). |
| Cruzamento de várias médias (20/40/80) | ❌ | Só duas EMAs. |

## 3. Oportunidades

### O1 — Métricas do perfil de tendência: razão ganho/perda, duração média de vencedoras/perdedoras e sequências máximas *(livro: C6, pp. 317–319)*

Calcular/exibir conjunto da Tabela 8.4 para cada backtest: quantidade e proporção de vencedoras, ganho médio, perda média, **razão ganho/perda**, **barras médias de manutenção de vencedoras e perdedoras**, maiores sequências de ganhos/perdas. Texto auxiliar: sistema com ~35% de acerto precisa razão média ganho/perda superior a 100/35 para lucrar; mostrar **razão necessária** junto à real (mesma aritmética da taxa de equilíbrio, livro 4, cap. 3 O1).

**Motivo:** permite verificar se o bot se comporta conforme projetado (bot tendencial que mantém vencedoras e perdedoras por igual é suspeito) e preparar psicologicamente para sequências de perdas; estas alimentam análise de risco de ruína (caps. 22–23). **Complexidade:** baixa (funções puras nas operações completas, duração em barras; precisa índices de barras de entrada/saída, deriváveis dos horários de execução). **Validação:** casos manuais no estilo da Tabela 8.4.

### O2 — Sensibilidade a atraso de execução *(livro: C5, pp. 316–318)*

Adicionar opção de atrasar preenchimento em `k` candles (k=0 comportamento atual na próxima abertura; 1, 2…) e reportar efeito em retorno/fator de lucro. Resultado depende do mercado: atraso prejudica tendências limpas e pode ajudar séries ruidosas. Medir por par/intervalo.

**Benefício:** teste de robustez para latência, fila, limites de requisição e indisponibilidade do operador; mudança simples no motor (deslocar sinais pendentes). **Complexidade:** baixa. **Riscos:** representa atraso só em barras; em 1m, várias barras excedem latência real; explicar interpretação. **Validação:** estratégia cuja vantagem desaparece com atraso deve mostrar isso; k=0 reproduz resultado atual bit a bit.

### O3 — Banda de histerese ao redor da tendência (ATR/percentual/desvio) como opção *(livro: C7, pp. 320–323)*

Parâmetro opcional `band_multiple` em `ema_crossover` ou diferença das EMAs: entrar comprado apenas se EMA rápida superar a lenta em mais de `s ×` medida de volatilidade (ATR ou desvio-padrão dos fechamentos); sair quando cair abaixo (zero ou banda menor). Bandas ajudam séries ruidosas e prejudicam tendenciais; condicionar à medição de ruído (livro 4, cap. 1 O1/O2). Desligado por padrão.

**Riscos:** mais um parâmetro e aumento de N; atraso de entrada; resultados variam por mercado nos próprios testes do livro. **Validação:** truncamento; contagem de operações (deve cair); perfil (acerto sobe? relação ganho/perda muda?). Hipótese **H-TREND-BAND**.

### O4 — Sinal de direção de linha tendencial única *(livro: C4, pp. 314–316)*

Modo de sinal “inclinação da EMA vira para cima/baixo” em vez de cruzamento entre duas EMAs. No livro, gera aproximadamente 26–37% menos operações que cruzar preço com linha (Amazon, dez anos). Cruzamento duplo existente já reduz oscilações em comparação ao preço; diferença da inclinação deve ser medida. **Complexidade:** baixa. Pode duplicar comportamento de EMA muito lenta versus rápida; verificar N efetivo (livro 3, cap. 6 O4).

### O5 — Predefinições de grade com períodos dobrados *(livro: C4, C8, pp. 315, 337)*

Como no livro 3, cap. 8 O1/livro 4, cap. 7 O1: autor usa 5, 10, 20, 40, 80, 160 para manter mudança percentual constante e evitar muitos períodos longos parecidos. Oferecer essa predefinição. **Complexidade:** trivial.

### O6 — Ajuda para escolher velocidade pela duração média das oscilações *(livro: C9, pp. 360–361)*

Auxiliar que detecte oscilações em candles armazenados (filtro swing; livro 4, cap. 5) e sugira período de cálculo de cerca de um quarto da oscilação média, avisando que período “ótimo” maior que quarto da duração da tendência pode tê-la perdido. Referência inicial **sem otimização** por desempenho. **Complexidade:** média (detecção de oscilações). **Riscos:** limite do swing também é parâmetro; regra de um quarto vem de um exemplo de ação do autor.

### O7 — Respeitar o perfil: não adicionar stops/alvos a tendências sem medir *(livro: C6, pp. 319–320)*

Autor alerta que stop e realização de lucro podem destruir captura de cauda pesada. Sistema já oferece `stop_loss_pct`/`take_profit_pct` opcionais. Acrescentar texto de ajuda e alerta: se `take_profit_pct` apertado estiver ativo, comparar com versão sem ele (execução de ablação de um clique, desativando cada regra opcional e reportando diferença). **Complexidade:** baixa a média. Ablação implementa recomendação de provar que cada recurso acrescentado melhora resultado (caps. 1 e 8). **Validação:** ablação reproduz resultado-base quando nada está ativado.

### Não aplicável

Mecânica de futuros, dados ajustados retroativamente, métodos swing/ponto-e-figura (não lidos), entrada de primeiro recuo de Raschke (não lida em detalhe).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O5 predefinição de períodos dobrados | média | – | – | trivial | – |
| 2 | O1 métricas de perfil tendencial | alta | média | – | baixa | duração de operações |
| 3 | O2 sensibilidade a atraso | alta | média | média | baixa | mudança no motor |
| 4 | O7 execução de ablações | alta | – | – | baixa–média | – |
| 5 | O3 banda de histerese (experimento) | média | – | – | baixa–média | auxiliar ATR e fluxo de validação |
| 6 | O6 ajuda de velocidade | baixa | – | – | média | detecção de oscilação |
| 7 | O4 sinal de inclinação | baixa | – | – | baixa | verificar N efetivo |

## 5. Arquivos afetados

`analytics/domain/metrics.py`, `backtesting/domain/engine.py` (atraso opcional), `backtesting/domain/models.py` (configuração), `backtesting/application/service.py` (tarefas de ablação/sensibilidade), `strategies/domain/ema_crossover.py` (banda opcional), auxiliares de indicadores, `docs/openapi.json`, formulários/detalhes de backtest e testes.

## 6. Plano incremental

1. Predefinição de grade e métricas de perfil.
2. Opção de atraso no motor, com teste (k=0 idêntico).
3. Executor de ablações.
4. Experimentos de bandas e inclinação pelo fluxo de validação.

## 7. Critérios de aceitação e testes

* Atraso zero mantém resultado do motor (teste de regressão contra execuções atuais).
* Métricas de perfil conferem com cálculos manuais; sequências e durações corretas em casos fixos.
* Novas opções de estratégia desligadas por padrão; Ruff, mypy e testes passam.

## Ressalvas

Todos os números de desempenho vêm de ações/futuros (muitos sem custos, 1990–2011), geralmente um mercado por afirmação. “Retornos semelhantes” entre métodos é observação do autor, não prova. Taxa de acerto de 30–35% refere-se aos testes dele; cripto pode diferir.
