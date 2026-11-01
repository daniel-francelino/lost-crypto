# Síntese de estratégia · Kaufman (livro 4) + Aronson (livro 3)

Status: **Fases 1 e 2 implementadas (2026-11-01); Fases 0, 3, 4 e 5 dependem de dados e de rodar a validação.** Ver "Estado da implementação" (seção 9) e "Resultado do backtest" (seção 10). Escrita em 2026-11-01 a partir dos relatórios de capítulo já feitos ([livro 4](04-trading-systems-and-methods-kaufman), [livro 3](03-evidence-based-technical-analysis-aronson)) e do código verificado nesta data. Páginas citadas são as dos livros, como nos relatórios. Tudo que é cripto é **adaptação nossa**: nenhum dos dois livros trata de cripto, e os resultados citados são de futuros e ações.

## 1. A ideia em uma frase

**Seguir tendência por rompimento de canal, só quando o mercado está "limpo" (pouco ruído), com stop dimensionado pela volatilidade e sem alvo de lucro; e só aceitar a estratégia depois de passar por um processo de validação que desconta a seleção de parâmetros.**

O Kaufman diz *o que* construir. O Aronson diz *o quanto desconfiar do resultado*. A estratégia só existe se as duas metades existirem.

## 2. O que cada livro contribui

| Decisão | Origem | Por quê |
|---|---|---|
| Família: **rompimento de canal** (Donchian), long/flat | Kaufman cap. 8 C8 (pp. 336–347); Aronson cap. 8 C4 (pp. 391–392, regra CBO) | O rompimento faz menos da metade das operações dos outros métodos, tem maior proporção de vencedoras e maior lucro por operação. É também a família que o Aronson usou como caso de estudo, com a barra atual excluída. |
| **Filtro de ruído** pela razão de eficiência (ER) | Kaufman cap. 1 C3–C4 (pp. 10–14); cap. 8 C7 (pp. 320–323) | Baixo ruído favorece tendência; alto ruído favorece reversão. Bandas/filtros ajudaram o S&P (ruidoso) e atrapalharam o Eurodólar (limpo): o filtro é **hipótese a medir**, não certeza. |
| **Stop por ATR**, sem alvo de lucro | Kaufman cap. 20 C7 (p. 861); cap. 8 C6 (pp. 319–320) | Alvo e stop apertado "eliminam a cauda longa" que paga o sistema. Um stop largo e adaptativo protege sem cortar a cauda. |
| **Dimensionar pelo risco do stop** | Kaufman cap. 20 C1, C2; cap. 23 | Com stop em ATR, o `max_risk_per_trade_pct` que já existe vira dimensionamento por volatilidade, sem módulo novo. |
| **Timeframe lento** (4h ou 1d), não 1m–15m | Kaufman cap. 1 C2 (pp. 8–9); cap. 8 C3 (p. 313); cap. 19 C4 | Tendências rápidas são menos estáveis; períodos longos dão mais lucro por operação e mais robustez. Em cripto o custo por operação também pesa mais nos prazos curtos. |
| **Grade pequena e geométrica** | Aronson cap. 8 C6 (pp. 419–420); Kaufman cap. 8 C4/C8 | Janelas em razão ≈ 1,5–2 evitam testar vários períodos quase idênticos. Menos regras testadas = menos viés de seleção. |
| **Justificativa teórica antes do backtest** | Aronson cap. 7 C2, C6 (pp. 332, 378–385) | Tendência como **prêmio de risco/reação lenta** é a hipótese. Sem ela o backtest é um resultado isolado e possivelmente sortudo. |
| **Esperar um perfil de tendência**: ~35% de acerto, ganhos 4–5× mais longos que perdas, séries de 8–10 perdas | Kaufman cap. 8 C6 (pp. 317–320) | Se o bot não tem esse perfil, algo não é o que se projetou. Prepara o operador para o ruim que é normal. |
| **Contar o universo testado** e corrigir o "melhor de N" | Aronson cap. 6 C1–C8, cap. 9 C1–C3 (pp. 255–330, 441–444) | O vencedor de uma varredura é estimativa enviesada para cima. No estudo de 6.402 regras, a melhor tinha p = 0,82 depois da correção, e 320 regras (5%) pareceriam significativas por acaso. |
| **Adicionar complexidade só enquanto o teste melhora** | Aronson cap. 9 C7 (pp. 457–461); Kaufman cap. 1 C8 (Occam), cap. 20 C11 | Cada filtro "elimina boas operações, na esperança de eliminar mais ruins". Cada um tem de provar isso por **ablação**. |

