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
curl $B/market-data/imports/<job_id>                       # status, candles_rejected, candles_changed
curl "$B/market-data/coverage?symbol=BTC/USDT&timeframe=1h"  # quantidade e lacunas da série
curl "$B/market-data/coverage?symbol=BTC/USDT&timeframe=1h&start=2024-01-01T00:00:00Z&end=2024-07-01T00:00:00Z"  # + in_range
curl "$B/market-data/outliers?symbol=BTC/USDT&timeframe=1h&start=2024-01-01T00:00:00Z&end=2024-07-01T00:00:00Z"  # > 4σ
curl "$B/market-data/listings?symbol=BTC/USDT"               # listado/deslistado (registro diário)

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
curl $B/backtests/sweeps/<id>                                  # ranking pelo TREINO; o teste confere o vencedor
curl "$B/backtests/sweeps/<id>?rank_by=test_sharpe_ratio"      # outro critério (consome o teste)
curl "$B/backtests/compare?ids=<id1>&ids=<id2>"                # lado a lado

# Robustez: escada de custos (0x a 3x taxa+slippage, até 50.000 candles) e tolerância de drawdown
curl -X POST $B/backtests -H 'content-type: application/json' -d '{
  "strategy_type": "ema_crossover", "start": "2024-01-01T00:00:00Z", "end": "2024-07-01T00:00:00Z",
  "cost_sensitivity": true, "max_drawdown_tolerance_pct": "15", "max_drawdown_tolerance_days": 60
}'
```

Com `test_fraction`, a varredura **escolhe pelo treino** e mostra o teste do vencedor como verificação: escolher pelo teste o transforma em dado de seleção. A resposta traz `trials` (combinações tentadas) e `prior_trials` (execuções anteriores da mesma estratégia sobre os mesmos dados, aproximado). Sem `test_fraction` o ranking usa o período todo e a resposta avisa disso.

Qualidade dos dados: candles inválidos (máxima abaixo do corpo, preço ≤ 0, horário fora da grade…) **não são gravados** na importação (`candles_rejected` + amostras) e o bot pula o candle com um evento de auditoria `data.invalid_candle`; reimportações contam `candles_changed`. Um backtest com mais de 1% dos candles faltando no período, ou um buraco maior que 24 h, é recusado (422) a menos que `"allow_gaps": true`; cada execução traz `data_quality` (lacunas, candles inválidos, movimentos acima de 4σ, tamanho da amostra contra 252 × parâmetros livres). A varredura traz `robustness` (`plateau`, `peak`, `unprofitable`, `insufficient`) comparando o vencedor com os vizinhos na grade. O worker grava uma vez por dia os pares listados pela exchange (`/market-data/listings`).

Execução (livro 1, cap. 5): cada ordem guarda o preço de referência e os horários (`slippage_bps`, `latency_ms`); `GET /bots/{id}/execution-quality`. O bot grava os candles que processa; `POST /bots/{id}/parity` (o worker roda) refaz a sessão no backtester e classifica as diferenças, e o live exige uma paridade recente sem `unexplained`; `GET /bots/{id}/divergence` dá o checklist do livro. Backtests aceitam `"fill_timing": "signal_close"` e `"risk": {…}` para executar e dimensionar como um bot. Limite opcional `max_order_pct_of_volume` no risco do bot.

Métricas (`metrics`, também em `/bots/{id}/performance`): além de retorno e drawdown, Sharpe, Sortino, information ratio contra comprar e segurar, retorno e volatilidade anualizados (365 dias, taxa livre de risco 0; `null` com menos de 30 retornos), exposição, duração do drawdown e se ele ainda está aberto. Cada backtest traz também `periods` (por ano, ou trimestre abaixo de 2 anos) e, se pedido, `cost_ladder` com o custo de equilíbrio e `tolerance`.

### Observabilidade

Operação (servidor, monitor externo, backup e restauração, relógio, chaves): [`docs/operations/runbook.md`](docs/operations/runbook.md). Resumo: `GET /health/worker` responde 503 quando o worker para (aponte um monitor externo para ele); `make backup` e `make restore-check`; `POST /exchange-connections/{id}/recheck` reverifica as permissões de uma chave.

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

## Fase 4 — testnet da exchange (dinheiro fictício, ordens reais no sandbox)

Detalhes, diagramas e limitações: [docs/architecture/12-testnet-and-reconciliation.md](docs/architecture/12-testnet-and-reconciliation.md).

**Pré-requisitos (nada é aceito sem eles):**

```bash
make master-key                      # gera a chave que criptografa as credenciais
# .env (não versionar): API_TOKEN=<segredo>  CREDENTIAL_MASTER_KEYS=<chave>  TESTNET_TRADING_ENABLED=true
```

- `API_TOKEN`: todo endpoint (exceto health) passa a exigir `Authorization: Bearer <token>`. Em `APP_ENV=prod` a API nem sobe sem ele; `/exchange-connections` exige o token sempre.
- `CREDENTIAL_MASTER_KEYS`: chave Fernet que criptografa as credenciais no banco (várias, separadas por vírgula, para rotação).
- `TESTNET_TRADING_ENABLED=true` no **worker**: sem isso um bot testnet entra em `error` ao iniciar.
- Chaves da testnet: https://testnet.binance.vision (login com GitHub). **Só chaves de testnet.** Conexões `live` são recusadas.

```bash
H="Authorization: Bearer $API_TOKEN"; B=localhost:8000/api/v1
# 1. Credenciais (guardadas criptografadas; nunca devolvidas)
curl -H "$H" -X POST $B/exchange-connections -H 'content-type: application/json' \
  -d '{"label":"minha-testnet","api_key":"...","api_secret":"..."}'
