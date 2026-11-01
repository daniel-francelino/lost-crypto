# Livro 1 · Capítulo 7 — Tópicos especiais em trading quantitativo

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **análise + plano de implementação detalhado (2026-11-01); nada foi implementado**. O diagnóstico foi revisado contra o código depois dos Caps. 2–5 (ver §2.1). Quem for implementar deve ler o §8.

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

### 2.1 O que mudou desde a versão anterior deste relatório (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| C2 limpeza de dados (pré-requisito de qualquer reversão à média) | ⚠️ | ✅ Cap. 3: integridade OHLC, relatório de outliers (`data_quality.candle_report`), guarda de lacunas, tudo gravado na corrida. **O5 deste capítulo está feito.** |
| Portões que uma estratégia nova precisa passar | parciais | ✅ teste de truncamento que roda em **toda** estratégia do catálogo (`tests/unit/test_lookahead.py`), contagem de tentativas e robustez do sweep, escada de custos, treino × teste, checagem de amostra por parâmetro livre, paridade bot × backtest. Uma estratégia nova ganha tudo isso de graça. |
| C8 saída por tempo | ❌ | ❌ continua (busca por `max_hold`/`holding` em `api/src`: nada). |
| C8 meia-vida | ❌ | ❌ continua. |
| C5 regime | ❌ | ❌ continua. O passo "regime" do diagnóstico de divergência (Cap. 5) só compara o retorno do bot com o pior período de um backtest comparável; não descreve o regime. |
| Catálogo | 2 estratégias de tendência | 2 estratégias de tendência (`ema_crossover`, `donchian_breakout`). |

**Achados novos que moldam o plano (todos verificados):**
* `StrategyContext` só traz `symbol`, `candle` e `position_quantity`: não há preço de entrada nem quantas barras o bot está posicionado. Uma saída por tempo precisa contar barras **dentro do estado da estratégia**.
* As estratégias são compartilhadas pelo motor de backtest, pelo trader e pelo replay de paridade. Uma regra de saída **dentro da estratégia** vale nos três sem mexer no motor nem no trader; já uma regra no motor deixaria o trader de fora e quebraria a paridade.
* `parse_numeric_params` (`strategies/domain/base.py`) recusa `None` em parâmetro inteiro; um inteiro opcional (`max_holding_candles`) exige ajustar essa função.
* `ParamSpec.minimum` e `ParamOut.minimum` são `int | None`; limites fracionários (`entry_z > 0`) não cabem.
* O teste de contrato (`tests/unit/test_strategy_contract.py`) usa uma série de **tendência** (lateral, alta, queda) e exige que **toda** estratégia compre na alta e venda na queda; uma estratégia de reversão à média reprovaria sem que haja erro. O teste precisa de série por estilo.
* `StrategyOut.too_many_parameters` compara `len(PARAMETERS) > 5`; `free_parameters` (checagem de amostra) conta só os parâmetros não nulos.
* O risco do bot recusa entradas em candles com amplitude acima de `max_candle_range_pct` (padrão 25%): as "facas caindo" mais violentas serão recusadas, com o motivo registrado.

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

### O5 — Limpeza de dados antes do trabalho de reversão à média *(livro: C2, p. 117)* — ✅ feito no Cap. 3
A dependência de O1 está satisfeita (integridade dos candles, relatório de outliers e guarda de lacunas existem). Nada a fazer aqui.

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
Substituído pelo plano detalhado do §8 (fases 1 a 5, com ordem, arquivos, contratos e testes).

## 7. Critérios de aceite e testes
* Qualquer estratégia nova passa no teste de truncamento e tem validação de parâmetros como as existentes.
* A meia-vida devolve o valor conhecido numa série sintética e `None` num passeio aleatório.
* A saída por tempo fecha no candle especificado e é coberta por testes do motor.
* Nenhuma mudança no comportamento das estratégias existentes; ruff, mypy, todos os testes verdes.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01 **sem alterar código**. Convenções do projeto: `Decimal` no domínio (sem `float`), números e dinheiro como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil. Próxima migração livre: **`0013`** (a última é `0012_alerts`); se o [Cap. 6, Fase A](ch06-money-and-risk-management.md) já tiver criado `0013_tail_risk`, a desta fase é a seguinte.

