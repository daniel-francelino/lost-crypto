# Lost Crypto — API

Arquitetura: [docs/architecture/](docs/architecture/README.md). Contrato OpenAPI: [docs/openapi.json](docs/openapi.json).
Swagger UI com a API no ar: http://localhost:8000/docs

`src/` é a raiz de imports (`PYTHONPATH=src`); o `Makefile` e o Docker já configuram isso.

## Subir e testar

```bash
make up                 # postgres + api + worker
make migrate            # (local) aplica migrations; no Docker: docker compose exec api alembic upgrade head
make check              # ruff + mypy + testes unitários
make test-integration   # banco separado (lostcrypto_test), cria e migra sozinho; requer: make db
```

## Fase 1 — importar dados e rodar um backtest (EMA 9/21)

Importação e backtest são jobs assíncronos executados pelo worker: a API responde `202` e você consulta o status.

```bash
B=localhost:8000/api/v1

# 1. Importar candles de BTC/USDT (1h)
curl -X POST $B/market-data/imports -H 'content-type: application/json' \
  -d '{"symbol":"BTC/USDT","timeframe":"1h","start":"2024-01-01T00:00:00Z","end":"2024-07-01T00:00:00Z"}'
curl $B/market-data/imports/<job_id>                       # status: queued → running → completed
curl "$B/market-data/coverage?symbol=BTC/USDT&timeframe=1h"  # quantidade e lacunas

# 2. Rodar o backtest
curl -X POST $B/backtests -H 'content-type: application/json' -d '{
  "strategy_type": "ema_crossover",
  "strategy_params": {"fast_period": 9, "slow_period": 21},
  "symbol": "BTC/USDT", "timeframe": "1h",
  "start": "2024-01-01T00:00:00Z", "end": "2024-07-01T00:00:00Z",
  "initial_capital": "1000", "fee_rate": "0.001", "slippage_bps": "5"
}'
curl $B/backtests/<run_id>            # métricas (líquidas de taxas) + benchmark buy & hold
curl $B/backtests/<run_id>/trades     # fills simulados
curl $B/backtests/<run_id>/equity     # curva de capital
```

### Modelo da simulação

- Sinal gerado no fechamento do candle *i* é executado na **abertura do candle *i+1*** (sem look-ahead).
- Taxa (`fee_rate`, na moeda de cotação) e slippage adverso (`slippage_bps`) em toda execução.
- Quantidade arredondada para baixo no lote da exchange; ordens abaixo do mínimo são rejeitadas e contadas.
- Long-only spot: compra com todo o caixa no cruzamento para cima, vende toda a posição no cruzamento para baixo.
- Reprodutível: `data_hash` identifica os candles usados; mesmos dados + parâmetros = mesmo resultado.
- Resultados são simulações em dados históricos, **não** uma previsão de retorno. Compare sempre com o `buy_and_hold_return_pct`.

## Fase 2 — bots de paper trading

Preço real da Binance, dinheiro **simulado**: nenhuma chave de API e nenhuma ordem real. O bot roda no worker; a API só grava o estado desejado (`desired_state`) e o worker o aplica (`observed_state`).

