# Livro 2 · Capítulo 8 — Gestão de risco

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 169–186 foi lido. Complementa [livro 1, cap. 6](../01-quantitative-trading-chan/ch06-money-and-risk-management.md).

## 1. Resumo do capítulo (pp. 169–186)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Objetivo: **maximizar o crescimento patrimonial no longo prazo**; evitar risco apenas quando prejudica esse objetivo. A aversão à perda (exigir cerca de US$ 2 de ganho para cada US$ 1 de perda, segundo Kahneman) explica por que Sharpe 2 parece bom, mas isso não é, por si só, racional. | Enquadrar o risco. | 169 |
| C2 | **Pressupostos da alavancagem ótima**: a distribuição futura dos retornos é igual à passada; versões mais estritas: distribuição da própria estratégia não muda; versão mais estrita: distribuição gaussiana. Alavancagem ótima pressupõe que não houve ruína histórica; limite de drawdown máximo torna-se uma restrição adicional. **A alavancagem deve permanecer constante**, o que significa vender após perdas e comprar após ganhos (exemplo 8.1: alavancagem 5, patrimônio 100 mil → 90 mil força venda até 450 mil). Essa venda após perdas foi apontada como causa de contágio na crise quantitativa de agosto de 2007. | Disciplina de alavancagem constante. | 170–171 |
| C3 | **Kelly** `f = m/σ²` (gaussiano). Superestimar a média ou subestimar a variância superestima a alavancagem e pode levar à ruína; subestimá-las só reduz o crescimento, por isso traders usam **meio Kelly**. Pela experiência do autor, Kelly é **limite superior**: o Kelly calculado pelo backtest frequentemente excede os limites da corretora ou teria levado a conta à ruína, pois os retornos não são gaussianos. Kelly de Russell 1000/2000 ≈ 1,8 ante ETFs 3×. Para várias estratégias: `F = C⁻¹M`; sob limite máximo de alavancagem, escalar todas igualmente não é ótimo. Exemplo 8.2 (duas estratégias, limite 2): todo o poder de compra na estratégia de maior crescimento dá g = 0,96, contra 0,82 com escala proporcional. | Dimensionamento. | 172–175 |
| C4 | **Otimização do crescimento por Monte Carlo**: `g(f) = ⟨log(1 + f·R)⟩` sobre retornos simulados por barra R, extraídos de uma distribuição do **sistema de Pearson** compatível com média, desvio-padrão, assimetria e curtose da estratégia; maximizar numericamente. Exemplo: Kelly 18,4, Monte Carlo ≈ 19, otimização histórica 18,4; alavancagem acima de 1/|pior retorno| (30,2) leva a −100%. Otimização direta dos retornos históricos sofre seleção de dados, embora neste exemplo concorde com os outros dois métodos. | Dimensionamento com caudas pesadas. | 175–178 |
| C5 | **Restrição de drawdown máximo**: não varia linearmente com alavancagem; ótimo irrestrito produz drawdown simulado de −99,9%; metade ainda produz −96,3%; é necessário reduzir a alavancagem cerca de sete vezes (para 2,7) para atingir −50%; retornos históricos exigiram divisão por apenas 1,5. Retornos simulados aumentam o poder estatístico, mas podem perder autocorrelação e representar eventos raríssimos; históricos capturam correlação, mas são poucos. **Sugere-se combinar os dois métodos**. Limites de alavancagem não garantem drawdowns futuros. | Orçamento de drawdown. | 179–180 |
| C6 | **CPPI** (seguro de carteira com proporção constante): reservar `D` (drawdown máximo permitido) como subconta de negociação e aplicar alavancagem Kelly `f` a ela; o resto permanece em caixa. **Repor a subconta até D do patrimônio total apenas quando houver nova máxima histórica, nunca após perdas**; se esgotada, retirar a estratégia (encerramento disciplinado). Na simulação do autor, crescimento igual ao de alavancagem fixa equivalente (0,002484 contra 0,002525 por dia), mas drawdown limitado abaixo de `D` (0,5 contra 0,9). Aplica-se a **uma estratégia por conta**; não protege contra lacunas nem interrupções de negociação. | Limitar drawdown sem abandonar crescimento. | 180–182 |
| C7 | **Stop de perda**: por posição versus por estratégia (este é incômodo e usado uma única vez; o autor prefere CPPI). Só funciona enquanto o mercado está aberto e há liquidez; pode falhar quando ela desaparece (cotações residuais no flash crash de 2010: stop de Accenture executado a US$ 0,01). Para estratégias de **reversão à média**, stops reduzem o desempenho do backtest, em parte por **viés de sobrevivência** (estratégias cujo regime mudou para tendência nunca entraram no catálogo). Recomendação: pôr o stop **além do maior drawdown intradiário do backtest**, sem acioná-lo no backtest e usando-o só para cisnes negros. Para **momentum**, o sinal oposto já funciona como stop, reduzindo o risco de cauda. | Usar stops com critério. | 182–184 |
| C8 | **Indicadores antecedentes de risco** (VIX, spread TED, HYG, MXN, ONN/OFF, fluxo de ordens): evitar proativamente períodos arriscados; dependem da estratégia (VIX > 35 *ajudou* compra na lacuna e *prejudicou* a estratégia FSTX de lacuna: Sharpe 1,4 → 0,16). Crises são raras, o que facilita selecionar dados nesses indicadores. | Evitar períodos desfavoráveis. | 184–186 |
| C9 | Conclusão: ainda há decisões de julgamento (reduzir alavancagem antes de evento conhecido: o autor diz que não se o modelo já resistiu a estresse anterior; distribuir Kelly **por estratégia** para que as piores sejam eliminadas, em vez de agrupar); divergências entre operação real e backtest muitas vezes vêm de mudanças de regime, não de falhas do backtest; hipótese → modelo → teste em dados não vistos. | Julgamento e regras. | 187–189 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Alavancagem constante/dimensionamento proporcional ao patrimônio | ✅ à vista | Entradas são dimensionadas como fração do **patrimônio atual do bot** (`equity * max_position_fraction` em `assess_signal`); o tamanho diminui após perdas e cresce após ganhos, sem rebalanceamento explícito. Alavancagem ≤ 1. |
| Kelly/otimização de crescimento por Monte Carlo | ❌ | Não se calcula `m/σ²`, `g(f)` ou otimização simulada. |
| Drawdown em função da exposição | ❌ | Não há análise da escala de drawdown conforme `max_position_fraction`. |
| Stops: ordens nativas na corretora durante operação real | ✅ | `trader.py:189-196`: “um stop colocado na corretora é a autoridade”. Paper/backtest usa modelo de execução na abertura após lacuna. |
| Regra de stop que não dispara no backtest | ❌ | `stop_loss_pct` é escolhido pelo usuário; não é comparado à pior excursão adversa do backtest. |
| Stop de drawdown por estratégia | ✅ | `max_drawdown_pct`, `max_daily_loss_pct`, `max_consecutive_losses` pausam o bot (`risk_management/domain/models.py`, `trader.py:550-568`). |
| Subconta no estilo CPPI | ⚠️ parcial | Cada bot é uma subconta virtual com capital próprio (`bot_portfolios`); a reconciliação exige que a conta da corretora tenha pelo menos a soma dos livros dos bots. Não há *ratchet* (elevar alocação em novas máximas, nunca após perdas) nem encerramento automático por orçamento de drawdown, além da pausa. |
| Alocação por estratégia em vez de conjunta | ✅ | Bots são independentes. |
| Indicadores antecedentes de risco | ❌ | Sem indicadores externos; a única proteção baseada no mercado é `max_candle_range_pct` na entrada. |
| Limites máximos de exposição | ✅ | `max_position_fraction`, `max_order_notional`, exposição global e limites da operação real. |

