# Livro 1 · Capítulo 6 — Gestão de dinheiro e de risco

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **análise + plano de implementação detalhado (2026-11-01); nada foi implementado**. O diagnóstico foi revisado contra o código depois da implementação dos Caps. 2–5 e dos alertas (ver §2.1). Quem for implementar deve ler o §8.

## 1. Resumo do capítulo (pp. 95–113)

O capítulo segue o tratamento de E. Thorp para o critério de Kelly. Chan o aplica a uma carteira de *estratégias*.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Objetivo: maximizar o crescimento composto de longo prazo**, o que exige evitar a ruína (se a ruína tem probabilidade diferente de zero, a riqueza de longo prazo é zero). Assume retornos gaussianos com média e desvio-padrão fixos, líquidos de custos de financiamento (retornos em excesso); o autor afirma que isso é grosseiro e pode ser impreciso. | O que significa "ótimo". | 96 |
| C2 | **Alocação de Kelly:** `F = C⁻¹ M` (C = matriz de covariância dos retornos em excesso simples, sem alavancagem, de um período; M = retornos médios). Para estratégias independentes: **`fᵢ = mᵢ / sᵢ²`**. O `f` de Kelly não depende da escala de tempo (entradas anuais ou diárias dão o mesmo `f`). | Quanto capital e alavancagem por estratégia. | 96–97, 99 |
| C3 | **Taxa de crescimento:** para uma estratégia `g(f) = r + f·m − s²·f²/2`; com `f = 1`, `r = 0`, `m = 0` isso dá `g = −s²/2` (Exemplo 6.1: um passeio aleatório de ±1% por minuto perde 0,5 bp por minuto embora o retorno médio seja zero). No ótimo, `g = r + S²/2` com S o índice de Sharpe; multiestratégia: `g = r + FᵀCF/2`, `S = √(FᵀCF)`. Lição: **o risco sempre reduz o crescimento de longo prazo.** | Por que a gestão de risco não é opcional. | 97–98, 102, 112–113 |
| C4 | **Exemplos trabalhados:** SPY: média 11,23%, desvio-padrão 16,91%, livre de risco 4% → Sharpe 0,4275, alavancagem de Kelly 2,528, crescimento 13,14% (sem alavancagem 9,8%). Três ETFs: F = (1,29, 1,17, −1,49), crescimento 15,29%, Sharpe 0,4751. | Referência numérica para testes. | 99–102 |
| C5 | **Half-Kelly** é comum porque as entradas são incertas e os retornos não são gaussianos. Se a alavancagem da corretora é limitada em *l*, escalar cada `fᵢ` por `l / Σ|fᵢ|`. | Erro de estimação e limites. | 98 |
| C6 | **Rebalancear conforme o patrimônio muda:** após uma perda, Kelly diz para *reduzir* a exposição (exemplo do livro com SPY: uma perda de 10% numa carteira 2,528× implica cortar para 2,528 × novo patrimônio); após ganhos, aumentar. Atualizar ao menos diariamente; reestimar `F*` a partir de uma janela móvel (regra prática: **seis meses para estratégias que seguram cerca de um dia**) — uma janela curta também permite descontinuar estratégias que perdem a vantagem. Para números variáveis de posições, usar Kelly para definir o número/capital máximo. Sempre é mais seguro ficar abaixo de Kelly. | Controle de risco contínuo. | 102–103 |
| C7 | **Gestão de risco significa vender com prejuízo**; em escala causa contágio (as perdas quant de agosto de 2007 são descritas). O half-Kelly reduz quanto precisa ser vendido. | Custo de reduzir risco. | 103–105 |
| C8 | **Caudas gordas:** estimar a **maior perda histórica em um período** por backtest, dividir a queda de patrimônio máxima tolerável em um período por ela e usar **o menor entre half-Kelly e essa alavancagem**. Exemplo do S&P: pior dia −20,47% (19 out 1987); com tolerância de 20%, alavancagem máxima ≈ 1 contra half-Kelly 1,26. Eventos realmente sem precedentes não podem ser modelados. | Cisnes negros. | 105–106 |
| C9 | **Stop-loss não é proteção universal** (quadro lateral): numa lacuna (gap) catastrófica o stop executa muito abaixo; stops ajudam só em regime de momentum/tendência e prejudicam em regime de reversão à média; movimentos com notícia tendem a ser momentum, movimentos sem notícia aparente tendem a ser eventos de liquidez que revertem. Observação do autor, não prova. | Uso indevido de stops. | 106–107 |
| C10 | **Outros riscos, em ordem decrescente de probabilidade:** *risco de modelo* (vieses, erros, concorrência, mudança de regime; **peça a um colaborador que replique seu backtest de forma independente**; mitigar reduzindo a alavancagem gradualmente conforme perde, via Kelly móvel, em vez de desligar de repente), *risco de software* (comparar operações live com as do backtest), *risco de desastre natural* (Internet/energia; ver Cap. 4). | Riscos não de mercado. | 107–108 |
| C11 | **Psicologia:** aversão à perda/viés de status quo (segurar perdedoras, fechar vencedoras cedo demais; **sair imediatamente de uma posição errada**), viés de representatividade (reajustar após uma perda → qualquer mudança deve ser testada num período longo), desespero (desligar ou dobrar a aposta) e ganância (alavancar após boas fases). A regra de ouro: **manter o tamanho da carteira sob controle o tempo todo**; começar pequeno e crescer. LTCM e Amaranth são citados como falhas por excesso de alavancagem. | Intervenção humana. | 108–111 |
| C12 | O excesso de alavancagem atinge mais os melhores desempenhos recentes (excesso de confiança). | – | 111–112 |

