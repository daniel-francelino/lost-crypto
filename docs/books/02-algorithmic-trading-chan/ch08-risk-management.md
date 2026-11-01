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

## Ressalvas

Todos os números de Kelly, Monte Carlo e drawdown referem-se a uma estratégia semelhante a futuros com exposição de 18× (estratégia do Exemplo 5.1) e não descrevem cripto à vista. O autor afirma que Kelly é limite superior, a hipótese gaussiana não é confiável, limites de alavancagem não garantem drawdown futuro e CPPI não protege contra lacunas (pp. 172, 179, 182). Retornos passados não garantem comportamento futuro.