## 3. Oportunidades

### O1 — Curvas de crescimento e drawdown do backtest em função da exposição *(livro: C3–C5, pp. 172–180)*

* **Problema:** `max_position_fraction` é escolhido sem base quantitativa; os métodos do capítulo mostram como crescimento `g(f)` e drawdown variam com a exposição.
* **Proposta:** a partir dos retornos por barra do backtest, calcular para exposição `f ∈ (0, 1]` (limite 1 por ser à vista): (a) crescimento empírico `⟨log(1+f·R)⟩`; (b) drawdown máximo; (c) aviso se `f` exceder Kelly ou meio Kelly. Mostrar curva/tabela junto à fração configurada do bot. Começar pelos retornos históricos; acrescentar *bootstrap* dos retornos por barra como contraparte “simulada” (adaptação nossa: reamostragem dispensa o sistema de Pearson e preserva assimetria/curtose sem ajustar uma família, mas destrói autocorrelação, limitação também observada pelo livro para retornos simulados).
* **Benefício:** números concretos para dimensionamento e orçamento de drawdown, em vez de palpites. **Complexidade:** média (log-crescimento em `Decimal` ou conversão float documentada; bootstrap requer gerador aleatório com semente).
* **Riscos:** depende da qualidade da amostra (otimização histórica sujeita a seleção e simulações podem representar extremos nunca observados); retornos cripto são voláteis e autocorrelacionados. Um “ótimo” único incentiva excesso de confiança: mostrar faixa e tratar Kelly como limite superior, como o autor.
* **Validação:** reproduzir números do Exemplo 8.2 para o caso gaussiano; retornos sintéticos conhecidos cujo `g(f)` atinge o Kelly analítico; determinismo com semente; alavancagem acima de `1/|pior retorno|` resulta em ruína.