O capítulo assume ações, futuros e alavancagem de corretora. As observações sobre cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C1/C2 Kelly ou qualquer dimensionamento ótimo de crescimento | ❌ | Sem Kelly nem dimensionamento por volatilidade. O tamanho é `max_position_fraction` do patrimônio, opcionalmente limitado por `max_order_notional` e por `max_risk_per_trade_pct` quando o sinal traz um stop (`risk_management/domain/models.py::assess_signal`). |
| Alavancagem | n/a | Spot long-only: alavancagem efetiva ≤ 1 (`max_position_fraction ∈ (0,1]`). Um Kelly `f > 1` não é utilizável; `f < 1` seria informativo. |
| C3 crescimento/ruína | ❌ | Nenhuma estimativa de taxa de crescimento ou probabilidade de ruína em qualquer relatório. |
| C5 half-Kelly / dimensionamento conservador | ⚠️ | Conservador por padrão apenas pela fração escolhida pelo usuário. |
| C6 redução dinâmica de risco | ❌ | Apenas controles binários: `max_daily_loss_pct`, `max_drawdown_pct` e `max_consecutive_losses` **pausam** o bot (desligamento abrupto, o comportamento que C10 desaconselha); sem redução gradual de tamanho conforme o desempenho decai. Violações de perda diária e drawdown são checadas em `daily_loss_breached` / `drawdown_breached`. |
| C8 pior perda histórica de um período vs. tolerância | ❌ | `max_drawdown_pct` é um limiar de pausa em tempo de execução, sem relação com a pior perda histórica de um período do par negociado. |
| C9 stops | ⚠️ | Os stops existem e executam com a regra de gap-through-stop na abertura (mais conservadora que executar no stop, coerente com o quadro lateral), tanto no backtest quanto no paper (`risk_management/domain/stops.py`). Nada liga a escolha do stop ao regime da estratégia (tendência vs. reversão à média). |
| C10 risco de modelo: replicação independente | ❌ | Os backtests são reproduzíveis (`seed`, SHA-256 dos candles), mas não há segunda implementação independente nem checagem cruzada. |
| C10 risco de software | ❌ | Mesma lacuna do capítulo 5 (sem relatório de paridade). |
| C10 risco de desastre | ⚠️ | O reconciler trata quedas; sem plano de continuidade documentado (capítulo 4). |
| C11 disciplina de intervenção | ⚠️ | O kill switch e os controles são auditados; nenhum motivo registrado (capítulo 1). Edições de estratégia após perdas não têm trava; os parâmetros de estratégia de um bot podem ser editados (o app tem uma página de edição), mas nada exige antes uma comparação por backtest. |
| C11 "sair de posições erradas" | ✅ | Saídas são sempre permitidas, mesmo com o kill switch ligado. |
| Proteção contra excesso de alavancagem | ✅ | Limites live definidos pelo operador (`LiveLimits`), exposição global e limites de posições abertas. |