## 3. Especificação proposta: `trend_quality_breakout`

Long-only, spot, uma posição por bot, `StrategyStyle.TREND`. Decide em candles **fechados**; sinal preenchido na abertura seguinte (igual ao motor atual).

| Regra | Definição |
|---|---|
| Entrada | Fechamento acima da **máxima** dos `entry_period` candles anteriores **e** `ER(entry_period) ≥ er_min`. A barra atual não entra no canal. |
| Saída por canal | Fechamento abaixo da **mínima** dos `exit_period` candles anteriores (igual ao `donchian_breakout`). |
| Stop inicial | `entrada − atr_multiple × ATR(20)`, calculado no candle do sinal. Vai como `stop_loss` do sinal, então o stop nativo e o dimensionamento por risco já funcionam. |
| Alvo | **Nenhum.** A saída é o canal ou o stop. |
| Dimensionamento | Pelo módulo de risco existente (`max_risk_per_trade_pct` a partir do stop). Nenhum código novo de sizing. |

**Parâmetros livres: 4** (limite do catálogo é 5): `entry_period`, `exit_period`, `atr_multiple`, `er_min`. Constantes documentadas e **não** ajustáveis: janela do ER = `entry_period`; janela do ATR = 20. Sobra uma vaga, reservada ao filtro de volatilidade da Fase 3 (só entra se a ablação justificar).

**Faixas pré-declaradas** (escritas antes de qualquer varredura, para o pré-registro do Aronson):

| Parâmetro | Valores | Razão |
|---|---|---|
| `entry_period` | 20, 40, 80 | Dobrando, como Kaufman (p. 315) |
| `exit_period` | `entry_period / 2` (fixo pela regra, não varia livremente) | Mantém a razão do canal, reduz N |
| `atr_multiple` | 2, 3, 4 | k ≈ 3 é o do livro (p. 861) |
| `er_min` | 0 (desligado), 0,15, 0,25 | ER de 20 dias de séries reais fica tipicamente baixo; faixa a **calibrar nos dados antes** com a ferramenta de diagnóstico, sem olhar PnL |

Total: 3 × 3 × 3 = **27 configurações**, e N efetivo menor ainda (vizinhas são correlacionadas). Ordem de grandeza bem diferente das 6.402 do Aronson, o que ajuda.

## 4. O que já existe e o que falta

| Peça | Estado | Observação |
|---|---|---|
| Canal de rompimento e saída | ✅ | `donchian_breakout`. Esta estratégia estende a mesma lógica. |
| Razão de eficiência | ✅ | `efficiency_ratio` em `analytics/domain/regime.py`. A estratégia precisa de uma versão incremental sobre o histórico do estado (pequena). |
| ATR | ❌ | Não existe. Precisa de `true_range` e `atr` em `Decimal` (backlog B1). |
| Dimensionamento pelo stop | ✅ | `max_risk_per_trade_pct`, usado por bots e por backtests com `risk`. |
| Teste de entradas aleatórias, Sharpe real × backtest, sensibilidade à data inicial, escada de custos, quebras de regime, curva de exposição | ✅ | Feitos nos capítulos do livro 2. |
| Teste de truncamento (olhar para o futuro) | ✅ | Cobre toda estratégia do catálogo automaticamente. |
| Contagem de tentativas (universo) | ⚠️ | Existe `prior_runs` aproximado e `trials` da varredura; não há ledger formal por (par, intervalo, família). |
| Correção do melhor de N (permutação Monte Carlo) | ❌ | Aronson cap. 6 O1. Domínio público; o Reality Check de White é patenteado e **não** deve ser implementado sem decisão jurídica. |
| Métricas de perfil de tendência (ganho/perda, duração de vencedoras e perdedoras, sequências) | ❌ | Kaufman cap. 8 O1. |
| Sensibilidade a atraso de execução | ❌ | Kaufman cap. 8 O2. |
| Ablação de um clique | ❌ | Kaufman cap. 8 O7. |