```bash
B=localhost:8000/api/v1

# 1. Criar o bot (nasce parado)
curl -X POST $B/bots -H 'content-type: application/json' -d '{
  "name": "ema-btc-1h", "strategy_type": "ema_crossover",
  "strategy_params": {"fast_period": 9, "slow_period": 21},
  "symbol": "BTC/USDT", "timeframe": "1h", "initial_capital": "1000",
  "risk": {"max_position_fraction": "1", "max_daily_loss_pct": "10"}
}'

# 2. Comandos (assíncronos, 202): o worker aplica em poucos segundos
curl -X POST $B/bots/<id>/start     # também retoma um bot pausado
curl -X POST $B/bots/<id>/pause     # mantém sessão e estado da estratégia
curl -X POST $B/bots/<id>/stop      # encerra a sessão; o portfólio virtual é mantido

# 3. Acompanhar
curl $B/bots/<id>                   # desired_state x observed_state, heartbeat, last_error
curl $B/bots/<id>/orders            # ordens e status
curl $B/bots/<id>/signals           # sinais e a decisão do risco (approved/rejected/discarded_stale)
curl $B/bots/<id>/portfolio         # caixa, posição, PnL realizado/não realizado
curl $B/bots/<id>/performance       # mesmas métricas do backtest, líquidas de taxas
curl $B/bots/<id>/equity            # curva de capital (1 ponto por candle)
curl "$B/audit-events?bot_id=<id>"  # trilha de auditoria

# Emergência: pausa todos os bots e bloqueia novas entradas (soltar NÃO retoma os bots)
curl -X PUT $B/system/kill-switch -H 'content-type: application/json' -d '{"active": true, "reason": "teste"}'
```

Configuração (`PATCH /bots/{id}`) e `POST /bots/{id}/reset-portfolio` só funcionam com o bot parado.

### Como o paper trading funciona

- A cada candle **fechado** (checado no worker, sem chamada de rede até o próximo fechar) a estratégia avalia, o risco aprova/dimensiona e a ordem é simulada. Tudo em **uma transação**: ordem, fills, portfólio, snapshot, estado da estratégia e auditoria.
- Preço de referência do fill: fechamento do candle do sinal, com slippage adverso e taxa (mesma simulação do backtest).
- Início de sessão: ~300 candles só para aquecer a estratégia (sem sinais nem ordens).
- **Sem ordem duplicada:** o `client_order_id` é determinístico (bot + candle + lado) e único no banco; reprocessar o mesmo candle é no-op.
- **Sinal velho não vira ordem:** candles processados tarde demais (ex.: worker parado) atualizam só o estado da estratégia; o sinal fica registrado como `discarded_stale`.
- **Reinício do worker:** estado em Postgres; a sessão continua de onde parou, sem duplicar.
- **Falhas:** backoff exponencial por bot; após 5 seguidas o bot vai para `error` e é pausado. Um bot com problema não afeta os outros.
- **Risco:** fração máxima do capital por posição, teto de notional por ordem, perda diária máxima (pausa o bot) e kill switch global. Saídas continuam permitidas com o kill switch ativo.

## Fase 3 — exchanges, risco e pesquisa de estratégias

### Exchanges (trocar de exchange sem mexer em estratégia/risco)

Uma exchange é **uma classe em um arquivo** (`exchanges/infrastructure/binance.py`) que implementa o contrato único `Exchange` (`exchanges/application/exchange.py`: candles, regras de mercado, ordens). Quem escolhe quais ficam ativas é o catálogo (`exchanges/infrastructure/catalog.py`) junto com a variável `ENABLED_EXCHANGES` (padrão `binance`). Bots, backtests e importações têm o campo `exchange`; a taxa (`fee_rate`) é opcional e, sem ela, vale a taxa taker da exchange.

Para adicionar outra: copie `binance.py`, ajuste o perfil, registre no catálogo e habilite em `ENABLED_EXCHANGES`. Passo a passo e padrões de projeto: [docs/architecture/10-exchanges.md](docs/architecture/10-exchanges.md).

### Stop-loss, take-profit e limites de risco

A estratégia EMA aceita `stop_loss_pct` e `take_profit_pct` (% sobre o preço de entrada); o risco valida os níveis e o bot os monitora a cada candle (pela mínima/máxima; se os dois estiverem no candle, assume-se que o stop veio primeiro). O backtest aplica exatamente a mesma regra.

