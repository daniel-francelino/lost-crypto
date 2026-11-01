# Livro 1 · Capítulo 5 — Sistemas de execução

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **implementado** (O1–O7) em 2026-11-01; ver §8. As tabelas §2 descrevem o código **antes** desta implementação.

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
| C1 mesmo código no backtest e no live | ✅ | Estratégias, `execution/domain/fills.py` (preço com slippage, taxa, normalização) e `risk_management/domain/stops.py` são os mesmos no backtester e no trader. O teste de truncamento do Cap. 3 cobre o motor. |
| C1 **momento** da execução | ⚠️ divergência | O backtester executa o sinal na **abertura do candle seguinte** (`backtesting/domain/engine.py`); o trader executa no **fechamento do candle do sinal** (`reference_price=candle.close` em `trading/application/trader.py`), no paper com o slippage configurado e em testnet/live com uma ordem a mercado enviada logo depois. Em cripto, que negocia sem parar, os dois preços costumam ser quase iguais, mas não são o mesmo número, e nenhum lugar mede essa diferença. |
| C1 dimensionamento e regras de risco | ❌ | O backtester compra com todo o caixa e vende tudo; o trader passa cada sinal por `assess_signal` (`max_position_fraction`, `max_order_notional`, risco por operação a partir do stop, exposição global, candle suspeito) e pausa o bot por perda diária, drawdown e perdas consecutivas. O backtest **não** reproduz nada disso. |
| C3 limite de volume | ❌ | Nenhuma regra usa o volume (busca por `volume` em `risk_management` e `trading`: nenhuma ocorrência). O volume do candle chega ao trader e é ignorado. |
| C3 impacto dependente do tamanho | ❌ | Slippage em bps fixo; a escada de custos do Cap. 2 mede a sensibilidade, mas não modela impacto. |
| C4 paridade paper × backtest | ❌ | Nada compara os sinais e as operações de um bot com um backtest da mesma estratégia no mesmo período. Pior: **o bot não guarda os candles que processou** (busca na exchange a cada ciclo; só os snapshots guardam o fechamento), então nem dá para reproduzir com exatidão o que ele viu. Os sinais (`trading_signals`: candle, lado, decisão, motivo) e as ordens/fills ficam gravados e servem de lado "real" da comparação. |
| C4 prontidão para o live | ⚠️ | `live_min_paper_days` (`bots/application/live.py`) conta só **dias decorridos** de paper; nenhuma verificação de que o paper se comportou como o backtest. |
| C4 tempos operacionais | ✅ | Heartbeat, bots parados, reconciliação, monitor externo e relógio (Cap. 4). |
| C5 custo de execução realizado | ❌ | A ordem guarda `bar_time`, `created_at`, `avg_fill_price` e os fills com horário, mas **não o preço de referência** da decisão; sem ele não se calcula o slippage realizado nem a latência de forma direta. |
| C5 snooping por simplificação | ⚠️ | Dá para fazer à mão com backtests (desligar stop/alvo, mudar parâmetros); nada empacotado. |
| C5 mudança de regime | ⚠️ | O Cap. 2 trouxe métricas por período e o Cap. 3 a qualidade dos dados, mas nada compara o desempenho live/paper com a faixa esperada pelo backtest. |

### 2.1 O que mudou desde a versão anterior deste relatório
* **Achado novo:** o momento da execução difere entre backtest (abertura seguinte) e trader (fechamento do sinal). Não é um bug, mas tem de ser declarado e medido na paridade.
* **Achado novo:** os bots não gravam os candles que processam; sem isso, a paridade exige importar os candles depois e torcer para a exchange devolver os mesmos valores.
* Já existe desde os Caps. 2–4: escada de custos (a sensibilidade que O4 alimenta), métricas por período, contagem de tentativas, sinais com motivo da decisão.

## 3. Oportunidades

Convenções dos capítulos anteriores: campos novos opcionais e aditivos; `openapi.json` + `npm run api:types` + `check:consistency`; textos da UI em português; nenhuma mudança enfraquece as salvaguardas do live.