### Fase 1 — Saída por tempo dentro das estratégias (O2) · prioridade 1

Objetivo: parâmetro opcional `max_holding_candles` que fecha a posição depois de N candles, valendo igual no backtest, no paper/live e na paridade.

* **1.1 `parse_numeric_params`** (`strategies/domain/base.py`): novo argumento `optional_integers: frozenset[str] = frozenset()`; nesses nomes `None` é aceito e qualquer outro valor segue sendo inteiro (booleano continua recusado). As estratégias existentes passam `optional_integers={"max_holding_candles"}`.
* **1.2 Parâmetros:** `EmaCrossoverParams` e `DonchianParams` ganham `max_holding_candles: int | None = None` (validação `>= 1`) e um `ParamSpec("max_holding_candles", "integer", None, "Optional: sell after this many candles in the position (>= 1)", 1)`. Cada estratégia passa a ter **5** parâmetros declarados, ainda dentro do limite de 5 (`too_many_parameters` continua falso); `free_parameters` só conta o parâmetro quando preenchido.
* **1.3 Estado:** `EmaCrossoverState` e `DonchianState` ganham `bars_held: int = 0`. `serialize_state` grava a chave; `deserialize_state` lê `raw.get("bars_held", 0)`, para que bots já rodando continuem a abrir (um bot que já estava posicionado na hora do deploy recomeça a contagem em 0 e pode ficar até N candles a mais; avisar na nota da versão).
* **1.4 Regra** em `evaluate`: `held = state.bars_held + 1 if ctx.position_quantity > 0 else 0`. Com posição aberta, `max_holding_candles` definido e `held >= max`, emitir `Signal(SELL, EXIT, "holding limit of N candles reached")`, a menos que a própria estratégia já esteja saindo naquele candle (um único SELL; vale o motivo da estratégia). Um helper compartilhado em `base.py` (`next_bars_held(position_quantity, previous)`) evita copiar a regra três vezes. **Contagem:** conta os candles fechados vistos com posição aberta, inclusive o primeiro. No backtest padrão (`next_open`) a entrada preenche na abertura do candle seguinte e a estratégia só "vê" a posição ao fechar esse candle, então a posição dura N candles mais o intervalo até o preenchimento da saída (abertura seguinte); nos bots (`signal_close`) o preenchimento é no fechamento do candle do sinal. Stop e alvo continuam separados e ganham quando caem no mesmo candle (o motor checa a saída protetora antes de avaliar a estratégia).
* **1.5 Testes:** `tests/unit/test_time_exit.py` (as duas estratégias: a posição fecha exatamente no candle esperado; `None` reproduz o comportamento atual em série fixa; estado antigo sem a chave; entrada seguinte depois do limite; limite e saída da estratégia no mesmo candle dão um único SELL). Em `tests/unit/test_lookahead.py`, acrescentar à função `_params_variants` o caso `{"max_holding_candles": 5}` para as estratégias que têm o parâmetro, para o teste de truncamento cobri-lo. Em `tests/unit/test_strategy_contract.py` os testes de estado/reinício continuam valendo.
* **1.6 Front-end:** nenhuma tela nova. Os formulários de bot e de backtest montam os campos a partir de `GET /strategies` (`components/shared/strategy/strategy-fields.tsx`); um inteiro opcional vazio já é aceito por `validateParam` e ignorado por `buildStrategyParams` (`lib/shared/strategies/params.ts`). Acrescentar um caso em `params.test.ts`. Conferir o campo a 360 px.
* **1.7 Documentos:** README da API (parâmetro novo), OpenAPI, nota sobre a contagem.
* **Aceite:** com o parâmetro vazio, **todos** os testes atuais passam sem mudança; com ele preenchido, a posição fecha no candle certo no backtest, no trader e no replay de paridade (sem diferença `unexplained`).

### Fase 2 — Estratégia de reversão à média `mean_reversion_zscore` (O1) · prioridade 2