### 2.1 O que mudou desde a versão anterior deste relatório (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| Métricas de risco ajustado (C3, pré-requisito de Kelly) | ❌ | ✅ `analytics/domain/risk_ratios.py`: Sharpe, Sortino, information ratio, volatilidade e retorno anualizados (365 dias), `periodic_returns` (descarta passos que cruzam lacunas e os conta) e mínimo de 30 retornos (`MIN_RETURNS`). A taxa de crescimento `g` e o Kelly **continuam ausentes** (busca por `kelly` no `api/src`: nada). |
| Drawdown | só profundidade | ✅ profundidade, duração, pico, vale, aberto ou recuperado (`Metrics`), tolerância do operador em profundidade e dias (`BacktestConfig.max_drawdown_tolerance_*`). **Não existe** a pior perda de **um período** (C8). |
| Backtest com o risco do bot (C6/C10) | ❌ | ✅ `BacktestConfig.risk` + `_RiskGuard` em `backtesting/domain/engine.py`: mesmo `assess_signal`, mesmas pausas (perda diária, drawdown, perdas seguidas). Qualquer mudança em `assess_signal` ou em `RiskLimits` vale para trader, backtest e replay de paridade ao mesmo tempo, **mas o estado** (por exemplo uma janela de retornos) precisa ser alimentado nos dois lugares. |
| Risco de software (C10) | ❌ | ✅ relatório de paridade bot × backtest e aba "Diagnóstico" (Cap. 5). |
| Teste de look-ahead (C10, risco de modelo) | ❌ | ✅ `tests/unit/test_lookahead.py` roda em toda estratégia do catálogo. |
| Desastre/continuidade (C10) | ⚠️ | ✅ runbook, backup com restauração testada, healthcheck externo (Cap. 4). |
| Limite de volume e escala | ❌ | ✅ `RiskLimits.max_order_pct_of_volume` (Cap. 5). |
| Replicação **independente** do backtest (C10) | ❌ | ❌ continua: a paridade compara bot × backtest com o **mesmo** motor; não há segunda implementação. |
| Dimensionamento por Kelly, pior perda por período, metadados de regime da estratégia | ❌ | ❌ continuam. |
| Disciplina de intervenção (C11) | ⚠️ | ⚠️ continua: `bot.*_requested` grava payload `{}` e `bot.config_updated` grava só `fields` e `version` (`bots/application/service.py`). **Correção:** o texto antigo falava em editar "um bot em execução"; `Bot.ensure_editable()` só deixa editar com o bot **parado**. |

Também corrigi um erro do plano antigo: o Exemplo 6.3 do livro (três ETFs, `F = C⁻¹M`) exige matriz de covariância e pertence à alocação multiestratégia (adiada); a validação do Kelly usa só os Exemplos 6.1 e 6.2.

## 3. Oportunidades

### O1 — Dimensionamento de referência Kelly/volatilidade como **conselho, não auto-trading** *(livro: C2, C3, C5, pp. 96–99 · a aplicação a cripto é adaptação nossa)*
* **Problema:** o operador escolhe `max_position_fraction` às cegas; o resultado central do livro diz que existe uma exposição ótima que depende da vantagem e da volatilidade, e que o próprio risco custa crescimento.
* **Proposta:** a partir dos retornos periódicos de um backtest, calcular `m`, `s`, o Kelly `f = m/s²` e o half-Kelly; mostrá-los (junto com o tamanho da amostra e o aviso de que as estimativas são ruidosas) ao lado da fração configurada. Limitar qualquer sugestão a 1 (spot). **Não** aplicar automaticamente na primeira iteração.
* **Benefício:** dimensionamento informado e um aviso visível quando a fração escolhida está acima de Kelly (mais risco, menos crescimento, conforme C3).
* **Complexidade:** baixa (funções puras, tudo em `Decimal`, testáveis contra os exemplos de SPY e dos três ETFs do livro).
* **Riscos:** `m` é difícil de estimar; poucos meses bons produzem um `f` grande; a hipótese gaussiana falha em cripto (caudas gordas), então usar no máximo half-Kelly e preferir o limite de C8; um Kelly dentro da amostra é tão sobreajustado quanto o backtest.
* **Validação:** reproduzir o Exemplo 6.1 (`g = −s²/2`) e o Exemplo 6.2 (f = 2,528, g = 13,14%, g sem alavancagem = 9,8%) em testes unitários. O Exemplo 6.3 (três ETFs) fica de fora: precisa de covariância entre estratégias (ver "Não aplicável / adiado").

### O2 — Limite de alavancagem sensível à cauda a partir da pior perda histórica de um período *(livro: C8, pp. 105–106)*
* **Proposta:** reportar, por backtest e por par/timeframe, a maior perda em um período e calcular `max_fraction = perda tolerável de patrimônio em um período / pior perda histórica`. Sugerir `min(half-Kelly, max_fraction, 1)` como teto de exposição. O operador informa a perda tolerável.
* **Benefício:** liga o tamanho da posição ao pior movimento observado. **Complexidade:** baixa. **Risco:** o histórico pode não conter o pior evento (o livro diz isso). **Validação:** testes unitários com um crash na série.