### O1 — Registrar a execução pretendida × real *(livro: C3, C5, pp. 88, 90)*
* **Back-end:**
  * Novas colunas em `orders`: `reference_price` (o preço da decisão: fechamento do candle do sinal, ou o gatilho do stop/alvo), `decided_at` (= `created_at` hoje, explícito), `submitted_at`, `first_fill_at`.
  * Calculados na leitura: `slippage_bps` realizado (adverso positivo: compra acima / venda abaixo da referência) e `latency_ms` (decisão → primeiro fill).
  * `GET /bots/{id}/execution-quality`: por bot, média, mediana e pior slippage realizado contra o `slippage_bps` configurado, latência média e máxima, número de ordens; separado por tipo (mercado, stop) e por modo.
  * Ordens antigas ficam com os campos nulos.
* **Front-end:**
  * Aba "Ordens" do bot: colunas "Referência", "Slippage (bps)" e "Latência", com o slippage acima do configurado em destaque.
  * Card "Qualidade de execução" no resumo do bot: "slippage realizado 7,2 bps × configurado 5 bps em 18 ordens", com a sugestão de usar o valor medido nos backtests (link que abre o formulário com o slippage preenchido).
* **Complexidade:** baixa–média. **Risco:** o slippage do paper é o próprio parâmetro e o da testnet não representa o da mainnet; a tela diz de qual modo vem cada número. **Validação:** teste de integração com fills paper (slippage = configurado) e testnet simulados (slippage conhecido).

### O2 — Gravar os candles que o bot processou *(livro: C4, p. 89 · pré-requisito da paridade)*
* **Back-end:** o trader faz `upsert` de cada candle **válido** que processa na tabela `candles` (mesma estrutura das importações), com a origem do bot. Assim a série que o bot viu fica disponível para o replay e para a tela de dados de mercado. Se um candle já existe com OHLCV diferente, conta como "alterado" (mesma regra do Cap. 3) e grava um evento.
* **Front-end:** nada novo; a cobertura do par passa a incluir o que os bots viram.
* **Complexidade:** baixa. **Risco:** volume de escrita por candle (desprezível nos intervalos atuais). **Validação:** teste de integração: depois de N candles, a tabela tem os mesmos N candles do bot.

### O3 — Relatório de paridade bot × backtest *(livro: C4, p. 89)*
* **Problema:** nada verifica que o sistema que opera faz o que o backtest diz.
* **Back-end:**
  * `POST /bots/{id}/parity` (fila, como os backtests): para o período da sessão (ou um intervalo pedido), roda o backtester com os candles gravados por O2, os mesmos parâmetros, `fee_rate`, `slippage_bps` e — quando O4 existir — os mesmos limites de risco.
  * Compara **sinais** (candle, lado, tipo) e **operações** (lado, quantidade, preço) e classifica cada diferença: `timing` (abertura seguinte × fechamento do sinal, esperada), `cost` (só preço, dentro do slippage medido), `risk` (rejeitado pelo risco no bot, sem equivalente no backtest sem O4), `data` (candle ausente ou alterado), `unexplained`.
  * Resultado salvo (`parity_runs`, JSONB): contagens por classe, lista das diferenças, PnL do bot × PnL do replay e a diferença explicada por custo e momento. Somente leitura: não afeta o trading.
* **Front-end:**
  * Aba "Paridade" no bot: botão "Comparar com o backtest", situação da execução, veredito ("consistente" / "diferenças não explicadas"), tabela de diferenças por classe com o candle e o motivo, e as duas curvas de capital sobrepostas.
  * Link para abrir o backtest equivalente na tela de backtests.
* **Complexidade:** média. **Risco:** se o risco não for aplicado no replay (O4), as rejeições do bot aparecem como `risk` e o veredito compara só os sinais. **Validação:** replay de uma sessão paper limpa = zero `unexplained`; uma diferença semeada (candle alterado, sinal removido) aparece na classe certa.

### O4 — O backtest com o risco do bot *(livro: C1, pp. 79–85 · adaptação)*
* **Back-end:**
  * Opção `risk_limits` em `BacktestCreate` (mesmo esquema do bloco de risco do bot) e `fill_timing` (`next_open`, padrão atual; `signal_close`, como o trader). Com limites, o motor passa cada sinal por `assess_signal` e aplica as pausas por perda diária, drawdown e perdas consecutivas, mantendo o estado necessário (patrimônio no início do dia UTC, pico, sequência de perdas).
  * O resultado mostra a origem do dimensionamento (`sizing: "all_in" | "risk_limits"`) e quantos sinais o risco recusou, por motivo.
  * Ação "Backtest com a configuração deste bot" no bot: copia estratégia, parâmetros, custos e limites.