## 5. Plano em fases

Cada fase só avança se a anterior passar. Nenhuma altera salvaguarda live.

**Fase 0, sem código de estratégia: ver se a hipótese tem chão.** Rodar `half-life`/Hurst/razão de variâncias e o ER dos pares candidatos (BTC/USDT, ETH/USDT) em 4h e 1d. Se a série for claramente de reversão em todos os prazos, **a hipótese cai antes de escrever código**. Registrar o resultado e a data.

**Fase 1, base: ATR + métricas de perfil.** `true_range`/`atr` em `Decimal` (função pura e testada); métricas de perfil de tendência no backtest (O1 do Kaufman cap. 8). Sem migração se as métricas forem derivadas ao exibir; com migração aditiva se forem gravadas, como foi feito com `excursion`.

**Fase 2, a estratégia mínima: rompimento + stop ATR, sem filtro.** `er_min = 0`. É o *baseline* que tudo mais precisa bater. Registrar no catálogo; o teste de truncamento e o de contrato a cobrem sozinhos.

**Fase 3, filtros, um de cada vez, por ablação.** (a) filtro de ER; (b) filtro de volatilidade alta ou baixa (Kaufman cap. 20 C8–C9: **adiar** a entrada em tendência, não eliminar). Cada um só fica se melhorar o *baseline* **fora da amostra**, em **mais de um** par e período, sem aumentar o número de parâmetros além de 5.

**Fase 4, validação pré-registrada (Aronson).**
1. Declarar as faixas da seção 3 **antes** (nota de análise no backtest, já existe).
2. Rodar a varredura de 27 configurações com `start_offset_days`.
3. Ler o resultado como **enviesado para cima**: mediana da grade, fração lucrativa, platô × pico (já existe), teste de entradas aleatórias da melhor (já existe).
4. Se se quiser um p-valor honesto do melhor de N: implementar o teste de permutação Monte Carlo (Aronson cap. 6 O1). Sem ele, **não afirmar significância**, só reportar a dispersão.
5. Deixar um trecho final sem tocar até a decisão (cap. 9 C7); ele é consumido uma vez.

**Fase 5, execução e paper.** Sensibilidade a atraso (Kaufman cap. 8 O2), paridade com o backtest (já existe), paper pelo prazo mínimo que o sistema já exige para live, e alerta de deterioração (já existe, livro 2 cap. 4). Só então se discute testnet/live, com `drawdown_action`, limite de exposição e as demais salvaguardas existentes.

## 6. Critérios para **abandonar** (definidos agora, para não racionalizar depois)

* Fase 0: série de reversão em todos os prazos testados.
* Fase 2: o *baseline* perde para comprar-e-segurar **e** para a mediana de entradas aleatórias (o teste existente) em ambos os pares.
* Fase 3: o filtro não melhora fora da amostra, ou melhora em um par e piora no outro. Nesse caso o filtro **não entra**.
* Fase 4: melhor configuração é pico isolado (vizinhas ruins), ou some ao se mover a data inicial.
* Qualquer fase: resultado bom **só** com custo zero. Se não sobrevive à escada de custos, não serve. Custo subestimado e custo superestimado são erros igualmente ruins (Kaufman cap. 1 C7), por isso a escada vai além do custo configurado.

## 7. Riscos e o que esta síntese **não** garante

* **Os dois livros não são sobre cripto.** O Kaufman mostra que índices de ações, mais ruidosos, tiveram o pior desempenho tendencial. Cripto pode estar em qualquer lado dessa escala; só a Fase 0 e os dados dizem.
* **Long-only perde metade da tendência** (a de baixa). O sistema fica fora do mercado nesses períodos, o que é uma redução de risco, mas também significa que, em mercado só lateral ou só de baixa, ele opera pouco ou nada. Isso é esperado, não falha.
* **O perfil de tendência é psicologicamente duro:** ~65% de operações perdedoras e séries longas de perdas são o normal (Kaufman p. 318). Se o operador não aguenta isso, a estratégia não serve a ele, independentemente do backtest.
* **O filtro de ER pode não ajudar**: no próprio livro o filtro piorou o Eurodólar. Está como hipótese, com critério de remoção.
* **Os resultados do Kaufman são de 1990–2011**, e o ER mostrou que o ruído dos índices subiu com a participação (cap. 1 C5). Vantagem de tendência pode ter encolhido.
* **O Aronson avisa que o mesmo histórico é reutilizado** (cap. 9 C8). Cada rodada sobre os mesmos dados de BTC consome um pouco do poder do teste; o ledger e o trecho final intocado só **limitam** isso, não eliminam.
* **Correlação com as estratégias que já existem:** `donchian_breakout` e `ema_crossover` são de tendência. Se esta nova for só um Donchian com stop ATR, ela se comporta quase como o Donchian que já há (N efetivo ≈ 1). A Fase 3 precisa mostrar **diferença real**.