### O3 — Redução gradual de risco em vez de apenas pausar *(livro: C6, C10, pp. 103, 107)*
* **Proposta:** um modo de risco opcional que escala `max_position_fraction` por um fator de desempenho móvel (por exemplo half-Kelly móvel limitado a [0, fração configurada]) para que uma estratégia em decaimento encolha suavemente até zero. Manter as pausas rígidas existentes como retaguarda.
* **Benefício:** evita tanto o desligamento abrupto no pior momento quanto dobrar a aposta. **Complexidade:** média (precisa de uma janela de retornos móvel no estado do bot e de regra de rebalanceamento para uma posição já aberta, já que o spot long-only só pode mudar o tamanho nas entradas). **Risco:** janelas móveis são ruidosas e podem travar o bot em zero; whipsaw; só se aplica a novas entradas, a menos que saídas parciais sejam adicionadas. **Validação:** séries de patrimônio simuladas com vantagem em decaimento devem mostrar frações decrescentes; testes unitários determinísticos.

### O4 — Política de stop por regime *(livro: C9, pp. 106–107; mais fundo no Cap. 7)*
* **Proposta:** registrar nos metadados de cada estratégia se ela é seguidora de tendência ou de reversão à média, e avisar quando um stop curto for combinado com uma estratégia de reversão à média (e quando uma estratégia de tendência não tiver stop). As estratégias existentes (cruzamento de EMAs, rompimento de Donchian) são de tendência/rompimento. **Complexidade:** baixa. **Risco:** o argumento do capítulo é observação do autor; apresentar como orientação, não como regra. Revisitar com o Capítulo 7 (saídas).

### O5 — Replicação independente dos backtests *(livro: C10, p. 107)*
* **Proposta:** uma pequena implementação de referência vetorizada e independente (outro caminho de código, por exemplo na suíte de testes) que reproduza as principais saídas de backtest das estratégias entregues em fixtures fixas; qualquer diferença reprova os testes. Aproximação barata do "colaborador" que o livro recomenda. **Complexidade:** média. **Validação:** ela mesma é a validação.

### O6 — Travas de disciplina em edições de parâmetros *(livro: C11, pp. 109–110 · adaptação)*
* **Proposta:** ao editar a configuração de um bot (só é possível com ele **parado**), mostrar o que muda, oferecer o backtest com a configuração nova e pedir um motivo (liga com o Capítulo 1 O3); registrar tudo na auditoria. Não bloquear. **Complexidade:** baixa–média. **Risco:** atrito ignorado por hábito. **A especificação detalhada está no [Cap. 8, §8](ch08-conclusion.md)**, que reúne as travas de disciplina dos Caps. 1, 6 e 8.

### O7 — Resumo de ruína/exposição para o operador *(livro: C1, C3, C11)*
* **Proposta:** visão de carteira mostrando a exposição atual vs. a referência de Kelly vs. os limites live, de modo que "manter o tamanho da carteira sob controle o tempo todo" seja observável. Depende de O1/O2. **Complexidade:** baixa.

### Não aplicável / adiado
Alocação multiestratégia por covariância `F = C⁻¹M` (um único pool, bots independentes; revisitar quando várias estratégias compartilharem capital), escalonamento de alavancagem da corretora (sem alavancagem), discussão de contágio, anedotas de Amaranth/LTCM (só ilustrações).

## 4. Prioridade

| # | Item | Gestão de risco | Confiabilidade | Qualidade do backtest | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O2 limite pela pior perda de período | **alta** | – | – | baixa | métricas (capítulo 2) |
| 2 | O1 referência Kelly (conselho) | alta | – | média | baixa | Sharpe/série de retornos |
| 3 | O5 replicação independente | média | **alta** | alta | média | – |
| 4 | O7 resumo de exposição | média | – | – | baixa | O1, O2 |
| 5 | O6 trava de edição de parâmetros | média | média | – | baixa–média | capítulo 1 O3 |
| 6 | O4 dica de stop por regime | baixa | – | – | baixa | metadados de estratégia |
| 7 | O3 redução gradual de risco | alta | – | – | média | O1; desenho separado |

## 5. Arquivos afetados
`analytics/domain/` (novas funções puras: série de retornos, Kelly, pior perda de período), `analytics/presentation/schemas.py`, `backtesting/application/service.py` e `router.py` (campos aditivos), `risk_management/domain/models.py` (apenas para O3), `strategies/domain/base.py` (metadados para O4), `bots/application/service.py` (O6), testes em `api/tests/unit`, app: detalhe do backtest e formulário de risco do bot (dicas), `docs/openapi.json`.

## 6. Plano incremental
Substituído pelo plano detalhado do §8 (fases A a G, com ordem, arquivos, contratos e testes).