### O2 — Orçamento de risco por bot no estilo CPPI *(livro: C6, pp. 180–182 · adaptação às subcontas dos bots)*

* **Problema:** perdas do bot são limitadas apenas por pausas e limites; o livro propõe estrutura que limita drawdown por projeto e encerra estratégias em deterioração.
* **Proposta:** atribuir a cada bot um **orçamento de risco `D`** (fração do capital alocado que pode ser perdida). Só esse orçamento fica “em risco”; quando o patrimônio atinge nova máxima, recalcular o orçamento como `D` do patrimônio (ratchet); após perdas, não repor; se esgotado, parar o bot definitivamente com motivo claro e registro de auditoria. Em posição à vista comprada, o tamanho seria `exposure × budget`. Camada fina sobre `RiskLimits`, generalizando `max_drawdown_pct` de “pausar” para “encerrar com ratchet”.
* **Benefício:** perda máxima explicável e limitada por bot, com regra de fim de vida para estratégias que perdem a vantagem. **Complexidade:** média (estado de máxima histórica/orçamento atual; interação com reinício, alterações manuais de capital e aprovações para operação real).
* **Riscos:** lacunas podem ultrapassar orçamento (livro, p. 182); dimensionamento à vista já diminui com o patrimônio, portanto o ganho adicional é menor que no exemplo alavancado; lógica de ratchet pode ser implementada incorretamente; aplica-se apenas por bot (o livro alerta que contas agrupadas permitem vencedores subsidiarem perdedores). **Validação:** testes unitários determinísticos do ratchet e encerramento; teste de propriedade de que a perda realizada não excede o orçamento sem lacunas; sem mudança quando desativado.

### O3 — Posicionamento do stop em relação à excursão adversa do backtest *(livro: C7, pp. 183–184)*

* **Problema:** stop mais apertado que o drawdown normal da estratégia aciona em ruído comum e altera silenciosamente o backtest; para reversão à média, o livro recomenda colocá-lo além desse drawdown como proteção “apenas para cisnes negros”.
* **Proposta:** calcular a maior **excursão adversa** (pior perda não realizada dentro da operação) e compará-la com `stop_loss_pct`; avisar se o stop estiver dentro da excursão histórica e explicar cada família (momentum: stop faz parte do sinal; reversão: stop além da pior excursão). **Complexidade:** baixa a média (motor precisa registrar mínima durante a operação). **Validação:** operações sintéticas com excursões conhecidas.

### O4 — Atenção à falha de stops em cripto *(livro: C7, pp. 182–183 · adaptação)*

O livro mostra que stops podem executar a preços absurdos quando a liquidez desaparece; cripto tem eventos semelhantes. O sistema já usa stops nativos na corretora durante a operação real e dimensiona com slippage. Acrescentar alerta quando uma saída protetora executar muito além do preço planejado (requer registros de execução, livro 1, cap. 5 O4) e documentar política de tipos de ordem (stop-market versus stop-limit) e suas concessões. **Complexidade:** baixa a média. **Dependências:** livro 1, cap. 1 O1 (alertas) e cap. 5 O4.

### O5 — Dimensionamento por estratégia, sem Kelly agrupado *(livro: C9, p. 188)*

Confirma o projeto atual (bots independentes). Não desenvolver alocação conjunta por covariância; registrar como **não alteração** para evitar desvio futuro. Manter **B-PORTFOLIO** como possibilidade futura somente se bots compartilharem capital.

### O6 — Indicadores de risco: apenas exploratórios *(livro: C8, pp. 184–186 · adaptação)*

* Os indicadores do livro referem-se a ações/crédito. Candidatos cripto (volatilidade realizada geral, drawdown de BTC, taxas de financiamento) são ideias nossas, não do livro. Dado o alerta contra seleção de dados em crises raras, propor apenas uma etapa **descritiva**: mostrar desempenho da estratégia separado por regime de volatilidade pré-registrado (livro 2, cap. 5 O1), sem condicionar a negociação até validar fora da amostra. **Complexidade:** baixa. Registrar como **H-RISK-INDICATOR**.