## 8. Decisões que preciso de você

1. **Pares e prazo:** posso assumir BTC/USDT e ETH/USDT em 4h e 1d para a Fase 0?
2. **Fase 3 e o limite de 5 parâmetros:** a estratégia usa 4; o filtro de volatilidade seria o 5º. Aceita esse teto, ou prefere reservar a vaga?
3. **Permutação Monte Carlo do melhor de N** (Fase 4, item 4): implemento, ou ficamos só com a dispersão da grade e o teste de entradas aleatórias?
4. **Por onde começar:** Fase 0 (diagnóstico, sem código de estratégia) ou direto Fase 1 + 2?

## 9. Estado da implementação (2026-11-01)

* **Implementado:** a estratégia `trend_quality_breakout` (`strategies/domain/trend_quality_breakout.py`, registrada no catálogo) com os quatro parâmetros da seção 3 e valores padrão `entry_period = 40`, `exit_period = 20`, `atr_multiple = 3`, `er_min = 0`. Todo sinal de entrada leva stop a `atr_multiple` × ATR(20) abaixo do fechamento e nunca há alvo de lucro; sem stop quando ele ficaria não positivo. `true_range` e a razão de eficiência vivem no mesmo arquivo, porque o domínio de estratégias só importa de `strategies` e `market_data`. Testes: `test_trend_quality_breakout.py`, mais o contrato e o teste de truncamento, que cobrem a estratégia sozinhos. O contrato ganhou o conjunto `STOP_BY_DESIGN`: estratégias cujo stop faz parte do desenho podem emitir stop por padrão; as demais continuam sem stop.
* **O padrão de `er_min` é 0 de propósito:** a faixa 0,15–0,25 da seção 3 é palpite a calibrar nos dados (Fase 0), sem olhar PnL. Com 0, a estratégia é o baseline da Fase 2 (Donchian + stop em ATR).
* **Front-end:** nada a fazer; os formulários leem os parâmetros de `GET /strategies` e a família `trend` já tem as dicas existentes.
* **Não feito:**
  * **Fase 0 e a grade foram executadas** fora do banco, com candles da API pública da Binance: ver seção 10.
  * **Métricas de perfil de tendência, sensibilidade a atraso, ablação de um clique** (Fase 1/5): propostas do Kaufman cap. 8 O1, O2 e O7, ainda não construídas.
  * **Teste de permutação Monte Carlo do melhor de N** (Fase 4, item 4): não construído; sem ele não se afirma significância do melhor da grade, só a dispersão.
  * **Filtro de volatilidade** (Fase 3b) e a validação pré-registrada (Fase 4): dependem dos dados.

## 10. Resultado do backtest (2026-11-01)

**Método.** Candles de BTC/USDT e ETH/USDT em 1d e 4h baixados da API pública da Binance (2017-08-17 a 2026-11-01), executados com o **próprio motor do sistema** (`run_backtest`, preenchimento na abertura seguinte, taxa 0,1%, slippage 5 bps, caixa todo investido, sem o módulo de risco). O script de pesquisa ficou fora do repositório (descartável). Os candles não foram gravados no banco: para ver estes números na interface, é preciso reconstruir a imagem da API (`make up`), aplicar as migrações (`make migrate`) e importar os candles pela tela de dados.

* **Desenvolvimento:** 2017-08 a 2022-12. **Avaliação, consumida uma vez:** 2023-01 a 2026-11. A grade de 27 configurações da seção 3 foi rodada nos dois trechos, 4 séries (108 execuções por trecho). Nada foi ajustado depois de olhar a avaliação.

### Fase 0: a hipótese tem chão?