## 7. Critérios de aceite e testes
* Os testes unitários batem com os Exemplos 6.2 e 6.3 dentro do arredondamento e com o Exemplo 6.1 (`g = −s²/2`).
* A saída de Kelly é `None` para poucos retornos ou variância zero, nunca infinita; sempre exibida com o tamanho da amostra.
* A exposição sugerida nunca excede 1 e nunca excede os limites live do operador.
* Nenhum comportamento de risco existente muda a menos que um modo opt-in seja ativado; salvaguardas do live intocadas.
* Tudo é `Decimal`; ruff, mypy, testes existentes verdes.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01 **sem alterar código**. As fases são independentes, salvo onde a dependência está dita. Convenções do projeto que valem para tudo abaixo: `Decimal` no domínio (nunca `float`), valores monetários e razões como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, comentários só onde explicam um porquê, texto de tela em português do Brasil, código e documentos em inglês no código (estes relatórios de livro estão em português por pedido do operador). Próxima migração livre: **`0013`** (a última é `0012_alerts`).

### Fase A — Dimensionamento de referência e perda de cauda (O1 + O2) · prioridade 1

Objetivo: dado um backtest concluído, mostrar ao operador (1) o Kelly cheio e o meio Kelly, (2) a pior perda em um período da estratégia e do ativo, (3) o teto de exposição `tolerável ÷ pior perda`, (4) uma fração máxima sugerida. **Conselho, nunca aplicação automática.**

**A.1 Back-end: funções puras** — novo `api/src/modules/analytics/domain/sizing.py` (sem frameworks; mesmo contexto de 40 dígitos de `risk_ratios.py`):
* `kelly_fraction(mean, variance) -> Decimal | None` = `mean / variance`; `None` se a variância for 0. Média e variância **por barra**: a razão é a mesma que com valores anualizados (o livro, p. 99, diz que o `f` de Kelly não depende da escala de tempo).
* `half_kelly(f)`; `growth_rate(f, mean, variance, risk_free=0)` = `r + f·m − s²·f²/2` (C3).
* `worst_period_loss(returns) -> Decimal | None`: a maior perda em um período, como valor positivo em %; `None` se não houve perda ou se a amostra for menor que `MIN_RETURNS`.
* `tail_cap(tolerable_loss_pct, worst_loss_pct) -> Decimal | None` = `tolerável ÷ pior perda` (sem limite se nunca houve perda).
* `suggest_fraction(configured_fraction, half_kelly_f, caps) -> Suggestion` com `value = min(1, configured_fraction × min(half_kelly, caps...))`, nunca maior que 1 (spot) e `binding` dizendo qual limite mandou (`half_kelly`, `tail_strategy`, `tail_asset`, `spot_limit`). `f` é um **multiplicador sobre o tamanho que a simulação usou**: numa simulação all-in vale 1 da carteira; numa simulação com limites vale `max_position_fraction` do bot (com `max_risk_per_trade_pct` a exposição real é menor, e isso entra como aviso).
* Amostra mínima de Kelly: **100 retornos** (constante `MIN_KELLY_RETURNS`, mais exigente que os 30 dos índices). Abaixo disso `kelly = None` com aviso.
* Caso de vantagem negativa (`mean ≤ 0`): `kelly_full = 0`, sugestão `0` e aviso "a simulação não mostrou vantagem".

**A.2 Back-end: bloco `tail_risk` gravado na execução** — novo `api/src/modules/analytics/domain/tail_risk.py`: `tail_risk(equity_curve, candles, bar) -> dict[str, Any]`, chamado em `BacktestExecutor._execute` (`backtesting/application/service.py`, junto de `compute_metrics`; já roda fora do laço de eventos). Conteúdo (todos os números como string decimal, datas em ISO UTC):
```
{
  "strategy": {"worst_bar_loss_pct", "worst_bar_at", "worst_day_loss_pct", "worst_day_at"},
  "asset":    {"worst_bar_return_pct", "worst_bar_at", "worst_day_return_pct", "worst_day_at"},
  "kelly_inputs": {"mean", "variance", "returns", "gaps"},
  "returns": n, "days": d
}
```
Retornos da estratégia: `periodic_returns` da curva de capital (descarta lacunas e as conta). Retornos do ativo: fechamento a fechamento dos candles. "Dia" = fechamento do último candle de cada dia UTC; para `timeframe` de 1 dia ou mais, dia e barra coincidem. Abaixo de `MIN_RETURNS`, os campos são `null`.