### O7 — Documentar decisões de julgamento *(livro: C9, pp. 188–189)*

Documentar no runbook do operador as decisões mencionadas pelo autor: reduzir tamanho antes de eventos conhecidos, dimensionar por estratégia ou em conjunto e decidir quando encerrar um modelo. Apenas documentação. **Complexidade:** muito baixa.

### Não aplicável

Limites de alavancagem da corretora, exposição vendida e indicadores VIX/TED/HYG/ONN como apresentados.

## 4. Prioridade

| # | Item | Gestão de risco | Qualidade do backtest | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O3 stop versus excursão adversa | alta | média | – | baixa–média | mudança no motor |
| 2 | O1 curvas de exposição | alta | média | – | média | livro 1, cap. 2 O1 (série de retornos) |
| 3 | O2 orçamento CPPI | **alta** | – | média | média | O1 para escolher `D` e exposição |
| 4 | O4 alerta de falha de stop | média | – | média | baixa–média | livro 1, cap. 1 O1; cap. 5 O4 |
| 5 | O7 documentar políticas | média | – | – | muito baixa | – |
| 6 | O6 relatório descritivo por regime | baixa | média | – | baixa | livro 2, cap. 5 O1 |
| – | O5 | não alteração | | | | |

## 5. Arquivos afetados

`backtesting/domain/engine.py` (excursão adversa), `analytics/domain/` (crescimento/drawdown por exposição e bootstrap), `risk_management/domain/models.py`, `trading/application/trader.py` (apenas O2), `bots/domain/models.py` (estado do orçamento), migrações, `docs/openapi.json`, formulário de risco do bot e detalhes de backtest no app, runbook em `docs/` e testes.

## 6. Plano incremental

1. Métrica de excursão adversa e aviso sobre o stop.
2. Curvas de exposição, crescimento e drawdown (primeiro histórico, depois bootstrap).
3. Orçamento de risco CPPI opcional por bot; operar apenas em paper até comprovar.
4. Alerta de falha de stop com base nos registros de execução.
5. Documentação das políticas de julgamento.

## 7. Critérios de aceitação e testes

