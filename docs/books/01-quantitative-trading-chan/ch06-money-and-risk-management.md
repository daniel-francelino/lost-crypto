# Livro 1 · Capítulo 6 — Gestão de dinheiro e de risco

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

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

## 3. Oportunidades

### O1 — Dimensionamento de referência Kelly/volatilidade como **conselho, não auto-trading** *(livro: C2, C3, C5, pp. 96–99 · a aplicação a cripto é adaptação nossa)*
* **Problema:** o operador escolhe `max_position_fraction` às cegas; o resultado central do livro diz que existe uma exposição ótima que depende da vantagem e da volatilidade, e que o próprio risco custa crescimento.
* **Proposta:** a partir dos retornos periódicos de um backtest, calcular `m`, `s`, o Kelly `f = m/s²` e o half-Kelly; mostrá-los (junto com o tamanho da amostra e o aviso de que as estimativas são ruidosas) ao lado da fração configurada. Limitar qualquer sugestão a 1 (spot). **Não** aplicar automaticamente na primeira iteração.
* **Benefício:** dimensionamento informado e um aviso visível quando a fração escolhida está acima de Kelly (mais risco, menos crescimento, conforme C3).
* **Complexidade:** baixa (funções puras, tudo em `Decimal`, testáveis contra os exemplos de SPY e dos três ETFs do livro).
* **Riscos:** `m` é difícil de estimar; poucos meses bons produzem um `f` grande; a hipótese gaussiana falha em cripto (caudas gordas), então usar no máximo half-Kelly e preferir o limite de C8; um Kelly dentro da amostra é tão sobreajustado quanto o backtest.
* **Validação:** reproduzir o Exemplo 6.2 (f = 2,528, g = 13,14%) e o Exemplo 6.3 (F = 1,2919, 1,1723, −1,4882; g = 15,29%, S = 0,4751) em testes unitários.

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
* **Proposta:** ao editar os parâmetros de estratégia de um bot em execução, mostrar a última comparação de backtest entre parâmetros antigos e novos e exigir um motivo (liga com o Capítulo 1 O3); registrar na auditoria. Não bloquear. **Complexidade:** baixa–média. **Risco:** atrito ignorado por hábito.

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
1. Funções puras de retornos, Kelly e pior perda de período, com os exemplos do livro como testes.
2. Expô-las nos resultados de backtest como campos opcionais; mostrar no app ao lado da fração escolhida.
3. Teste de checagem cruzada com implementação de referência (O5).
4. Resumo de exposição (O7) e trava de edição de parâmetros (O6).
5. Redução gradual de risco (O3) como desenho próprio depois que o acima tiver rodado por um tempo.

## 7. Critérios de aceite e testes
* Os testes unitários batem com os Exemplos 6.2 e 6.3 dentro do arredondamento e com o Exemplo 6.1 (`g = −s²/2`).
* A saída de Kelly é `None` para poucos retornos ou variância zero, nunca infinita; sempre exibida com o tamanho da amostra.
* A exposição sugerida nunca excede 1 e nunca excede os limites live do operador.
* Nenhum comportamento de risco existente muda a menos que um modo opt-in seja ativado; salvaguardas do live intocadas.
* Tudo é `Decimal`; ruff, mypy, testes existentes verdes.

## Ressalvas
O dimensionamento de Kelly assume retornos conhecidos, estáveis e gaussianos; cripto tem caudas gordas, mudanças de regime e erro de estimação, então um número de Kelly é um **limite superior a ser descontado**, nunca uma recomendação de aumentar o tamanho. As anedotas do autor (LTCM, Amaranth, as próprias perdas) ilustram comportamento e não são evidência da fórmula. A volatilidade passada não limita perdas futuras.