**A.3 Back-end: coluna e fio condutor** — migração `0013_tail_risk.py` (`ALTER TABLE backtest_runs ADD COLUMN tail_risk JSONB NULL`; `downgrade` remove a coluna; rodar `alembic check`). Seguir exatamente o caminho do `risk_report` (Cap. 5): `backtesting/application/ports.py` (campo em `BacktestRun` e parâmetro de `save_result`), `infrastructure/orm.py`, `infrastructure/repository.py` (mapeamento da linha e `save_result`), `application/service.py` (passar `tail_risk(...)`), `presentation/router.py` (`TailRiskOut` no `BacktestOut`), `api/docs/openapi.json`. Execuções antigas ficam com `tail_risk = null`.

**A.4 Back-end: endpoint** — `GET /api/v1/backtests/{run_id}/sizing?tolerable_loss_pct=<(0,100]>&scope=day|bar` (padrão `day`), em `backtesting/presentation/router.py`, regra em `backtesting/application/service.py` (`BacktestService.sizing`), tudo cálculo sobre o `tail_risk` gravado (barato, sem reler candles). Resposta `SizingAdviceOut`:
```
{
  "run_id", "scope", "tolerable_loss_pct",
  "sample": {"returns", "gaps", "min_required"},
  "kelly": {"full", "half", "growth_full", "growth_half", "mean", "variance"} | null,
  "tail": {"strategy_worst_loss_pct", "asset_worst_loss_pct", "cap_strategy", "cap_asset"} | null,
  "configured_fraction", "suggested_max_position_fraction",
  "binding": "half_kelly" | "tail_strategy" | "tail_asset" | "spot_limit",
  "above_reference": bool,
  "warnings": [str]
}
```
Erros: corrida inexistente → 404; corrida sem `tail_risk` (anterior a este recurso) ou ainda não concluída → 409 com mensagem pedindo para rodar de novo; `tolerable_loss_pct` fora de `(0, 100]` → 422. Avisos fixos: hipótese gaussiana e caudas gordas em cripto, Kelly calculado dentro da amostra tem o mesmo viés de overfitting do backtest, sugestão não aplicada. Leitura para qualquer papel (`require_access`); sem auditoria.

**A.5 Back-end: testes** — `tests/unit/test_sizing.py`: Exemplo 6.1 (`f=1`, `r=0`, `m=0`, `s=1%` → `g = −0,005%`), Exemplo 6.2 (média 11,23%, desvio 16,91%, livre de risco 4% → `f = 2,528`, `g = 13,14%`, `g(1) = 9,8%`); variância zero → `None`; média negativa → sugestão 0; sem perdas → sem teto; amostra curta → `None`; propriedade: multiplicar os retornos por `k` divide o teto por `k`; `suggest_fraction` nunca passa de 1 nem do limite do operador. `tests/unit/test_tail_risk.py`: curva sintética com um crash conhecido (pior barra e pior dia e seus horários), lacuna descartada e contada, timeframe diário. `tests/integration/test_sizing.py`: roda um backtest, chama `/sizing`, confere forma, 404, 409 (corrida antiga com `tail_risk` nulo), 422.

**A.6 Front-end** (regras de `app/AGENTS.md`):
* `lib/backtests/backtests.api.ts`: schemas `tailRiskSchema` (nullish) e `sizingSchema`, `getSizing(runId, tolerableLossPct, scope)`; `QueryKey.Backtests.sizing(id, tolerable, scope)` em `lib/shared/api/query-keys.ts`; hook `useSizing` em `hooks/backtests/use-backtests.ts` (só habilitado com a corrida concluída e `tail_risk` presente).
* `lib/shared/enums.ts`: nada de enum novo se `binding`/`scope` forem tratados como strings conhecidas em `lib/shared/labels.ts`; se virarem enum no OpenAPI, acrescentar a constante (o `check:consistency` falha se faltar).
* Componente novo `components/backtests/sizing-card.tsx`, usado em `backtest-detail-page.tsx` depois de `RiskReportCard`: campo "Perda tolerável em um período (%)" (padrão 10), seletor "Período: barra | dia", e o resultado: Kelly cheio e meio, pior perda da estratégia e do ativo (com data UTC), teto, **fração máxima sugerida e o limite que mandou**, tamanho da amostra, lista de avisos. Selo "acima da referência" com texto, nunca só cor, quando `above_reference`. Sem aritmética no app: tudo vem pronto da API e passa por `lib/shared/format.ts` (`formatRatio`, `formatPercent`, `formatFraction`).
* Botão "Criar bot com a fração sugerida": estender `BotPrefill` e `prefillFromRun` em `lib/shared/bot-prefill.ts` com `maxPositionFraction`, e `defaultFormValues`/`bot-form-page.tsx` para aceitar o pré-preenchimento. Ao lado do campo "fração máxima da posição" do formulário de bot, texto de apoio quando veio de um backtest.
* Esqueleto → erro com nova tentativa → vazio ("rode de novo para ver o dimensionamento") → dados; mostrar a data do cálculo; conferir em 1366 px e 360 px.
* Testes `vitest`: schema, formatação dos números, ordem dos avisos, pré-preenchimento.