```bash
curl -X POST $B/bots -H 'content-type: application/json' -d '{
  "name": "ema-stop", "strategy_type": "ema_crossover",
  "strategy_params": {"fast_period": 9, "slow_period": 21, "stop_loss_pct": 2, "take_profit_pct": 6},
  "risk": {
    "max_position_fraction": "1",     "max_order_notional": "500",
    "max_risk_per_trade_pct": "1",    "require_stop_loss": true,
    "max_daily_loss_pct": "5",        "max_drawdown_pct": "15",
    "max_consecutive_losses": 4,      "max_candle_range_pct": "25"
  }
}'
```

| Limite (por bot) | Efeito |
|---|---|
| `max_risk_per_trade_pct` | dimensiona a posição para perder no máximo esse % do capital se o stop for atingido |
| `require_stop_loss` | recusa entradas sem stop |
| `max_daily_loss_pct`, `max_drawdown_pct`, `max_consecutive_losses` | **pausam** o bot (motivo em `last_error`) |
| `max_candle_range_pct` | recusa entradas em candle suspeito (dado ruim); saídas continuam permitidas |

Limites **globais** (todos os bots) ficam no ambiente do worker, não na API: `RISK_MAX_OPEN_POSITIONS` e `RISK_MAX_TOTAL_EXPOSURE`.

### Pesquisa de estratégias

```bash
# Treino/teste: reserva o fim da série como out-of-sample e reporta os dois lados em `segments`
curl -X POST $B/backtests -H 'content-type: application/json' -d '{
  "strategy_type": "ema_crossover", "start": "2024-01-01T00:00:00Z", "end": "2024-07-01T00:00:00Z",
  "test_fraction": "0.3"
}'

# Varredura: uma execução por combinação (combinações inválidas, ex. fast >= slow, são puladas)
curl -X POST $B/backtests/sweeps -H 'content-type: application/json' -d '{
  "strategy_type": "ema_crossover", "start": "2024-01-01T00:00:00Z", "end": "2024-07-01T00:00:00Z",
  "test_fraction": "0.3", "grid": {"fast_period": [5, 9, 20], "slow_period": [21, 50, 100]}
}'
curl $B/backtests/sweeps/<id>                                  # ranking (por retorno no TESTE)
curl "$B/backtests/compare?ids=<id1>&ids=<id2>"                # lado a lado
```

Ranqueie pelo **retorno no teste**: o melhor parâmetro do treino costuma ser sobreajuste. Sem `test_fraction` o ranking usa o período todo e a resposta avisa disso.

### Observabilidade

```bash
curl $B/system/status     # worker vivo? bots 'running' sem heartbeat recente (stale_bots)? kill switch?
curl $B/bots/overview     # todos os bots lado a lado: equity, retorno %, PnL, taxas, posição
```

`worker.alive` fica falso se o worker não gravar heartbeat por mais de `WORKER_STALE_AFTER_SECONDS` (60 s); aponte um monitor para esse endpoint, porque stops são monitorados pelo bot e não protegem com o worker parado.

### Estratégias (uma por arquivo)

Mesmo desenho das exchanges: um contrato (`Strategy`, em `strategies/domain/base.py`), **um arquivo por estratégia que se descreve sozinho** (chave, nome, descrição, parâmetros) e um catálogo (`strategies/catalog.py`) que lista as disponíveis. `ENABLED_STRATEGIES` (vazio = todas) restringe o que um worker expõe.

| `strategy_type` | Arquivo | Ideia |
|---|---|---|
| `ema_crossover` | `strategies/domain/ema_crossover.py` | compra no cruzamento da EMA rápida acima da lenta |
| `donchian_breakout` | `strategies/domain/donchian_breakout.py` | compra o rompimento da máxima dos últimos N candles, vende ao perder a mínima dos últimos M |

`GET /strategies` lista todas com seus parâmetros. Para criar uma nova: copie `donchian_breakout.py`, registre em `catalog.py`, rode `make test` (a suíte de contrato valida a estratégia sozinha) e use o `TYPE_KEY` em bots/backtests/varreduras. Passo a passo e padrões de projeto: [docs/architecture/11-strategies.md](docs/architecture/11-strategies.md).