* Reproduzir os valores de Kelly, `g(f)` e alocação limitada do capítulo com os dados declarados pelo livro.
* Ratchet CPPI: orçamento só aumenta em nova máxima, nunca após perdas; encerramento ocorre quando se esgota; desativado, não tem efeito.
* Salvaguardas da operação real, kill switch e aprovações permanecem intactos; Ruff, mypy e testes existentes passam.
* A interface nunca apresenta exposição “ótima” calculada como recomendação sem ressalvas.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`; a exceção do bootstrap está na decisão pendente), números e dinheiro como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil, fronteiras entre módulos protegidas por `tests/unit/test_architecture.py`. A última migração é `0014_backtest_regime`. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| C3–C5 Kelly e crescimento (O1) | ❌ | ⚠️ **parcial**: `analytics/domain/sizing.py` calcula Kelly cheio e meio, taxa de crescimento `g(f)` **só nesses dois pontos** e o teto pela pior perda; `GET /backtests/{run_id}/sizing` e `components/backtests/sizing-card.tsx` (livro 1, cap. 6, Fase A). Falta a **curva** `g(f)` e o drawdown em função de `f` para `f ∈ (0, 1]`, e o bootstrap. |
| C6 CPPI (O2) | ⚠️ | ⚠️ continua: `RiskLimits.max_drawdown_pct` **pausa** o bot quando a queda a partir do pico passa do limite (`drawdown_breached`, `trader.py`, motivo `risk.drawdown_breached`), o que já é um *ratchet* implícito (o pico só sobe). A diferença para o livro é **encerrar de vez** em vez de pausar. |
| C7 stop × excursão adversa (O3) | ❌ | ❌ continua: nenhuma busca por excursão em `api/src` encontra algo. |
| C7 falha de stop (O4) | ❌ | ⚠️ as peças existem: registro de slippage e latência por ordem (livro 1, cap. 5) e `execution-quality`; falta o **alerta** (`AlertKind` não tem um para execução ruim). |
| C8 indicadores de risco (O6) | ❌ | ✅ descritivo: `analytics/domain/regime.py` mostra o desempenho por faixa de volatilidade (**H-RISK-INDICATOR**, sem condicionar negociação). Nada a fazer. |
| C9 julgamento documentado (O7) | ❌ | ❌ continua: `api/docs/operations/runbook.md` cobre servidor, chaves, backups e relógio, mas nada sobre decisões de julgamento. |
| Intervenções e motivo | ❌ | ✅ comandos e edições gravam autor e motivo; `GET /bots/{id}/interventions` (livro 1, cap. 8). Serve ao reinício de um bot encerrado (Fase D). |

**Achados que moldam o plano:**
* A excursão adversa **não precisa mudar o motor**: dá para calcular depois da execução com os fills já gravados e os candles armazenados (`min(low)` entre a entrada e a saída), como `periods.py` e `regime.py` são calculados fora do laço de eventos.
* O `sizing` hoje só lê `tail_risk` (barato, sem reler candles); a curva por exposição precisa dos **retornos por barra**, que dá para refazer a partir da curva de patrimônio já gravada em `backtest_runs.equity_curve` (JSONB).
* `RiskLimits` do bot são colunas em `bots`; qualquer campo novo (ação do drawdown) exige migração; os limites dos backtests ficam em JSONB e não.

### Fase A — Excursão adversa e aviso de stop (O3) · prioridade 1 · migração própria

* **A.1 Função pura** `analytics/domain/excursion.py`: `adverse_excursions(round_trips, candles) -> ExcursionReport | None`. Para cada operação completa (entrada e saída dos fills), a **maior queda não realizada** `(menor mínima entre entrada e saída ÷ preço de entrada − 1)` em %, como valor positivo; devolve `{trades, worst_pct, p95_pct, median_pct, worst_trades: [{entry_at, exit_at, pct}]}` (as 5 piores). Sem operações → `None`. `Decimal`, contexto de 40 dígitos; cálculo em `asyncio.to_thread` fora do laço.
* **A.2 Persistência:** coluna `excursion JSONB NULL` em `backtest_runs` (migração `NNNN_backtest_excursion`; `downgrade` remove; `alembic check`) pelo caminho do `regime`: `ports.py`, `orm.py`, `repository.py`, `service.py` (`_execute`), `router.py` (`ExcursionOut` em `BacktestOut`), OpenAPI. Execuções antigas ficam `null`.
* **A.3 Front-end:** `backtests.api.ts` (schema nullish); `components/backtests/excursion-card.tsx` em `backtest-detail-page.tsx` depois de `RiskReportCard`: a pior excursão, a mediana e as cinco piores operações. Em `lib/backtests/screening.ts`, flag `stop-inside-excursion` (`Warning`) quando `stop_loss_pct` de `strategy_params` é **menor** que a pior excursão (comparar com `compareDecimal`, sem aritmética): "este stop dispararia em oscilações que a própria estratégia já teve". O texto explica as duas famílias: em tendência, o stop faz parte do sinal; em reversão, o stop fica **além** da pior excursão, só contra cisne negro (p. 183–184).
* **A.4 Testes:** `tests/unit/test_excursion.py`: operações sintéticas com excursões conhecidas (valores à mão); operação que sobe sem cair → 0%; sem operações → `None`; ordem das piores. `vitest` da flag (stop dentro, stop fora, sem stop).
* **Aceite:** nenhum resultado de backtest muda (só se acrescenta o bloco); execuções antigas abrem sem o card.

### Fase B — Curvas de crescimento e drawdown por exposição (O1) · prioridade 2 · sem migração

* **B.1 Funções puras** em `analytics/domain/exposure.py`: `growth_curve(returns, fractions)` = `g(f) = média(ln(1 + f·r))` em `Decimal` (`ln` do contexto de 40 dígitos); `drawdown_at(returns, f)` refaz a curva com `1 + f·r` por barra e devolve o drawdown máximo; `ruin_fraction(worst_return)` = `1 ÷ |pior retorno|` (acima disso, ruína, p. 172). `fractions` = 20 passos entre 0 e 1 (**spot: nunca acima de 1**). Retornos por barra vêm de `periodic_returns` (`risk_ratios.py`), que já descarta lacunas e as conta.
* **B.2 Bootstrap com semente (a contraparte "simulada", adaptação nossa):** `bootstrap_drawdown(returns, f, simulations, seed)` reamostra retornos por barra com `random.Random(seed)` (com reposição) e devolve percentis (50º, 95º) do drawdown máximo. Reamostrar **destrói autocorrelação**, o que é dito na tela. Limites fixos no módulo (`MAX_BOOTSTRAP_RETURNS = 20_000`, `MAX_SIMULATIONS = 300`) porque cada simulação percorre a série em `Decimal`: acima disso, a série é **amostrada em blocos** ou a rota recusa (422). **Decisão pendente** (abaixo).
* **B.3 API:** `GET /api/v1/backtests/{run_id}/exposure-curve?steps=20&bootstrap=false&simulations=200&seed=0` em `backtesting/presentation/router.py`; `BacktestService.exposure_curve` lê a curva de patrimônio (`equity_curve(run_id)` já existe), calcula em `asyncio.to_thread`. Resposta `ExposureCurveOut`: `points: [{f, growth, max_drawdown_pct, bootstrap_p50?, bootstrap_p95?}]`, `kelly_full`, `kelly_half`, `configured_fraction`, `ruin_fraction`, `sample`, `warnings`. Erros: execução inexistente 404; ainda não concluída 409; sem curva (execução antiga) 409; `steps` ou `simulations` fora dos limites 422. Leitura para qualquer papel; sem auditoria.
* **B.4 Front-end:** `getExposureCurve` e schema em `lib/backtests/backtests.api.ts`, `QueryKey.Backtests.exposureCurve(id, steps, bootstrap, simulations, seed)`, hook em `use-backtests.ts`; dentro de `sizing-card.tsx`, um bloco "Curva por exposição": gráfico `recharts` (`f` × crescimento e `f` × drawdown) **com os números em tabela ao lado**, marcas de Kelly, meio Kelly e da fração configurada do bot; frase fixa "Kelly é um teto a ser descontado, nunca uma recomendação de aumentar a posição" e a faixa do bootstrap, nunca um "ótimo" único. Sem aritmética no app: tudo vem pronto e passa por `lib/shared/format.ts`. Esqueleto, erro com nova tentativa, vazio ("rode de novo para ver a curva"), dados; 360 px.
* **B.5 Testes:** `tests/unit/test_exposure.py`: retornos gaussianos sintéticos cujo `g(f)` máximo cai no Kelly analítico dentro de tolerância; reproduzir o **Exemplo 8.2** do livro com os dados declarados; `drawdown_at` cresce com `f`; `f` acima de `ruin_fraction` leva a perda total; bootstrap determinístico com a mesma semente; série curta → vazio com motivo. `tests/integration/test_exposure_curve.py`: forma da resposta, 404, 409 (execução sem curva), 422.
* **Aceite:** nenhum cálculo existente do `sizing` muda; a interface nunca apresenta um ponto "ótimo" como recomendação; tempo de resposta limitado pelos tetos.

### Fase C — Alerta de saída protetora muito pior que o plano (O4) · prioridade 3 · sem migração

* **C.1 Regra pura** em `notifications/application/conditions.py`: `protective_slippage(orders, limits)` → `Condition`s por bot quando uma saída protetora recente (ordem de stop ou take-profit já preenchida) tem slippage realizado acima de `alert_protective_slippage_multiple × slippage_bps configurado` do bot. Usa os campos que o registro de execução já grava (preço de referência, preço médio, slippage em bps). Chave estável por bot (sem contadores na mensagem).
* **C.2 Integração:** `AlertKind.PROTECTIVE_EXIT_SLIPPAGE`; o `evaluator.py` fornece as ordens recentes; novo `Settings.alert_protective_slippage_multiple` (padrão 3, **decisão pendente**) e `alert_protective_window_hours`. Severidade `WARNING`; nunca altera o bot.
* **C.3 Front-end:** rótulo em `lib/shared/labels.ts` e `AlertKind` em `lib/shared/enums.ts` (o `check:consistency` falha se faltar); nada além disso, porque `alerts-page.tsx` e `alerts-indicator.tsx` já listam por tipo.
* **C.4 Documentação (parte de O4):** em `api/docs/architecture/13-live-trading.md`, a política de **stop-market versus stop-limit** e o que cada um troca (garantia de saída × garantia de preço).
* **C.5 Testes:** `tests/unit/test_alert_conditions.py` (nome a conferir; ver `test_alert_episodes.py`): saída protetora dentro do múltiplo → nada; acima → condição; entrada ou saída sem ser protetora ignoradas; ordens antigas fora da janela; mensagem estável. Integração: o alerta abre e fecha.
* **Aceite:** nenhum bot muda de estado; o alerta fecha sozinho quando a condição some.

### Fase D — Encerrar em vez de pausar (O2, CPPI simplificado) · prioridade 4 · migração própria · **só em paper até comprovar**

Antes de codar, registrar a honestidade do desenho: o *ratchet* do CPPI **já existe** em `max_drawdown_pct` (queda a partir do pico, e o pico só sobe). O que falta é a ação **encerrar** e uma regra clara de reinício.

* **D.1 Domínio:** `RiskLimits.drawdown_action: DrawdownAction = PAUSE` (`StrEnum`: `pause`, `stop`) em `risk_management/domain/models.py`. `drawdown_breached` continua igual; o que muda é o que o trader faz com `risk.drawdown_breached`: com `stop`, leva o bot a `STOPPED` (`BotService.stop`, sem retomada automática) e grava a auditoria `risk.budget_exhausted` com o motivo. Hoje `risk.drawdown_breached` só impede novas entradas; **conferir em `trader.py` e `supervisor.py` o que acontece com o bot nesse caso** antes de escolher onde aplicar o `stop`.
* **D.2 Persistência e reinício:** coluna `drawdown_action TEXT NOT NULL DEFAULT 'pause'` em `bots` (migração `NNNN_drawdown_action`), mais `orm.py`, `repository.py`, `schemas.py`, OpenAPI. Reiniciar um bot encerrado por orçamento usa o `BotService.start` existente, mas **com motivo obrigatório** nesse caso (livro 1, cap. 8, Fase 1 já grava motivo e autor) e **recalibra o pico** para o patrimônio atual (novo orçamento); isso é uma intervenção contada. **Bots live:** a ação `stop` vale também, mas **nada nesta fase enfraquece as salvaguardas live**; aprovação e kill switch ficam como estão.
* **D.3 Front-end:** campo "Ao atingir o drawdown máximo" (Pausar / Encerrar) no bloco de risco de `lib/bots/form.ts` e `bot-form-page.tsx`, texto de apoio ("encerrar exige reinício manual com motivo; lacunas podem ultrapassar o limite, p. 182"); `bots.api.ts`; o estado `stopped` já existe no enum `BotState`. `api:types` e `check:consistency`.
* **D.4 Testes:** `tests/unit/test_risk_and_stops.py` e novo `test_drawdown_action.py`: com `pause`, tudo igual ao atual (regressão); com `stop`, o bot termina e audita; o pico só sobe; sem lacuna, a perda realizada não passa do orçamento; reinício recalibra o pico e exige motivo. Integração em `test_phase2_paper.py`-style com bot paper.
* **Aceite:** com o padrão `pause`, nenhum teste existente muda; só ativável por escolha explícita; **não ativar em live até ter rodado em paper por um tempo**.

### Fase E — Documentar decisões de julgamento (O7) · prioridade 5 · só documentação

Nova seção em `api/docs/operations/runbook.md` ("Decisões de julgamento do operador"): (1) reduzir tamanho antes de eventos conhecidos, **só se o modelo não resistiu a estresse parecido** (o autor recomenda não fazer se resistiu; postura inicial conservadora); (2) dimensionar por estratégia, não em conjunto (por isso os bots são independentes); (3) quando encerrar um modelo (monitor do [cap. 4, Fase B](ch04-mean-reversion-stocks-etfs.md) e a nota de análise da Fase A); (4) a deterioração costuma ser **mudança de regime**, não erro de backtest. Referenciar `app/docs/07-ux-rules.md` quando tocar a UI. Mesmo texto resumido na tela de Status? **Decisão pendente.**

### Estado da implementação (2026-11-01)

* **Fase A implementada** (migração `0019_backtest_excursion`): `analytics/domain/excursion.py` calcula, depois da execução e sem mexer no motor, a maior queda abaixo do preço de entrada de cada operação (mediana, 95º percentil, pior e as 5 piores), gravada em `excursion`. O app mostra o card e a flag `stop-inside-excursion` quando o `stop_loss_pct` é menor que a pior excursão. Testes: `test_excursion.py` e integração.
* **Fase B implementada** (sem migração): `analytics/domain/exposure.py` (crescimento `mean(ln(1 + f·r))`, drawdown máximo, fração de ruína, bootstrap semeado) e `GET /backtests/{id}/exposure-curve`. **Tetos do bootstrap adotados:** 5.000 retornos (os últimos) e 100 simulações, em `Decimal`; o resto fica de fora, e a resposta diz quantos retornos entraram. O app tem o bloco "Curva por exposição" dentro do card de dimensionamento, com dois gráficos e a tabela com os números. O ótimo nunca é apresentado como recomendação. Testes: `test_exposure.py` (inclui o ótimo exato de um retorno de dois pontos) e integração.
* **Fase C implementada** (sem migração): alerta `protective_exit_slippage` (`notifications/application/conditions.py::protective_slippage`) quando um stop nativo preenche mais de `ALERT_PROTECTIVE_SLIPPAGE_MULTIPLE` vezes pior que o slippage do bot (padrão 3×, piso de 10 bps), numa janela de `ALERT_PROTECTIVE_WINDOW_HOURS` (24 h); crítico em bot live, aviso nos demais; nunca altera o bot. **Só ordens `stop_loss` nativas** (testnet e live) são vigiadas; o stop do paper não é uma ordem separada. A política stop-market × stop-limit está em `api/docs/architecture/13-live-trading.md`. Testes: `test_protective_slippage.py`.
* **Fase D implementada** (migração `0020_drawdown_action`): `RiskLimits.drawdown_action` (`pause`, padrão, ou `stop`). Com `stop` e `max_drawdown_pct` atingido, o trader põe o bot em `stopped` (o supervisor encerra a sessão) e grava `risk.drawdown_breached` e `risk.budget_exhausted` com a ação; a posição é mantida. **Desvio do plano:** o "pico" do drawdown já é derivado dos snapshots do bot (o *ratchet* implícito), então **não há estado novo**; para começar de novo, reiniciar exige `reset-portfolio` com motivo (que zera o pico), e isso já conta como intervenção. Não há recalibração automática de pico nem motivo obrigatório novo em `start`. Campo no formulário do bot e na aba de configuração. Nenhuma salvaguarda live muda; recomendo usar `stop` primeiro em paper. Testes: integração (`stop` e `pause`).
* **Fase E implementada** (só documentação): seção 8 do [runbook](../../../api/docs/operations/runbook.md).
* **Decisões adotadas:** múltiplo 3× e janela 24 h; tetos do bootstrap acima; `stop` permitido em qualquer modo, por escolha explícita.

### Ordem, dependências e estimativa

A → B (a mesma tela de execução); C depende do registro de execução (já existe); D só depois de A e B (para escolher o limite com base) e **só em paper**; E é independente. Estimativa grosseira: A ≈ 2,5 dias (1,5 back, 1 front); B ≈ 4 (2,5 back, 1,5 front); C ≈ 1,5; D ≈ 3 (2 back, 1 front); E ≈ 0,5. Migrações: A e D (duas), B e C não mexem no banco.

### Decisões pendentes (para o operador)

* Bootstrap: aceitar os tetos (20.000 retornos, 300 simulações) ou amostrar em blocos; e se vale **uma** conversão `float` isolada para acelerar (proposta: ficar em `Decimal` e recusar acima do teto).
* Múltiplo do alerta de slippage de saída protetora (proposta: 3×) e a janela (proposta: 24 h).
* Se `drawdown_action = stop` pode ser usado em live depois de comprovado em paper (proposta: sim, por escolha explícita e com motivo no reinício).
* Se a seção de julgamento também aparece na tela de Status.

### Fora do escopo (decidido)

Kelly agrupado por covariância (**B-PORTFOLIO**, só se bots passarem a dividir capital), indicadores VIX/TED/HYG/ONN, limites de alavancagem da corretora, exposição vendida e qualquer condicionamento da negociação por indicador de risco antes de validar fora da amostra (**H-RISK-INDICATOR** continua descritivo).

### Critérios de aceite gerais

Nenhuma salvaguarda live, kill switch ou aprovação é enfraquecida; nada é aplicado automaticamente; o app nunca mostra "exposição ótima" sem ressalva; nenhum `float` no domínio (salvo a decisão acima, se aprovada); `make check`, integração com `alembic upgrade head` e `downgrade -1` em banco com dados, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas em 1366 px e 360 px. Os números de Kelly e drawdown do livro são de uma estratégia semelhante a futuros com exposição de 18× e não descrevem cripto à vista.

## Ressalvas

Todos os números de Kelly, Monte Carlo e drawdown referem-se a uma estratégia semelhante a futuros com exposição de 18× (estratégia do Exemplo 5.1) e não descrevem cripto à vista. O autor afirma que Kelly é limite superior, a hipótese gaussiana não é confiável, limites de alavancagem não garantem drawdown futuro e CPPI não protege contra lacunas (pp. 172, 179, 182). Retornos passados não garantem comportamento futuro.