**A.7 Documentos a atualizar na mesma mudança:** `api/README.md` (novo endpoint), `api/docs/openapi.json`, `app/docs/06-screens.md` (card), `docs/books/00-system-baseline.md`, o §8 deste relatório (virar "Implementação").

**Aceite da Fase A:** os exemplos 6.1 e 6.2 batem dentro do arredondamento; `suggested_max_position_fraction ≤ 1` e ≤ qualquer limite do operador; execuções antigas continuam abrindo (card em branco com a explicação); nenhum comportamento de risco ou de ordem muda; `make check` e a suíte de integração verdes; `npm run lint`, `typecheck`, `test`, `build` e `check:consistency` verdes.

### Fase B — Resumo de exposição do operador (O7, parte 1) · prioridade 2

Objetivo: tornar visível "manter o tamanho da carteira sob controle o tempo todo": exposição atual × limites globais × tetos live, por modo e moeda de cotação (nunca somar moedas diferentes).

* **Back-end:** `ExposureService` em `modules/risk_management/application/exposure.py` (usa `trading_stores`, as `Settings` e o relógio; campo `exposure` no `Container`). Reutilizar o agrupador por modo e moeda que `BotService.summary()` já usa. Endpoint `GET /api/v1/system/exposure` em `risk_management/presentation/router.py`:
```
{
  "groups": [{"mode", "quote_currency", "open_positions", "notional", "equity", "exposure_pct"}],
  "limits": {"global": {"max_open_positions", "max_total_exposure"},
             "live": {"max_order_notional", "max_total_exposure", "max_daily_loss"} | null},
  "bots": [{"bot_id", "name", "mode", "quote_currency", "configured_fraction", "notional", "pct_of_equity"}]
}
```
  Valores de `Settings.risk_max_open_positions`, `risk_max_total_exposure` e `live_max_*`. O custo é um laço por bot (como `overview`); aceitável até algumas centenas de bots. **Decisão pendente:** expor os tetos live a qualquer papel (não são segredos, mas hoje `/system/capabilities` não mostra números) ou só ao admin.
* **Testes:** unitário do agrupamento (duas moedas, nenhum bot, bot sem preço), integração com bots paper com posição aberta.
* **Front-end:** `lib/shared/system/system.api.ts` (`getExposure` + schema), `QueryKey.System.exposure`, hook em `hooks/shared/use-system.ts` (`Poll.Overview`), componente `components/shared/metrics/exposure-card.tsx` usado no painel (`components/bots/dashboard.tsx`) com barras de uso × limite **com o número escrito** e marca de "desatualizado" quando o polling falha; linha por bot com a fração configurada.
* **Parte 2 (depois da Fase A, fora deste corte):** coluna "× meio Kelly" por bot, exige decidir qual backtest representa o bot (mesma estratégia, símbolo e parâmetros) e como tratar vários.

### Fase C — Metadados de estilo e dica de stop (O4) · prioridade 3

* **Back-end:** em `strategies/domain/base.py`, `StrategyStyle(StrEnum)` com `TREND = "trend"` e `MEAN_REVERSION = "mean_reversion"` e `STYLE: ClassVar[StrategyStyle]` obrigatório; `StrategyRegistry.register` valida como já valida `NAME` (`strategies/domain/registry.py`). `ema_crossover` e `donchian_breakout` = `TREND`. `StrategyOut.style` em `strategies/presentation/router.py`. **Testes a ajustar:** as estratégias falsas de `tests/unit/test_strategy_contract.py` (casos de `registry refuses misdeclared`) e a estratégia com vazamento de `tests/unit/test_lookahead.py` precisam declarar `STYLE`; acrescentar caso "sem STYLE é recusada".
* **Front-end:** constante `StrategyStyle` em `lib/shared/enums.ts` e rótulos em `lib/shared/labels.ts` ("Tendência", "Reversão à média"); função pura `lib/shared/strategies/stop-hint.ts` (`stopHint(style, params, requireStopLoss)`) com teste: reversão à média com `stop_loss_pct` preenchido → "um stop curto sai no pior momento (Caps. 6 e 7); prefira o teto de risco"; tendência sem stop e sem `require_stop_loss` → "a saída é o sinal oposto; um stop limita a perda em gap". Aparece no rodapé de `components/shared/strategy/strategy-fields.tsx`, que os formulários de bot e de backtest já usam. Texto de **orientação**, nunca bloqueio (o argumento é observação do autor).