* **Front-end:**
  * Formulário de backtest: seção "Risco como no bot" (opcional, mesmo componente do formulário de bot) e escolha do momento da execução, com a explicação curta das duas opções.
  * Resultado: selo "dimensionado como o bot" e um card com as recusas do risco por motivo.
  * No bot: botão "Rodar backtest com esta configuração".
* **Complexidade:** média–alta. **Risco:** dois modos de dimensionamento produzem números diferentes; o selo deixa claro qual é qual. **Validação:** com limites que nunca atuam e `fill_timing=next_open`, resultado idêntico ao atual; com limites atuando, operações reduzidas como esperado; com `signal_close`, o replay de O3 casa com o paper.

### O5 — Limite de liquidez pelo volume *(livro: C3, p. 87 · o limiar é regra prática do autor; a aplicação a cripto é adaptação)*
* **Back-end:** novo limite `max_order_pct_of_volume` em `RiskLimits` (desligado por padrão): compara o valor da ordem com a média do volume em quote dos últimos 20 candles (volume × fechamento); acima do limite, reduz a ordem ao máximo permitido ou recusa se ficar abaixo do mínimo da exchange, com motivo. A estratégia não muda; o trader passa o volume médio no contexto do risco, e o backtester com O4 faz o mesmo.
* **Front-end:** campo no bloco de risco do bot ("Máximo da ordem como % do volume médio", com a dica do livro: 1% do volume diário em ações) e o motivo nas recusas da aba de sinais.
* **Complexidade:** baixa–média. **Risco:** o volume de uma exchange não é a liquidez total do mercado. **Validação:** testes de unidade de redução e recusa; teste de integração com um candle de volume baixo.

### O6 — Diagnóstico de divergência *(livro: C5, pp. 90–92)*
* **Back-end:** `GET /bots/{id}/divergence` monta a ordem de diagnóstico do livro a partir do que já existe: (1) paridade (O3), (2) operações iguais às do backtest (O3), (3) custo realizado × assumido (O1), (4) liquidez (O5: quantas ordens foram limitadas pelo volume), (5) snooping: resultado de um backtest **simplificado** (sem stop/alvo e com os parâmetros padrão da estratégia) no mesmo período, e (6) regime: retorno, Sharpe e drawdown do bot × a faixa do backtest por período (Cap. 2) e o veredito de robustez (Cap. 3) quando houver varredura.
* **Front-end:** aba "Diagnóstico" no bot com os seis passos como checklist, cada um com o estado (ok / atenção / sem dados), uma frase e o link para a evidência (paridade, ordens, backtest simplificado, períodos). Nunca conclui "foi má sorte" (o livro: isso não se prova).
* **Complexidade:** média. **Validação:** teste da API com um bot semeado; teste do front para cada estado.

### O7 — Paridade como requisito do live *(livro: C4, p. 90 · adaptação)*
* **Back-end:** nova verificação na prontidão live: existe uma paridade concluída nos últimos 7 dias de paper **sem diferenças `unexplained`**. Visível com o motivo; sem atalho para ignorar.
* **Front-end:** a lista de prontidão mostra o item com link para rodar a paridade.
* **Complexidade:** baixa depois de O3. **Risco:** bloquear a promoção por diferenças pequenas; por isso só a classe `unexplained` bloqueia. **Validação:** teste da prontidão com e sem paridade.

### Não aplicável / adiado
Ferramentas semiautomatizadas (arquivo de ordens, basket trader, DDE), ponderação por valor de mercado (um ativo por bot), dividir ordens grandes ao longo do tempo (o próprio livro diz que não serve para traders pequenos), dados que não são preço (dividendos, estimativas).

## 4. Prioridade

| # | Item | Confiabilidade | Qualidade do backtest | Gestão de risco | Esforço back | Esforço front | Depende de |
|---|---|---|---|---|---|---|---|
| 1 | O1 execução pretendida × real | média | média | média | baixo–médio | baixo | – |
| 2 | O2 gravar candles do bot | alta | – | – | baixo | – | – |
| 3 | O3 paridade bot × backtest | **alta** | alta | média | médio | médio | O2 |
| 4 | O4 backtest com o risco do bot | – | **alta** | alta | médio–alto | médio | – |
| 5 | O7 paridade no live | média | – | alta | baixo | baixo | O3 |
| 6 | O5 limite de volume | – | – | média | baixo–médio | baixo | – |
| 7 | O6 diagnóstico | – | média | – | médio | médio | O1, O3, O4 |