Depende da Fase 1 (parâmetro de tempo) e dos metadados de estilo do [Cap. 6, Fase C](ch06-money-and-risk-management.md) (`STYLE = MEAN_REVERSION`); fazer junto se a Fase C do Cap. 6 ainda não existir.

* **2.1 Arquivo e registro:** `api/src/modules/strategies/domain/mean_reversion_zscore.py`; uma linha em `AVAILABLE_STRATEGIES` (`strategies/catalog.py`).
* **2.2 Parâmetros (5, o limite):** `lookback` (inteiro ≥ 5, padrão 20: candles da janela, incluindo o atual), `entry_z` (número > 0, padrão 2,0: compra quando `z <= -entry_z`), `exit_z` (número, padrão 0: vende quando `z >= exit_z`; deve ser maior que `-entry_z`), `max_holding_candles` (inteiro opcional, Fase 1), `stop_loss_pct` (número opcional entre 0 e 100). Os valores padrão são **de partida nossos**, não vêm do livro.
* **2.3 Cálculo e sinais:** janela = últimos `lookback` fechamentos (o estado guarda a tupla); `média = Σ/n`; `desvio` = desvio-padrão **populacional** da janela com `Decimal.sqrt()` num contexto local de 40 dígitos (como `risk_ratios.py`); `z = (fechamento − média) / desvio`; desvio zero → nenhum sinal. Sem posição e `z <= -entry_z`: `BUY`/`ENTRY` com o motivo mostrando o `z`, e o stop (`percent_below_above`) só se `stop_loss_pct` estiver preenchido. Com posição: `z >= exit_z` → `SELL`/`EXIT` ("z-score back to X"); senão, o limite de tempo da Fase 1. Sem `take_profit` (a saída é a média). Nenhum sinal enquanto a janela não encheu. Estado: `closes: tuple[Decimal, ...]` e `bars_held: int`, serializados como strings.
* **2.4 Metadados:** `ParamSpec.minimum` passa de `int | None` para `Decimal | int | None` e `ParamOut.minimum` de `int | None` para `float | None` (`strategies/presentation/router.py`); o schema zod do app (`lib/shared/strategies/strategies.api.ts`) já aceita `number | null`, e `validateParam` usa `parseFloat`. `entry_z` com mínimo 0,1 e descrição "> 0".
* **2.5 Teste de contrato por estilo:** `_series()` de `tests/unit/test_strategy_contract.py` (lateral, alta, queda) vira `_series_for(strategy_cls)`: tendência para `TREND`, série oscilante com quedas fundas para `MEAN_REVERSION`; os pontos de corte do teste de reinício (30, 55, 75) passam a ser calculados a partir dos sinais emitidos (antes, durante e depois de uma operação) em vez de fixos; "compra e depois vende, alternando, sem níveis protetores por padrão" continua valendo para as duas famílias. Em `test_lookahead.py`, garantir que a série usada faz a nova estratégia **operar** (um teste de truncamento sem operações não prova nada).
* **2.6 Testes específicos:** `tests/unit/test_mean_reversion.py`: `z` calculado à mão numa janela pequena; desvio zero; limites exatos de entrada e saída; limite de tempo; nível do stop; validação (`lookback < 5`, `entry_z <= 0`, `exit_z <= -entry_z`, booleano recusado, chave desconhecida); ida e volta do estado em JSON.
* **2.7 Portão de pesquisa (não é código):** antes de qualquer bot, rodar o que os Caps. 2–5 construíram: backtest em pelo menos 2 anos e vários pares, com `cost_sensitivity`, `test_fraction`, `fill_timing = signal_close` e o risco do bot; sweep em `lookback × entry_z` lendo o veredito de robustez e a contagem de tentativas; depois paper e paridade. Esperar custos altos (reversão opera muito: ver a escada de custos) e comparar com comprar e segurar. Isto não promete lucro: se vale para cripto, **o livro não estabelece**.
* **2.8 Front-end:** nenhuma tela nova (nome, descrição e parâmetros vêm de `GET /strategies`). Conferir: formulário de backtest e de sweep com decimais em `entry_z` (`parseGridList`), o aviso de parâmetros e o formulário a 360 px. Atualizar `app/docs/06-screens.md` e o README da API.
* **Aceite:** passa em todo o teste de contrato e no de truncamento; um backtest completo roda e mostra tudo (métricas, períodos, escada de custos, qualidade, relatório de risco); parâmetros inválidos dão 422 com mensagem clara.