| Série (desenvolvimento) | Hurst | Razão de variâncias (lags 2/4/8) | Estacionária (5%) | ER de 40 (p25/p50/p75) |
|---|---|---|---|---|
| BTC 1d | 0,54 | 0,95 / 0,97 / 1,02 | não | 0,09 / 0,19 / 0,29 |
| BTC 4h | 0,50 | 0,95 / 0,94 / 0,96 | não | 0,07 / 0,16 / 0,27 |
| ETH 1d | 0,54 | 0,93 / 0,96 / 1,03 | não | 0,09 / 0,18 / 0,30 |
| ETH 4h | 0,51 | 0,95 / 0,96 / 0,97 | não | 0,07 / 0,16 / 0,26 |

Nenhuma série reverte à média. Em 1d há persistência fraca (Hurst 0,54); em 4h a série é indistinguível de passeio aleatório, com leve reversão nos lags curtos. A hipótese **não caiu**, mas é fraca, e mais fraca em 4h. O ER de 40 candles tem mediana perto de 0,18, então `er_min` de 0,15 e 0,25 correspondem a cortar cerca de 45% e 68% das barras.

### Desenvolvimento (2017–2022): parece ótimo

As 108 execuções foram lucrativas (retorno mediano de ~420% a ~970% contra ~290% de comprar-e-segurar), com Sharpe mediano de 0,8 a 1,2 e exposição de ~30% a 38% do tempo. Isso é exatamente o que o Aronson diz para desconfiar: o trecho tem o ciclo de 2020–21, e o melhor da grade é enviesado para cima.

### Avaliação (2023–2026): o que sobrou

| Série | Comprar-e-segurar (retorno / Sharpe / DD) | Baseline 40/20/3/0 (retorno / Sharpe / DD) | Entradas aleatórias: fração tão boa ou melhor |
|---|---|---|---|
| BTC 1d | 371% / 1,10 / 53% | 12% / 0,25 / 34% | 0,70 (nada melhor que o acaso) |
| BTC 4h | 371% / 1,12 / 53% | 209% / 1,24 / 30% | 0,09 |
| ETH 1d | 89% / 0,57 / 68% | 104% / 0,69 / 37% | 0,22 |
| ETH 4h | 89% / 0,58 / 68% | 33% / 0,39 / 46% | 0,44 |

* **A mediana da grade de 27 configurações na avaliação** teve Sharpe de 0,41 (BTC 1d), 1,04 (BTC 4h), 0,38 (ETH 1d) e 0,52 (ETH 4h). Lucrativas: 23, 27, 21 e 21 de 27.
* **O melhor do desenvolvimento não é o melhor na avaliação**: ficou nas posições 11, 16, 21 e 6 de 27. Mediana ~13,5, isto é, **a seleção do topo da grade não tem habilidade fora da amostra**. É o viés de seleção do Aronson, medido. A regressão foi forte: o melhor de BTC 1d fez 1.764% no desenvolvimento e 55% na avaliação.
* **O que a estratégia entrega de verdade é menos drawdown, não mais retorno**: drawdown de 30% a 46% contra 53% a 68% do ativo, ficando fora do mercado ~65% do tempo. Em BTC 1d ela perdeu feio para comprar-e-segurar (12% contra 371%); em BTC 4h e ETH 1d ficou à frente em Sharpe; em ETH 4h ficou atrás.

### Decisões que a grade já força

| Pergunta | Resultado | Decisão (critério da seção 6) |
|---|---|---|
| O filtro de ER (`er_min`) ajuda? | No desenvolvimento, `er_min` 0 ≥ 0,15 ≥ 0,25 em todas as séries (mediana de retorno e Sharpe). Na avaliação, **piora em 1d e melhora em 4h**: nenhum padrão consistente. | **Não entra.** Padrão continua `er_min = 0`. Fica como parâmetro, desligado. |
| Qual `atr_multiple`? | Pouca diferença no Sharpe mediano; 2 reduz drawdown em 1d, 4 piora em 4h. | Manter 3 (valor do livro); não há evidência para ajustar. |
| Qual `entry_period`? | 20 foi o melhor em 1d no desenvolvimento, 80 em 4h; **nenhum padrão se repete na avaliação**. | Manter 40/20 como referência. |
| Sobrevive à escada de custos? | Sim. BTC 1d, de custo zero a 3×: retorno de 1.512% a 1.142%, Sharpe 0,91 a 0,85. BTC 4h cai mais (5.025% → 1.241%) por ter 149 operações. | Passa; 4h é muito mais sensível ao custo. |
| Depende da data inicial? | BTC 1d, deslocando o início em 0–270 dias: retorno de 640% a 1.378%. | **Sensível:** o resultado de uma data inicial não representa a estratégia. |