### Fase D — Replicação independente do backtest (O5) · prioridade 4 (só testes)

* `api/tests/reference_engine.py` (importado como `from reference_engine import ...`, no estilo de `factories`): reimplementação **independente** para `ema_crossover` e `donchian_breakout`: indicadores recalculados do zero a cada barra (não incrementais, ao contrário das estratégias), preenchimento a partir da especificação (taxa sobre o valor, derrapagem em bps, arredondamento ao passo de quantidade, stop/alvo com a regra de abertura em gap), sem importar `modules.backtesting.domain.engine` nem `execution.domain.fills`.
* `tests/unit/test_reference_engine.py`: em séries fixas (tendência, lateral, crash; com taxa e derrapagem não nulas; com e sem stop e alvo) compara operações (hora, lado, quantidade, preço, taxa) e patrimônio final com o motor, e confere um arquivo de valores congelados (`tests/golden/`, JSON pequeno) para pegar regressões silenciosas.
* **Limite a registrar:** a mesma equipe escreve os dois lados; o teste acha divergência entre implementações, não um erro conceitual comum aos dois. Falha = investigar qual lado está certo; nunca ajustar o teste só para passar.

### Fase E — Travas de disciplina (O6)

Especificação completa no [Cap. 8, §8](ch08-conclusion.md) (motivo nos comandos, diálogo de confirmação com diferenças na edição, contagem de intervenções por bot).

### Fase F — Redução gradual de risco (O3) · **só desenho; decisão do operador antes de codar**

Pontos já verificados no código que o desenho precisa respeitar:
* A regra mora em `assess_signal` (`risk_management/domain/models.py`), usada pelo trader e pelo `_RiskGuard` do backtest; o replay de paridade usa o mesmo caminho. Um fator de tamanho entra como parâmetro novo (`size_factor`, padrão 1) e **nada muda com o padrão**.
* Para não criar estado novo que possa divergir entre trader, backtest e paridade, o fator deve ser **função pura de dados que os três já têm** (retornos da curva de capital numa janela, ou resultado das últimas N operações): `size_factor(window_returns, limits) -> Decimal` em `risk_management/domain/`.
* Configuração em `RiskLimits` (`limits_to_dict`/`limits_from_dict` são retrocompatíveis): `dynamic_sizing: bool = False`, janela e piso. Só vale para **novas entradas** (spot long-only só muda de tamanho ao entrar); as pausas atuais continuam como retaguarda.
* **Decisões para o operador antes da implementação:** política (meio Kelly móvel limitado a `[0, fração]` × degraus por drawdown), tamanho da janela (o livro sugere seis meses para estratégias de um dia, p. 103), piso (0 trava o bot para sempre), e se um bot "congelado" por fator zero deve avisar pelos alertas. Risco conhecido: janelas móveis são ruidosas e fazem whipsaw.
* Critérios de aceite do futuro: com a janela nunca atuando o resultado é idêntico ao atual; séries com vantagem decrescente mostram frações decrescentes; paridade bot × replay sem diferença não explicada; pausas rígidas intactas.

### Ordem e dependências

1. **Fase A** (back, depois front) → 2. **Fase B** → 3. **Fase C** → 4. **Fase D** (em paralelo com qualquer outra) → 5. **Fase E** (Cap. 8) → 6. **Fase F** só depois de A, B e E terem rodado por um tempo.
Estimativa grosseira: A ≈ 3 a 4 dias (2 back, 1 a 2 front); B ≈ 1,5; C ≈ 1; D ≈ 1,5; E ver Cap. 8.

### Decisões pendentes (para o operador)
* Perda tolerável padrão (proposta: 10% por dia) e escopo padrão (`day`).
* Amostra mínima do Kelly (proposta: 100 retornos).
* Expor os tetos live a qualquer papel ou só ao admin (Fase B).
* Cap. 6 diz que meio Kelly "costuma" ser usado; confirmar que a sugestão deve usar **meio** Kelly e não a fração inteira.

### Critérios de aceite gerais
Nenhuma salvaguarda do live enfraquecida; nada aplicado automaticamente; todos os números em `Decimal`; `make check` (ruff, mypy strict, testes de unidade), suíte de integração em Postgres, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas novas conferidas em 1366 px e 360 px.

## Ressalvas
O dimensionamento de Kelly assume retornos conhecidos, estáveis e gaussianos; cripto tem caudas gordas, mudanças de regime e erro de estimação, então um número de Kelly é um **limite superior a ser descontado**, nunca uma recomendação de aumentar o tamanho. As anedotas do autor (LTCM, Amaranth, as próprias perdas) ilustram comportamento e não são evidência da fórmula. A volatilidade passada não limita perdas futuras.