### Fase 3 — Meia-vida da reversão à média (O3) · prioridade 3

* **3.1 Função pura** `api/src/modules/analytics/domain/mean_reversion.py`: `half_life(series: Sequence[Decimal], *, log: bool = True) -> HalfLife | None`, com `HalfLife(n, slope, t_stat, half_life_bars, stationary)`. Regressão de mínimos quadrados `Δy_t = a + b·y_{t−1} + ε` em forma fechada com `Decimal` (`y` = log do preço por padrão); `φ = 1 + b`; se `0 < φ < 1`, `meia-vida = −ln(2) / ln(φ)` em barras (para `b` pequeno, igual ao `ln(2)/−b` do livro); `t_stat = b / erro-padrão(b)`; `stationary = t_stat <= −2,86`, valor crítico de 5% de um teste de Dickey–Fuller **com constante e sem defasagens** (valor de MacKinnon; **não vem dos capítulos, conferir na fonte antes de entregar**). Devolve `None` com menos de 100 pontos, série constante ou `b >= 0`; com `b < 0` mas `t_stat` fraco devolve a estimativa com `stationary = False`.
* **3.2 Serviço e endpoint:** `MarketDataService.half_life(...)` (`market_data/application/service.py`) lê os candles de `store.candles.get_range`, calcula fora do laço de eventos (`asyncio.to_thread`) e recusa mais de `MAX_ANALYSIS_CANDLES = 200_000` (422). `GET /api/v1/market-data/half-life?exchange&symbol&timeframe&start&end&log=true` em `market_data/presentation/router.py`, resposta `HalfLifeOut {n, slope, t_stat, stationary_at_5pct, half_life_bars, half_life_seconds, log_prices, gaps, warning}`; as lacunas vêm de `coverage` e viram aviso (a regressão usa os candles como estão).
* **3.3 Testes:** `tests/unit/test_half_life.py`: série AR(1) sintética com semente fixa e `φ = 0,95` (meia-vida teórica ≈ 13,5 barras) estimada dentro de uma tolerância declarada em 5.000 pontos; passeio aleatório → `stationary = False`; série em tendência → `None`; amostra curta → `None`; sem `float` no código de produção (o ruído do teste pode nascer em `float` e ser convertido para `Decimal`). `tests/integration/test_half_life.py`: endpoint com candles importados, 422 acima do limite.
* **3.4 Front-end:** `lib/shared/market-data/market-data.api.ts` (`getHalfLife` e schema), `QueryKey.MarketData.halfLife`, componente `components/market-data/half-life-card.tsx` dentro de `components/market-data/market-data-page.tsx`, reaproveitando o par, o intervalo e as datas já escolhidos na página. Mostra "meia-vida ≈ X barras (≈ Y horas)", o `t`, e o veredito em texto; estado vazio "sem reversão à média detectável (preços de cripto raramente são estacionários)". Esqueleto, erro com nova tentativa, vazio, dados; `vitest` para schema e formatação.

### Fase 4 — Descritores de regime de volatilidade (O4) · prioridade 4

Descritivo; **não** se opera com previsão de regime (o próprio livro é cético).