### O perfil bate com o do Kaufman

Baseline 40/20/3/0, período todo: BTC 1d tem 29 operações, 45% de acerto, razão ganho/perda média de 2,43 (necessária para empatar: 1,23), vencedoras mantidas 82 barras e perdedoras 23, e no máximo 4 perdas seguidas. Em 4h: 36% de acerto, ganho/perda 2,76, até 8 perdas seguidas. É um perfil de seguidor de tendência (acerta pouco, ganha mais por acerto, segura vencedoras 3,5 a 4 vezes mais), como o livro descreve (pp. 317–320). Cuidado: com 27–29 operações em 1d, cada número tem muito ruído.

### Veredito

* **Não aprovada para dinheiro real.** Fora da amostra, a vantagem **não está demonstrada**: em BTC 1d ela não distingue de entradas aleatórias (p ≈ 0,70) e perdeu para comprar-e-segurar; em ETH 4h também ficou atrás; só BTC 4h e ETH 1d mostram Sharpe acima do ativo, e com 8% a 22% de chance de acaso. O desenvolvimento enganava.
* **O que parece real e robusto:** corte de drawdown (~35 a 40% menor), perfil de tendência saudável, custo suportável em 1d.
* **O que fica como evidência para o Aronson:** a dispersão entre os dois trechos, a falta de habilidade na seleção da grade e a sensibilidade à data inicial.
* **Próximos passos honestos:** paper de pelo menos o prazo exigido pelo sistema, em 1d (menos custo, menos ruído); rodar com o módulo de risco (`max_risk_per_trade_pct`) em vez de caixa todo investido, que é como o bot opera; e só então discutir testnet. Resultados de 2017–2022 não devem ser citados como expectativa.

### Com o módulo de risco (como o bot opera)

Baseline 40/20/3/0 com `max_risk_per_trade_pct` e stop obrigatório (a posição é dimensionada pelo stop em ATR, em vez de caixa todo investido):

| Série | Risco por operação | Desenvolvimento (retorno / Sharpe / DD) | Avaliação (retorno / Sharpe / DD) |
|---|---|---|---|
| BTC 1d | 1% | 62% / 0,85 / 16% | 2% / 0,17 / 5% |
| ETH 1d | 1% | 26% / 0,31 / 42% | 11% / 0,69 / 7% |
| BTC 4h | 1% | 123% / 1,33 / 14% | 68% / 1,52 / 11% |
| ETH 4h | 1% | 66% / 0,99 / 8% | 22% / 0,64 / 12% |
| BTC 4h | 2% | 261% / 0,87 / 56% | 132% / 1,42 / 20% |

Com 1% por operação o drawdown cai para 5%–16% na maioria dos casos, e o Sharpe fica na mesma ordem do caixa todo investido: o dimensionamento muda o **tamanho** do risco, não a existência da vantagem. A conclusão do veredito não muda: BTC 1d segue sem vantagem na avaliação (Sharpe 0,17). O drawdown de 42% de ETH 1d com 1% no desenvolvimento tem causa conhecida (investigada em 2026-11-01): o módulo de risco **pausou a execução em 2021-05-20 por "limite de perda diária" e, no backtest, a pausa nunca é retomada**; as 74 entradas seguintes foram recusadas e uma terceira por candle suspeito (amplitude de 26%). O resultado de ETH com risco de 1% é, portanto, só o trecho até a pausa mais uma posição aberta, e **não é comparável** com as outras linhas. Antes de usar o limite de perda diária num backtest longo, convém decidir se a pausa deve expirar no dia seguinte (como num bot real em que o operador retoma).

## 11. Bot e backtests no banco (2026-11-01)

