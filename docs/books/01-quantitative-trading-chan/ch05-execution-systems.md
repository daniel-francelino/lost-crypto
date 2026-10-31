# Livro 1 · Capítulo 5 — Sistemas de execução

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

## 1. Resumo do capítulo (pp. 79–94)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Um **sistema de trading automatizado** busca dados, roda o algoritmo e envia ordens. O totalmente automatizado minimiza erro e atraso humanos e é indispensável para alta frequência; o semiautomatizado (arquivo de ordens → basket trader) serve para poucas ondas por dia. Muitas vezes o programa que gera ordens é o mesmo do backtest. | Execução fiel da estratégia testada. | 79–85 |
| C2 | Entradas que não são preço (dividendos, estimativas) também precisam ser buscadas e interpretadas. | Dados além dos preços. | 80 |
| C3 | **Minimizar custos de transação**: evitar ações de preço baixo; **limitar o tamanho da ordem a cerca de 1% do volume médio diário** (regra prática; exemplo: 1% do volume da IRN = 510 ações ≈ US$ 2.269); escalar o tamanho da posição de forma sublinear com o valor de mercado (raiz quarta mantém a razão maior/menor perto de 10) para preservar a diversificação; dividir ordens grandes troca impacto de mercado por slippage e não serve para traders pequenos. Verificações de velocidade/risco da corretora causam slippage fora do seu controle. | Impacto de mercado e iliquidez. | 87–88 |
| C4 | **Paper trading**: a única forma de achar bugs de software sem perder dinheiro; revela viés de look-ahead ("não tinha como você ter esse dado"); **comparar as operações e o P&L do paper com o backtest rodado nos mesmos dados mais recentes; diferenças não explicadas pelos custos (incluindo um atraso de execução esperado) significam bugs**. Também dá intuição sobre a volatilidade do P&L, o capital usado, operações por dia, tempos operacionais. Um mês ou mais pode revelar data-snooping, mas a atenção às contas de paper some, então o snooping geralmente só é revelado operando um capital real pequeno. | Verificar a implementação e a estratégia fora da amostra. | 89–90 |
| C5 | **Por que o live diverge do backtest** — diagnosticar em ordem: (1) bugs, (2) as operações live batem com as do backtest, (3) custos de execução maiores que o assumido, (4) iliquidez/impacto de mercado, depois (5) **data-snooping** (testar removendo regras e parâmetros: se o backtest desmorona, o snooping é provável; se continua razoável, má sorte é possível) e (6) **mudanças de regime** (exemplos: decimalização em 2001; a regra de uptick para vendas a descoberto até 2007; ações difíceis de alugar). Nunca se pode provar que foi má sorte. | Resultados live decepcionantes. | 90–92, 93–94 |
| C6 | Resumo dos benefícios do ATS: aderência à estratégia testada, rodar várias estratégias, velocidade. | – | 92–94 |

As ferramentas de corretora de Chan (links DDE, basket/spread traders, MATLAB, TradeStation) não se aplicam. As observações sobre cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C1 mesmo código no backtest e no live | ✅ forte | O backtester e o paper trader compartilham `execution/domain/fills.py` e `risk_management/domain/stops.py`; as estratégias são uma única classe usada pelos dois. |
| C1 backtest usa o dimensionamento do live | ❌ | O backtester dimensiona de forma trivial (todo o caixa); o dimensionamento/risco do live vive em `risk_management/domain/models.py::assess_signal` e **não** é aplicado nos backtests. Assim backtest e live podem divergir no tamanho da posição, no dimensionamento por risco por operação e nas rejeições de entrada. (Documentado na docstring de `engine.py`, mas é uma divergência real.) |
| C3 limite de volume | ❌ | Nenhum limite ligado a volume em `RiskLimits` ou no trader (busquei `volume` em `risk_management` e `trading`: sem ocorrências). O volume do candle é armazenado, mas não usado para risco. |
| C3 impacto dependente do tamanho | ❌ | O slippage é um bps fixo, independente do tamanho da ordem ou da liquidez. |
| C4 comparação paper vs. backtest | ❌ | Nenhuma ferramenta compara fills/PnL de um bot em paper com um backtest da mesma estratégia no mesmo período. `live_min_paper_days` condiciona a promoção apenas aos **dias decorridos** (`bots/application/live.py:146`), não à concordância com o backtest. |
| C4 tempos operacionais | ✅ | Heartbeat do worker, detecção de bot parado, reconciler a cada 60 s. |
| C5 diagnóstico de divergência | ❌ | Sem registro de fill esperado vs. real (preço pretendido no momento do sinal, preço do fill, latência), então o custo de execução não pode ser medido. |
| C5 checagem de snooping por simplificação | ⚠️ | Possível manualmente com sweeps; não empacotado. |
| C5 mudanças de regime | ❌ | Sem rastreamento de regime nem alertas quando o desempenho live sai da faixa do backtest. |

## 3. Oportunidades

### O1 — Relatório de paridade backtest/paper *(livro: C4, p. 89)*
* **Problema:** nada verifica que o sistema que roda a estratégia faz o que o backtest diz.
* **Proposta:** para um bot em paper, reexecutar o backtester sobre os candles exatos que o bot viu no mesmo período (mesmos parâmetros de estratégia e custos) e comparar sinais e fills; mostrar as diferenças não explicadas. Diferenças causadas só por custos/latência são esperadas (a exceção do livro).
* **Benefício:** pega bugs de implementação e look-ahead antes do dinheiro real. **Complexidade:** média. **Risco:** o pipeline live aplica dimensionamento de risco que o backtester não aplica; a paridade deve ou aplicar as mesmas regras de risco no replay (ver O2) ou comparar só os sinais. **Validação:** o replay de uma sessão paper conhecida deve bater; uma divergência injetada deve ser reportada.

