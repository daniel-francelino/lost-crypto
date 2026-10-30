# Lost Crypto — API

Arquitetura: [docs/architecture/](docs/architecture/README.md). Contrato OpenAPI: [docs/openapi.json](docs/openapi.json).
Swagger UI com a API no ar: http://localhost:8000/docs

`src/` é a raiz de imports (`PYTHONPATH=src`); o `Makefile` e o Docker já configuram isso.

## Subir e testar

```bash
make up                 # postgres + api + worker
make migrate            # (local) aplica migrations; no Docker: docker compose exec api alembic upgrade head
make check              # ruff + mypy + testes unitários
make test-integration   # requer: make db (e migrations aplicadas)
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
