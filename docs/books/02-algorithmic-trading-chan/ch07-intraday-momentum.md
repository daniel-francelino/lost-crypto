# Livro 2 · Capítulo 7 — Estratégias de momentum intradiário

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 155–168 foi lido. O raspador do calendário de resultados em MATLAB (Quadro 7.1) foi lido, mas não resumido.

Os exemplos são estratégias de ações, futuros e câmbio, com vendas a descoberto, aberturas/fechos diários, calendários de resultados, rebalanceamento de ETFs e livros de ordens; os resultados não incluem custos e cobrem 2004–2012. A maioria não se aplica ao Lost Crypto.

## 1. Resumo do capítulo (pp. 155–168)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Momentum entre pregões tem poucos sinais independentes (Sharpe menor e significância fraca) e sofre após crises; **momentum intradiário mais curto evita ambos os problemas**. Todas as causas de momentum do cap. 6 atuam intradiariamente, exceto retornos de rolagem; uma nova causa é o **acionamento de ordens stop** (rompimentos). | 155–156 |
| C2 | **Estratégia de lacuna na abertura**: comprar se a abertura superar a máxima anterior por uma fração (0,1) do desvio-padrão dos retornos diários dos últimos 90 dias; vender a descoberto se ficar abaixo da mínima anterior pelo mesmo valor; fechar no fim do dia. Futuros FSTX: retorno anual 13%, Sharpe 1,4 (2004–2012); GBPUSD com horários próprios de abertura/fecho: 7,2%, Sharpe 1,3. Hipótese: após período sem negociação (noite/fim de semana), stops são acionados em conjunto e desencadeiam uma cascata. | 156–157 |
| C3 | **Momentum acionado por notícias**: deriva pós-divulgação de resultados (entrar na abertura se o retorno overnight superar meio desvio-padrão em qualquer direção, **sem interpretar a notícia**; sair no fecho): S&P 500, 2011–2012, retorno anual 6,7%, Sharpe 1,5, alavancagem possível de apenas cerca de 4×; manter durante a noite teve retorno médio negativo, indicando que o horizonte da deriva encolheu para intradiário. Outros eventos (mudanças de analistas, fusões/aquisições, cerca de 3% ao ano, mudanças em índices) também mostram esse encurtamento. Nos testes do autor, divulgações macroeconômicas não tiveram efeito significativo em EURUSD; estudo anterior encontrou momentum de GBPUSD em 10 minutos. | 157–163 |
| C4 | **ETFs alavancados** precisam rebalancear perto do fecho na direção da variação do dia, criando momentum. Comprar DRN se o retorno até 15 minutos antes do fecho superar +2%, vender a descoberto se ficar abaixo de −2%: retorno anual 15%, Sharpe 1,8 (out. 2011–out. 2012); efeito maior em ETFs com mais ativos. | 163–164 |
| C5 | **Alta frequência**: desequilíbrio entre volumes de compra/venda prevê variações de preço de curto prazo (relação linear, mais forte em ações de baixo volume). Táticas: juntar-se à melhor oferta de compra (operação de razão), ajustar cotações, iniciar momentum e inverter posição (ordens enganosas), caçar stops junto a suportes/resistências e números redondos, fluxo de ordens (volume com sinal). O autor observa que lucros de HFT vêm de operadores mais lentos e que os tamanhos cotados diminuíram por causa disso. | 164–168 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Momentum por rompimento | ✅ | `donchian_breakout` compra acima da máxima de N barras; é da família de C1/C2 e somente comprada. |
| Lacuna/abertura de sessão | n/a | Cripto negocia 24/7; não há lacuna noturna/de fim de semana. “Abertura diária” (00:00 UTC) é apenas convenção. |
| Intervalos intradiários | ✅ | Há suporte a candles de 1m, 5m, 15m, 1h, 4h e 1d (`Timeframe`). |
| Notícias/eventos, mudanças em índices, rebalanceamento de ETFs | ❌ / n/a | Não há dados de eventos; anúncios de listagem e rebalanceamento não existem no sistema. |
| Livro/fluxo de ordens | ❌ | Só se armazenam candles OHLCV (`market_data/domain/models.py::Candle`: abertura, máxima, mínima, fecho, volume). Sem compra/venda, profundidade ou volume com sinal. |
| Execução de alta frequência | n/a | Fluxo baseado em candles via REST, mínimo de 1 minuto; preenchimento simulado na próxima abertura. Não é uma infraestrutura HFT. |
| Custos em horizontes curtos | ✅ | Taxas e slippage sempre aplicados; modelo usa bps fixos, otimista em 1m. |

## 3. Oportunidades

### O1 — Pesquisa de tendências em horizontes curtos e mais sinais independentes *(livro: C1, p. 155; relacionado ao livro 2, cap. 6 C7)*

* **Problema:** bots de tendência entre pregões fazem poucas operações, reduzindo a confiança estatística (livro 2, cap. 6). O livro propõe períodos de manutenção mais curtos.
* **Proposta:** usar intervalos existentes de 5m/15m/1h nos backtests e apresentar, por intervalo, quantidade de operações completas independentes, custo e significância (livro 2, cap. 1 O1), permitindo observar o compromisso. Não exige nova função além das métricas já propostas; é orientação de pesquisa/interface (“operações completas necessárias”).
* **Risco:** em horizontes curtos, custos e slippage dominam; o modelo fixo em bps é menos realista (ver O2).

### O2 — Slippage dependente do tamanho da ordem e da volatilidade em intervalos curtos *(livro: C5 e cap. 1, pp. 164–167 · adaptação)*

