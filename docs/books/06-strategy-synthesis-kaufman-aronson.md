# Síntese de estratégia · Kaufman (livro 4) + Aronson (livro 3)

Status: **Fases 1 e 2 implementadas (2026-11-01); Fases 0, 3, 4 e 5 dependem de dados e de rodar a validação.** Ver "Estado da implementação" ao final. Escrita em 2026-11-01 a partir dos relatórios de capítulo já feitos ([livro 4](04-trading-systems-and-methods-kaufman), [livro 3](03-evidence-based-technical-analysis-aronson)) e do código verificado nesta data. Páginas citadas são as dos livros, como nos relatórios. Tudo que é cripto é **adaptação nossa**: nenhum dos dois livros trata de cripto, e os resultados citados são de futuros e ações.

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
  * **Fase 0** (diagnóstico de BTC/ETH em 4h e 1d): precisa de candles importados, que não existem nesta máquina. É o próximo passo antes de qualquer varredura.
  * **Métricas de perfil de tendência, sensibilidade a atraso, ablação de um clique** (Fase 1/5): propostas do Kaufman cap. 8 O1, O2 e O7, ainda não construídas.
  * **Teste de permutação Monte Carlo do melhor de N** (Fase 4, item 4): não construído; sem ele não se afirma significância do melhor da grade, só a dispersão.
  * **Filtro de volatilidade** (Fase 3b) e a validação pré-registrada (Fase 4): dependem dos dados.