### O2 — Rodar o módulo de risco real dentro do backtester *(livro: C1, pp. 79–85 · adaptação)*
* **Problema:** os backtests assumem dimensionamento all-in, então o risco e os retornos reportados não descrevem o que um bot com `RiskLimits` faria.
* **Proposta:** um modo opcional de backtest que passa cada sinal por `assess_signal` com os limites do bot e aplica pausas por perda diária, drawdown e perdas consecutivas, de modo que o replay reflita o comportamento live.
* **Benefício:** resultados de backtest comparáveis com paper/live. **Complexidade:** média–alta (é preciso estado como patrimônio no início do dia e perdas consecutivas). **Risco:** dois modos de dimensionamento produzem dois conjuntos de números; rotular com clareza. **Validação:** com limites que nunca atuam, os resultados são iguais ao modo all-in atual; com limites atuando, as operações são reduzidas como esperado.

### O3 — Limite de liquidez relativo ao volume *(livro: C3, p. 87 · o limiar é regra prática do autor; a aplicabilidade a cripto é adaptação)*
* **Proposta:** um limite de risco `max_order_pct_of_volume` usando o volume negociado recente (por exemplo uma média móvel do volume dos candles no ativo base), aplicado em `assess_signal` e no backtester. Desligado por padrão ou conservador; para os nossos tamanhos de conta raramente vai atuar nos pares principais, mas protege pares ilíquidos.
* **Complexidade:** baixa–média (precisa do volume no contexto de risco). **Risco:** o volume de candle em uma exchange não é a liquidez total do mercado. **Validação:** testes unitários da rejeição e do dimensionamento.

### O4 — Registrar execução pretendida vs. real *(livro: C3, C5, pp. 88, 90)*
* **Proposta:** persistir o preço de referência no momento do sinal/decisão, o preço do fill e a latência por ordem; calcular o slippage realizado por bot e compará-lo com o `slippage_bps` configurado.
* **Benefício:** mede a premissa de custo em vez de chutá-la; alimenta a sensibilidade a custos dos capítulos 2/3. **Complexidade:** baixa–média (novos campos nas ordens, aditivos). **Risco:** o slippage da testnet não representa o da mainnet. **Validação:** teste de integração com fills em paper.

### O5 — Checklist e painel de diagnóstico de divergência *(livro: C5, pp. 90–92)*
* **Proposta:** uma visão por bot que segue a ordem do livro — resultado da paridade (bugs), custo realizado vs. assumido, depois um convite para rodar o sweep de simplificação "remover parâmetros" (snooping), depois a comparação da distribuição de retornos live com a do backtest (regime). Em grande parte uma composição de O1, O4 e sweeps. **Complexidade:** média. **Validação:** teste de UI com um bot com dados semeados.

### O6 — Condicionar a promoção ao live à paridade *(livro: C4, p. 90 · adaptação)*
* Depois que O1 existir, adicionar "resultado do paper consistente com o backtest" como verificação de prontidão adicional ao lado de `live_min_paper_days`. **Complexidade:** baixa depois que O1 existir. **Risco:** limiares rígidos demais bloqueiam a promoção; fazer uma verificação visível com explicação clara, ainda sobrescrevível apenas pela política do operador (não em silêncio).

### Não aplicável / adiado
Ferramentas semiautomatizadas, DDE, contratar consultores, ponderação por valor de mercado (bots de ativo único), dividir ordens ao longo do tempo (o próprio livro diz que não serve para traders pequenos).

## 4. Prioridade

| # | Item | Confiabilidade | Qualidade do backtest | Gestão de risco | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O4 execução pretendida vs. real | média | média | média | baixa–média | – |
| 2 | O1 relatório de paridade | **alta** | alta | média | média | – |
| 3 | O3 limite de volume | – | – | média | baixa–média | – |
| 4 | O2 risco dentro do backtest | – | **alta** | alta | média–alta | – |
| 5 | O6 portão de promoção | média | – | alta | baixa | O1 |
| 6 | O5 painel de diagnóstico | – | média | – | média | O1, O4 |

## 5. Arquivos afetados
`backtesting/domain/engine.py`, `backtesting/application/service.py`, `risk_management/domain/models.py`, `trading/application/trader.py`, `execution/domain/orders.py` e seu ORM/repositório (campos aditivos), `bots/application/live.py`, novos testes em `api/tests/unit` e `api/tests/integration`, `docs/openapi.json`, páginas de detalhe do bot e de prontidão do app.

## 6. Plano incremental
1. O4: adicionar preço pretendido / latência aos registros de ordens (aditivo).
2. O1: ferramenta de replay como serviço e endpoint somente leitura, sem efeito sobre o trading.
3. O3: limite de volume como limite opcional.
4. O2: modo de backtest com risco atrás de uma flag.
5. O6, O5: portão e painel.

## 7. Critérios de aceite e testes
* Paridade: uma sessão paper limpa mostra zero diferenças não explicadas; uma divergência semeada é reportada.
* Registro de execução: novos campos anuláveis, ordens antigas não afetadas.
* Limite de volume: desligado por padrão; ligado, entradas grandes demais são reduzidas ou rejeitadas com um motivo.
* Backtest com risco: idêntico ao modo atual quando nenhum limite atua.
* Sem mudança nas salvaguardas do live; ruff, mypy e todos os testes existentes continuam verdes.

## Ressalva
A regra de 1% do volume médio diário é regra prática de Chan para ações e não foi calibrada para cripto. Os fills do paper trading simulam o mercado e não reproduzem a liquidez real nem a posição na fila.