* **Problema:** slippage constante subestima os custos em movimentos rápidos e livros pouco líquidos, justamente onde atua o momentum intradiário; o autor alerta que backtests de comportamento semelhante a HFT são pouco confiáveis (livro 2, cap. 1 C7).
* **Proposta:** modelo opcional de slippage escalado pela volatilidade recente (por exemplo, amplitude do candle) e pelo tamanho da ordem em relação ao volume do candle; manter o modelo fixo como padrão e exibir faixa de sensibilidade de custos (livro 1, cap. 2 O4).
* **Benefício:** backtests de curto prazo mais honestos. **Complexidade:** média. **Riscos:** parâmetros adicionais também podem ser ajustados em excesso; calibrar com slippage realizado registrado (livro 1, cap. 5 O4), não por estimativa arbitrária. **Validação:** testes unitários com valores calculados manualmente e análise de sensibilidade.

### O3 — Indicador de fluxo de ordens por candle com volume agressor *(livro: C5, pp. 167–168 · adaptação; o livro usa dados de ticks)*

* **Problema:** armazenamos apenas OHLCV, mas a ideia de fluxo de ordens do livro (volume com sinal prevê movimentos curtos) exige distinguir compras e vendas.
* **Proposta (verificar antes de desenvolver):** dados de *kline* da corretora costumam incluir volume de compras a mercado por candle (confirmar no adaptador Binance e testnet); armazená-lo numa coluna aditiva e expor indicador “desequilíbrio de fluxo” (volume comprador agressor ÷ volume total) para diagnósticos e, mais tarde, estratégias. É **adaptação nossa**; a evidência do livro refere-se a fluxo por tick em ações/futuros/câmbio.
* **Benefício:** caminho de baixo custo para sinais de microestrutura sem feed do livro de ordens. **Complexidade:** média (migração, mudança no importador, carga retroativa). **Riscos:** agregação em candles perde o momento dentro do candle considerado pelo livro; mais dados armazenados; não há evidência de poder preditivo em cripto. **Validação:** teste de importação com fonte falsa; correlação do indicador com retorno do candle seguinte, apenas como diagnóstico.

### O4 — Considerar ideias de abertura de sessão inaplicáveis; não portar estratégia de lacuna *(livro: C2, pp. 156–157)*

Não existe lacuna de noite/fim de semana no mercado cripto à vista. Um mecanismo parecido poderia ser um rompimento da faixa anterior de N horas/dias, já aproximado por Donchian. Não se propõe trabalho.

### O5 — Momentum baseado em eventos: apenas no backlog *(livro: C3, pp. 157–163)*

Exige eventos legíveis por máquina (listagens, remoções, atualizações de protocolo, divulgações macroeconômicas). Registrar como **B-EVENTS**; hoje não há fonte, e o livro diz que esses efeitos encolheram até o horizonte intradiário.

### Não aplicável

Deriva de resultados empresariais, alterações de índices, rebalanceamento de ETFs alavancados, desequilíbrio entre compra/venda, ajuste de cotações, ignição de momentum, inversão de posição e caça a stops (os dois últimos descrevem comportamentos adversariais contra os quais o sistema deve **se defender**, não imitar; ver nota).

### Nota defensiva (interpretação nossa, não recomendação do livro)

O livro descreve táticas enganosas de ordens (ignição de momentum, inversão de posição e caça a stops). Para um bot que usa ordens a mercado em níveis de stop conhecidos, a lição relevante é que **níveis visíveis de stops e concentrações em números redondos podem ser alvo**. A simulação já executa stops atravessados por uma lacuna na abertura; não se propõe outro controle, mas o registro do slippage realizado (livro 1, cap. 5 O4) mostrará se a execução dos stops é sistematicamente pior que a estimada.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O2 slippage ajustado por volatilidade/tamanho | alta | média | – | média | livro 1, cap. 5 O4 (dados de calibração) |
| 2 | O1 comparação de intervalos temporais | média | – | – | baixa | livro 2, cap. 1 O1 |
| 3 | O3 indicador de volume agressor | baixa (especulativo) | – | – | média | confirmar campos da corretora |
| 4 | O5 eventos | – | – | – | n/a | B-EVENTS |

## 5. Arquivos afetados

`execution/domain/fills.py`, `backtesting/domain/models.py` (opção de slippage), `market_data/domain/models.py`, `orm.py`, importador e adaptadores de corretora (O3, aditivo), formulário/detalhes de backtest no app e testes.

## 6. Plano incremental

1. Registrar slippage realizado (livro 1, cap. 5 O4) para calibrar o modelo.
2. Adicionar modelo opcional de slippage, mantendo o padrão atual.
3. Incluir sugestões de comparação entre intervalos.
4. Verificar disponibilidade de volume agressor; se houver, armazenar e executar o diagnóstico.

## 7. Critérios de aceitação e testes

* Com a nova opção de slippage desligada, o resultado padrão do backtest permanece idêntico bit a bit.
* Testes unitários da nova opção cobrem escala por volatilidade/tamanho e garantem que o slippage nunca favorece a operação.
* Nova coluna de candle é anulável; candles existentes e hashes (`hash_candles`) não mudam, salvo adesão explícita à coluna.
* Ruff, mypy e testes existentes passam.

## Ressalvas

Os números (retorno anual de 7–15%, Sharpe 1,3–1,8) vêm de amostras de um ano ou de um único mercado, excluem custos e dependem de instrumentos/microestrutura diferentes do mercado cripto à vista. O autor diz que a duração do momentum de notícias continua diminuindo. O capítulo não sustenta afirmação alguma sobre rentabilidade em cripto.