# 2. Bot em modo testnet usando essa conexão
curl -H "$H" -X POST $B/bots -H 'content-type: application/json' -d '{
  "name":"ema-testnet","mode":"testnet","connection_id":"<id>","symbol":"BTC/USDT","timeframe":"1h",
  "strategy_type":"ema_crossover","strategy_params":{"stop_loss_pct":2}}'
curl -H "$H" -X POST $B/bots/<id>/start
curl -H "$H" $B/bots/<id>/orders      # status (SUBMITTING/UNKNOWN/FILLED...), exchange_order_id, tipo
curl -H "$H" $B/bots/<id>/portfolio   # reserved_cash e native_stop_active
```

**Como funciona (resumo):** a ordem é gravada como `SUBMITTING` (id determinístico + capital reservado) numa transação, enviada à exchange fora de qualquer transação e o resultado aplicado numa segunda. Falha ambígua (timeout) vira `UNKNOWN` e é resolvida **consultando o id na exchange**, nunca reenviando. O stop-loss fica na exchange e é aplicado ao portfólio mesmo se o worker estava parado. A cada minuto a conta é conferida: se a exchange tem menos do que os bots acham que têm, ou há ordem com o prefixo `lc-` desconhecida, os bots são **pausados** (`reconciliation mismatch`) e a execução fica em `reconciliation_runs`.

**Validação:** o ciclo é coberto por testes contra uma exchange *simulada* com falhas injetadas. Contra a Binance real foram confirmados (com chave inválida) o endpoint sandbox, as regras de mercado e o erro `-2015`. **Ordens reais ainda não foram testadas** (sem chaves): rode `make test-testnet` com `TESTNET_API_KEY`/`TESTNET_API_SECRET`.

## Autenticação (frontend)

Detalhes: [docs/architecture/14-authentication.md](docs/architecture/14-authentication.md).

```bash
make jwt-secret                  # valor para JWT_SECRET (no .env)
make create-admin                # primeiro admin (pede a senha); no Docker: docker compose exec api python -m manage create-user daniel --role admin
```

```bash
B=localhost:8000/api/v1
curl -c jar -X POST $B/auth/login -H 'content-type: application/json' -d '{"username":"daniel","password":"..."}'
#  -> {"access_token": "...", "expires_in": 900, "user": {...}}   + cookie httpOnly refresh_token
curl -H "Authorization: Bearer <access_token>" $B/auth/me
curl -b jar -c jar -X POST $B/auth/refresh     # novo access token; o cookie é rotacionado
curl -b jar -X POST $B/auth/logout
```

- **Access token** (JWT, 15 min) em memória no frontend + **refresh token** em cookie `httpOnly` (rotativo; reutilizar um token antigo derruba a sessão inteira).
- Papéis: `viewer` só lê (todo `GET`); `admin` faz tudo. `API_TOKEN` continua existindo como token de serviço (admin) para scripts.
- 5 senhas erradas seguidas bloqueiam a conta por 15 min; trocar a senha desloga todos os dispositivos.
- Sem `JWT_SECRET`/`API_TOKEN` a API só funciona aberta com `APP_ENV=local`; em qualquer outro ambiente ela nem sobe.

## Endpoints pensados para o frontend

- `GET /system/capabilities` — o live é possível neste ambiente? Se não, `live_blockers` diz por quê. Também lista exchanges e estratégias registradas (sem segredos).
- `GET /bots/summary` — equity, PnL e taxas somados **por modo e moeda de cotação** (paper, testnet e live nunca se misturam).
- Listas que crescem (`/audit-events`, `/bots/{id}/orders`, `/bots/{id}/signals`, `/backtests`) aceitam `limit` + `offset` e devolvem o total no header `X-Total-Count`; a auditoria também filtra por `event_type`.
- `can_write` no usuário (`/auth/me`, login): se o usuário pode alterar algo.

## Fase 5 — trading live (DINHEIRO REAL)

> Desligado por padrão. Nada neste repositório envia ordem real sem que você ligue, de propósito, **todas** as travas abaixo. Leia [docs/architecture/13-live-trading.md](docs/architecture/13-live-trading.md) antes. O caminho live foi testado só contra uma conta *simulada*; **comece com tetos minúsculos**.

Travas (resumo): `LIVE_TRADING_ENABLED=true` + `APP_ENV=prod` + os três tetos (`LIVE_MAX_ORDER_NOTIONAL`, `LIVE_MAX_TOTAL_EXPOSURE`, `LIVE_MAX_DAILY_LOSS`) no worker; chave **só de trade** (sem saque/transferência, restrita por IP) verificada pelo worker; bot promovido por endpoint próprio, com histórico limpo de paper (`LIVE_MIN_PAPER_DAYS`); e uma aprovação de **uso único**, digitando o nome do bot, exigida a **cada** partida.

```bash
H="Authorization: Bearer $TOKEN"
# 1. Conexão live (a chave fica 'pending' até o worker verificar o que ela pode fazer)
curl -H "$H" -X POST $B/exchange-connections -H 'content-type: application/json' \
  -d '{"environment":"live","confirm_real_money":true,"label":"binance-live","api_key":"...","api_secret":"..."}'
# 2. Promover um bot parado (com paper rodado) e ver o checklist
curl -H "$H" -X POST $B/bots/<id>/promote-to-live -H 'content-type: application/json' -d '{"connection_id":"<conexao>"}'
curl -H "$H" $B/bots/<id>/live-readiness
# 3. Aprovar (digite o nome exato do bot) e iniciar com o token devolvido
curl -H "$H" -X POST $B/bots/<id>/live-approvals -H 'content-type: application/json' -d '{"confirm_name":"<nome do bot>"}'
curl -H "$H" -X POST $B/bots/<id>/start -H 'content-type: application/json' -d '{"confirmation_token":"<token>"}'
```