* Imagens reconstruídas (`docker compose up -d --build`), migração `0020` aplicada, candles diários de BTC/USDT e ETH/USDT importados pela API (3.363 cada, 2017-08-17 a 2026-10-31).
* **Bot** `Trend quality BTC 1d (paper)` (id `500979eb-0c1a-4674-ac59-a97fcf1aa142`): `trend_quality_breakout` 40/20/3/0, BTC/USDT 1d, paper, risco de 1% por operação com stop obrigatório. **Criado parado**; nada foi iniciado.
* **Backtests** (BTC e ETH, 1d, período todo, capital de 10.000, taxa de 0,1%, slippage de 5 bps, divisão de teste em 2023-01-22, escada de custos ligada): um com caixa todo investido e um com risco de 1%. Estão na tela de backtests.

| Execução | Retorno | Comprar-e-segurar | Drawdown | Operações | Sharpe |
|---|---|---|---|---|---|
| BTC, caixa todo investido | 1.378% | 1.721% | 60% | 29 | 0,89 |
| BTC, risco 1% | 71% | 1.721% | 16% | 29 | 0,68 |
| ETH, caixa todo investido | 2.256% | 649% | 72% | 27 | 0,91 |
| ETH, risco 1% (pausado em 2021) | 50% | 649% | 42% | 8 | 0,31 |

Teste de entradas aleatórias do BTC (1.000 simulações): 10,8% das aleatórias fizeram tão bem ou melhor no período todo, o que não é significativo a 5%.

## 12. Melhorias e estudo com vários pares (2026-11-01)

**O que mudou no código**

* **Pausa por perda diária no backtest** (`resume_daily_pause`, migração `0021`, API e `docs/openapi.json`): com `risk`, a pausa por perda diária pode terminar no dia UTC seguinte, como um operador que retoma o bot toda manhã. Pausas por drawdown e por sequência de perdas **nunca** terminam sozinhas. Padrão desligado, então nada antigo muda. Testes em `test_execution_systems.py`.
* **Saída por ATR móvel** na `trend_quality_breakout` (`trail_atr_multiple`, quinto e último parâmetro, desligado por padrão): vende quando o fechamento fica `k` ATRs abaixo do maior fechamento desde a entrada. Só vende **antes** do canal, nunca depois. O pico é guardado no estado e sobrevive a reinício. Testes em `test_trend_quality_breakout.py`.
* **Triagem de tipo de par** na tela de dados (card de meia-vida): com o Hurst e a razão de variâncias de 8 candles, o par é marcado como favorável, desfavorável ou inconclusivo para seguir tendência (`lib/market-data/series-diagnostics.ts`). É descritivo; não bloqueia nada.

**Estudo com 15 pares** (BTC, ETH, BNB, XRP, ADA, DOGE, LTC, LINK, TRX, SOL, AVAX, DOT, ETC, ATOM e ETH/BTC), 1d, desenvolvimento antes de 2023 e avaliação depois, tudo declarado antes de olhar. Configurações fixas: baseline 40/20/3/0 (A) e com saída móvel de 2, 3 e 4 ATRs (T2, T3, T4), caixa todo investido.

| Medida na avaliação (2023–2026), 15 pares | A | T2 | T3 | T4 | Comprar-e-segurar |
|---|---|---|---|---|---|
| Sharpe mediano | 0,38 | 0,43 | 0,41 | 0,44 | 0,43 |
| Pares com Sharpe acima de comprar-e-segurar | 8 | 6 | 9 | 9 | – |
| Pares com drawdown menor que o do ativo | 15 | 14 | 15 | 15 | – |
| Drawdown mediano | 55% | 42% | 51% | 55% | 76% |