O1 e O2 primeiro: são baratos e sem eles a paridade não tem com o que comparar.

## 5. Arquivos afetados

**Back-end (`api/`)**
* `src/modules/execution/domain/orders.py`, `execution/infrastructure/orm.py` e repositório (`reference_price`, `submitted_at`, `first_fill_at`), `trading/application/trader.py` e `orders.py` (gravar referência e horários; gravar candles; volume no contexto do risco).
* `src/modules/risk_management/domain/models.py` (`max_order_pct_of_volume`), `bots` (formulário de risco, prontidão com paridade, rotas `execution-quality`, `parity`, `divergence`).
* `src/modules/backtesting/domain/engine.py` (`fill_timing`, risco opcional com estado), `backtesting/application/service.py`, `presentation/router.py`.
* Novo `src/modules/trading/application/parity.py` (replay e classificação das diferenças) e tabela `parity_runs`.
* Migração `0011_execution_parity.py`; `docs/openapi.json`.
* Testes: unidade (slippage realizado, classificação da paridade, limite de volume, motor com risco), integração (paridade de uma sessão paper, prontidão com paridade).

**Front-end (`app/`)**
* `src/components/bots/bot-tabs.tsx` e novos componentes de aba ("Paridade", "Diagnóstico"), card "Qualidade de execução", colunas novas em "Ordens"; `src/lib/bots/bots.api.ts` (schemas e chamadas).
* `src/components/bots/bot-form-page.tsx` (limite de volume); `src/components/backtests/backtest-form-page.tsx` e `src/lib/backtests/form.ts` (risco como no bot, momento da execução).
* Fluxo de aprovação live (item de paridade na prontidão); `app/docs/06-screens.md`.

## 6. Plano incremental
1. **O1 + O2:** referência e horários nas ordens; candles do bot gravados; colunas e card de qualidade de execução.
2. **O4 parte 1:** `fill_timing` no backtest (barato e já ajuda a paridade).
3. **O3:** paridade por sinais e operações, com classificação; aba "Paridade".
4. **O4 parte 2:** risco do bot dentro do backtest; botão "backtest com esta configuração".
5. **O7:** paridade na prontidão live.
6. **O5:** limite de volume.
7. **O6:** aba de diagnóstico.

## 7. Critérios de aceite e testes
* Ordens novas trazem preço de referência e horários; o slippage realizado de uma ordem paper é igual ao configurado; ordens antigas continuam abrindo.
* Cada candle processado por um bot está na tabela `candles`.
* A paridade de uma sessão paper limpa (com `fill_timing=signal_close` e o risco do bot) não tem diferenças `unexplained`; uma diferença semeada cai na classe certa.
* Um backtest com limites que nunca atuam e `fill_timing=next_open` é idêntico ao atual.
* Com `max_order_pct_of_volume` ligado, uma entrada grande demais é reduzida ou recusada com motivo; desligado, nada muda.
* A prontidão live exige uma paridade recente sem `unexplained`.
* Nenhuma salvaguarda do live enfraquecida; `make check`, integração, `npm run lint`, `typecheck`, `test`, `build` verdes; telas novas conferidas em 1366 px e 360 px.

## 8. Implementação (2026-11-01)

Implementado na branch `docs/ch02-fishing-for-ideas-review`, back-end e front-end.

