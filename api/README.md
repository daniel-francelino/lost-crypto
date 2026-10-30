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