* **A estratégia, entre pares, é um redutor de drawdown:** em 15 de 15 pares o drawdown ficou abaixo do ativo (mediana 55% contra 76%), com Sharpe mediano parecido com o de comprar-e-segurar (0,38 contra 0,43). Não é uma máquina de retorno.
* **A saída móvel ajuda um pouco e de forma consistente nos dois trechos, mas pouco:** T3 melhora o Sharpe em 10 de 15 pares tanto no desenvolvimento quanto na avaliação, e reduz o drawdown em 11 de 15 na avaliação (15 de 15 no desenvolvimento). 10 de 15 não é significativo (p ≈ 0,15). T2, T3 e T4 dão medianas parecidas, o que é sinal de platô, não de pico. **Recomendo T3 para bots novos, sabendo que a evidência é fraca.** Padrão da estratégia continua desligado.
* **O tipo de par importa:** os pares cujo Hurst ≥ 0,5 e razão de variâncias de 8 candles ≥ 1 **antes de 2023** (BTC, ETH, BNB, DOGE, SOL, AVAX, ETC, ETH/BTC) tiveram Sharpe médio de 0,59 com T3 e vantagem de +0,10 sobre comprar-e-segurar; os outros sete tiveram 0,23 e −0,13. Correlação entre o Hurst do desenvolvimento e a vantagem na avaliação: 0,39; com a razão de variâncias, 0,43. Com 15 pares isso é **indício, não prova**, e é por isso que a triagem é só um aviso.
* **Pares pior com tendência neste estudo:** LTC (Sharpe −0,55 com T3), DOT e ATOM (perto de zero); XRP e LINK não vencem comprar-e-segurar. ETH/BTC (par relativo) teve Sharpe 0,36 com drawdown de 22%, ao contrário de 77% do ativo.

**No banco (candles diários de 15 pares importados; 39 backtests do estudo)**

| Par | A: Sharpe / DD | T3: Sharpe / DD | T3 com risco 1% e retomada diária: retorno / DD |
|---|---|---|---|
| BNB | 0,85 / 77% | 0,98 / 61% | 92% / 13% |
| SOL | 1,40 / 63% | 1,33 / 55% | 53% / 7% |
| AVAX | 1,06 / 72% | 1,18 / 58% | 50% / 16% |
| DOGE | 0,62 / 94% | 0,66 / 87% | 19% / 20% |
| LTC | 0,39 / 87% | 0,10 / 89% | 2% / 15% |
| XRP | 0,18 / 90% | 0,34 / 76% | 15% / 11% |

Período todo de cada par (dominado pelo desenvolvimento); a tabela completa está nas telas de backtests. Todos com divisão de teste em 2023-01-01.

**Bots no banco, todos em paper e parados:** `Trend quality BTC 1d (paper)` (agora com `trail_atr_multiple = 3`, config v2) e um bot para cada um de ETH, BNB, SOL, AVAX e DOGE com os mesmos parâmetros e risco de 1% por operação. Esses cinco passaram na triagem de par (Hurst ≥ 0,5 e razão de variâncias de 8 ≥ 1 antes de 2023). **Nenhum foi iniciado.**

**O que continua não feito:** a decisão de usar T3 como padrão, o teste de permutação Monte Carlo do melhor de N, a validação cruzada com purga, o filtro de volatilidade, um limite de exposição entre os bots (hoje cada bot arrisca 1% sem saber dos outros) e a avaliação de uma carteira desses pares como um todo.

## 13. Só USDT, capital realista e moedas com ícone (2026-11-01)

* **Regra do projeto:** o operador investe no máximo **1.000 USDT**, então os resultados precisam ser lidos em dólares. Por isso todo par é cotado em **USDT** (a API recusa outra cotação com 422 em backtests, bots e importações) e o backtest começa com **100 ou 1.000 USDT** (seletor no formulário; o padrão da API já era 1.000).
* **Todos os backtests anteriores foram apagados** a pedido (61 execuções, 5.070 operações e 1 varredura), junto com os candles de ETH/BTC. As tabelas das seções 10 a 12 ficam como **registro histórico** do estudo, feito com 10.000 de capital; o par ETH/BTC deixou de existir no banco. Os números relativos (Sharpe, drawdown, retorno em %) não dependem do capital, mas o valor em dólares sim: com 1.000 USDT, +100% é +1.000 USDT, não +10.000.
* **Seleção de moedas com ícone:** os formulários de bot, de backtest e de dados de mercado usam um seletor com os pares oferecidos por `GET /market-data/symbols` (14 pares USDT, lista curada em `market_data/domain/pairs.py`), e as listas de bots, backtests e dados mostram o ícone ao lado do par. Os ícones são SVG servidos pelo próprio app em `app/public/coins/` (sem depender de CDN externa, que quebraria sem rede e vazaria a navegação); se faltar o arquivo de uma moeda, aparece a inicial. Origem: pacote `@web3icons/core` (licença MIT), versão 4.0.58, arquivos `branded` das 14 moedas.