**Back-end (`api/`)**
* **O1:** `orders` ganhou `reference_price` (fechamento do sinal ou gatilho do stop), `submitted_at` (quando saiu para a exchange; no paper, no mesmo passo) e `first_fill_at`. `realized_slippage_bps` e `latency_ms` (`execution/domain/orders.py`) aparecem em cada ordem; `GET /bots/{id}/execution-quality` agrega por tipo de ordem contra o `slippage_bps` configurado.
* **O2:** o trader grava na tabela `candles` cada candle válido que processa (inclusive o aquecimento); um candle já guardado que a exchange devolve diferente é sobrescrito e auditado (`data.candle_changed`).
* **O4:** `BacktestConfig.fill_timing` (`next_open` padrão, `signal_close` como os bots) e `risk` (limites do bot). Com limites, o motor usa o mesmo `assess_signal` e as mesmas pausas (perda diária, drawdown, perdas seguidas); pausado, só os stops funcionam. `risk_report` no resultado (dimensionamento, pausa, recusas por motivo). **O caminho padrão ficou idêntico** (todos os testes antigos, incluindo o de truncamento, passam sem mudança).
* **O5:** `RiskLimits.max_order_pct_of_volume` (média do valor negociado dos últimos 20 candles, ignorada com menos de 5) no trader e no backtest com risco; recusa com motivo quando o tamanho limitado fica abaixo do mínimo da exchange.
* **O3:** `POST /bots/{id}/parity` enfileira; o worker (`ParityExecutor`) refaz a última sessão nos candles guardados, com aquecimento, `signal_close` e o risco do bot, e classifica cada sinal (`trading/domain/parity.py`): `match`, `cost`, `risk`, `operational`, `data`, `unexplained`. Também roda um replay com os parâmetros padrão (para o passo de snooping). Resultado em `parity_runs`; `GET /bots/{id}/parity`.
* **O6:** `GET /bots/{id}/divergence`: os seis passos do livro (bugs, operações, custo, liquidez, snooping, regime), cada um com estado e os valores numéricos; regime compara o retorno do bot com o pior período do último backtest comparável.
* **O7:** a prontidão live exige uma paridade concluída nos últimos 7 dias **sem** diferenças `unexplained`.
* Migração `0011_execution_parity.py` (`alembic check` limpo; downgrade testado); `parity_runs` apaga em cascata com o bot.

**Front-end (`app/`)**
* Ordens do bot com referência, slippage (destacado acima do assumido) e latência; card "Qualidade de execução" no resumo com link para um backtest usando o slippage medido.
* Abas novas no bot: "Paridade" (comparar, veredito, contagem por classe, retornos, curvas sobrepostas, tabela de diferenças) e "Diagnóstico" (checklist em português montado a partir dos valores da API; nunca conclui "azar").
* "Rodar backtest com esta configuração": `/backtests/new` aceita pré-preenchimento (estratégia, parâmetros, custos, momento da execução, limites de risco).
* Formulário de backtest: card "Execução e risco como no bot"; resultado com card "Como foi dimensionado".
* Formulário de bot: "Máximo da ordem (% do volume médio)".

**Diferenças em relação ao plano**
* A paridade roda no **worker** (fila), não na API: o replay precisa das regras de mercado da exchange, que só o worker acessa.
* Classe nova `operational` (sinal atrasado, ordem pendente, kill switch, avisos de chave/relógio, hard caps), separada de `risk`.
* A comparação é por sinal (candle + lado), com preço; a quantidade não é comparada (o capital da sessão pode diferir do replay quando havia posição antes dela).
* O texto do diagnóstico em português é montado no app; a API devolve o detalhe em inglês e os números (`values`).
* Ajustes de tela achados na conferência em 360 px: o JSON de parâmetros do backtest agora quebra linha e as tabelas de períodos/custos rolam dentro do card.

**Verificação**
* API: `make check` (ruff, mypy strict, 276 testes de unidade) e 86 testes de integração em Postgres 16, todos passando. Destaque: os 15 testes de live agora rodam a paridade de verdade na sessão paper antes da promoção, e todos dão **zero** diferenças sem explicação; o novo `test_phase7_execution.py` cobre candles guardados, slippage medido = configurado no paper, paridade consistente, uma divergência semeada detectada e um backtest com o risco do bot sobre os candles que o bot guardou.
* Sessão paper sintética de 130 h com stop: 11 sinais idênticos, 0 sem explicação; retorno do bot = retorno do replay.
* App: `lint`, `typecheck`, `test` (81), `format:check`, `check:consistency`, `build`; telas conferidas em 1366 px e 360 px sem erros no console.
* **Problema existente, não tratado:** em 360 px a tela do bot rola ~400 px na horizontal por causa da fileira de botões do cabeçalho (Iniciar/Pausar/Parar/Resetar/Promover/Editar), que não foi alterada nesta branch.

## Ressalva
A regra de 1% do volume médio diário é regra prática de Chan para ações e não foi calibrada para cripto. Os fills do paper trading simulam o mercado e não reproduzem a liquidez real nem a posição na fila.