* **4.1 Funções puras** `api/src/modules/analytics/domain/regime.py`: `rolling_volatility(returns, window)` em O(n) com somas correntes (desvio populacional, `Decimal`), `terciles(values)`, `efficiency_ratio(closes, window)` (Kaufman: `|c_t − c_{t−w}| / Σ|Δc|`, como o Cap. 1 do Livro 4 propõe) e `regime_report(candles, equity_curve, in_market, window=30)` devolvendo, para volatilidade e para eficiência, três faixas (baixa/média/alta por **tercis da própria série**, sem limiar arbitrário): `{label, bars, share_pct, strategy_return_pct, asset_return_pct, in_market_pct}` e os limites dos tercis. A faixa da barra `t` usa só dados **até `t−1`** (a atribuição não olha o futuro); os tercis são da série inteira, o que é descritivo e deve ser dito na tela. Retornos por faixa compostos em `Decimal`.
* **4.2 Persistência:** coluna JSONB `regime` em `backtest_runs` (migração própria ou junto com a do Cap. 6 Fase A, a que vier primeiro: `0013_backtest_diagnostics` com `tail_risk` e `regime`), pelo mesmo fio do `risk_report`: `backtesting/application/ports.py`, `infrastructure/orm.py`, `infrastructure/repository.py`, `application/service.py` (calcular em `_execute` com `asyncio.to_thread`, pular com menos de `2 × window` candles), `presentation/router.py` (`RegimeOut`), OpenAPI. Execuções antigas ficam `null`.
* **4.3 Testes:** `tests/unit/test_regime.py`: série sintética com um degrau de volatilidade (faixas e participações esperadas, soma de `share_pct` fechando 100); os retornos por faixa compõem o retorno total; propriedade de não olhar o futuro (a faixa da barra `t` não muda ao cortar candles posteriores); janela maior que a série → `None`.
* **4.4 Front-end:** `lib/backtests/backtests.api.ts` (schema nullish), `components/backtests/regime-card.tsx` em `backtest-detail-page.tsx` depois de `PeriodsCard`: duas tabelas (volatilidade e eficiência) com as colunas acima e a frase "descritivo, não serve para prever o regime"; `vitest`; conferir a 360 px (tabela rolando dentro do card, como as de períodos e custos).

### Fase 5 — Sazonalidade e calendário (O6) · adiada

Só depois das fases 1 a 4 e de existir uma estratégia que justifique. Desenho mínimo para quando chegar a hora: função pura `analytics/domain/calendar.py` com retorno médio e `t` por hora UTC (24 grupos) e dia da semana (7), **correção por testes múltiplos** (31 testes: Bonferroni) e a contagem de tentativas, página de pesquisa somente leitura. Lição do livro (p. 143 em diante): lógica econômica antes do dado, variar as datas e esperar decaimento.

### Ordem, dependências e estimativa
1 → 2 (precisa de 1 e do `STYLE` do Cap. 6 Fase C) → 3 e 4 (independentes entre si e de 1 e 2) → 5.
Estimativa grosseira: Fase 1 ≈ 1 dia; Fase 2 ≈ 2 a 3 dias (a adaptação do teste de contrato pesa); Fase 3 ≈ 2 dias (1,5 back, 0,5 front); Fase 4 ≈ 2 dias. Só a Fase 4 mexe no banco.

### Decisões pendentes (para o operador)
* Valores de partida de `lookback` (20), `entry_z` (2,0) e `exit_z` (0) e se o desvio é populacional (proposta) ou amostral.
* Meia-vida em log do preço (proposta) ou no preço; confirmar o valor crítico de Dickey–Fuller na fonte.
* Se a nova estratégia nasce com `max_holding_candles` obrigatório (proposta: opcional, com aviso na tela quando vazio, junto da dica de stop do Cap. 6 Fase C).
* Prioridade real da Fase 4 (útil para ler resultados, sem efeito em dinheiro).

### Critérios de aceite gerais
Nenhuma estratégia existente muda de comportamento com os parâmetros novos vazios; nenhum `float` no domínio; `make check` e a suíte de integração verdes; `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas conferidas em 1366 px e 360 px; nada disso é evidência de lucro.

## Ressalvas
Toda cifra de desempenho neste capítulo é um exemplo de ações ou futuros da era de 2008, na maioria brutos de custos e vários com viés de sobrevivência que o próprio autor declara. A afirmação de que a reversão à média é mais prevalente que o momentum é a visão do autor para ações e **não deve ser assumida para cripto**. Nada aqui é evidência de lucratividade futura.
