# Integração com a Binance Demo

## Objetivo e escopo

Este documento descreve a seleção de ambiente, credenciais e fluxos Binance Demo implementados
neste projeto. A Demo serve para validar integração com fundos simulados. Ela não é a conta live e
seus resultados não demonstram que uma estratégia será lucrativa em produção.

Produtos contemplados:

- Spot Demo via `binance` e REST `https://demo-api.binance.com/api`.
- USDⓈ-M USDT perpetual via `binance-usdm` e REST `https://demo-fapi.binance.com`.
- Futures isolado, modo one-way, posição direcional única por bot e alavancagem de 1x a 10x.

As credenciais ficam no cadastro protegido de conexões. Nunca as copie para código, `.env`, logs,
issues, screenshots ou documentação. Não habilite permissão de saque. Restrinja os IPs permitidos
quando o ambiente de execução tiver IP estável.

## Estado de liberação

Spot Demo pode ser executado com `TESTNET_TRADING_ENABLED=true` no worker e uma conexão `demo`.
USD-M Futures paper é um simulador local que precisa de uma conexão USD-M Demo ativa para ler dados
da conta e as leverage tiers; requer `FUTURES_PAPER_ENABLED=true`. Futures Demo agora tem um trader
separado que grava intents e envia ordens pelo `OrderExecutor`; exige `TESTNET_TRADING_ENABLED=true`,
conexão `binance-usdm` / `demo`, margem disponível suficiente e configuração isolada confirmada.
Essa implementação ainda precisa passar os cenários de recuperação e fault injection do plano e
ser validada em conta Demo antes de ser considerada liberada. Futures live permanece bloqueado.
Uma conexão válida e um teste paper não comprovam execução Demo.

## Hosts e ambientes

| Produto e ambiente | REST | WebSocket | Uso no projeto |
|---|---|---|---|
| Spot Demo | `https://demo-api.binance.com/api` | `wss://demo-ws-api.binance.com/ws-api/v3`; streams `wss://demo-stream.binance.com/ws` ou `/stream` | `environment=demo`, exchange `binance` |
| USD-M Demo | `https://demo-fapi.binance.com` | `wss://demo-fstream.binance.com` | `environment=demo`, exchange `binance-usdm` |
| Spot live | `https://api.binance.com/api` | Hosts live Spot | `environment=live` |
| USD-M live | `https://fapi.binance.com` | Hosts live USD-M | `environment=live` |
| Sandbox/testnet do CCXT | Host selecionado pelo sandbox do CCXT | Conforme CCXT | `environment=testnet`; distinto da Demo Binance |

A documentação oficial Spot chama o produto de **Demo Mode**. A documentação USD-M ainda lista as
URLs Demo na seção **Testnet API Information**. Neste projeto, `demo` seleciona explicitamente
`demo-api.binance.com` ou `demo-fapi.binance.com`; não significa live nem o sandbox genérico do
CCXT. O adaptador confere os hosts configurados antes de disponibilizar um cliente Demo e rejeita
configuração incoerente entre sandbox e Demo. Dados públicos de mercado podem vir dos endpoints
públicos normais; saldo, ordens e configuração privada usam a conexão autenticada Demo.

## Criar e cadastrar credenciais

1. Entre na [Binance Demo](https://demo.binance.com/en/futures/BTCUSDT) e crie uma API key no
   gerenciamento de chaves do produto pretendido.
2. Habilite leitura e trading apenas para o produto necessário. Para Futures, a chave precisa ter
   permissão USDⓈ-M Futures; uma chave Spot não substitui a permissão Futures.
3. Deixe saques desativados e aplique restrição de IP quando possível.
4. Na aplicação, crie uma conexão Binance com ambiente **Demo** e selecione `binance` para Spot ou
   `binance-usdm` para USDⓈ-M Futures.
5. Insira API Key e Secret nos campos protegidos da conexão. Não reutilize uma chave live.
6. Use **Verificar/Revalidar conexão** (`POST /api/v1/exchange-connections/{id}/recheck`). Para
   Demo/testnet, essa ação confirma leitura autenticada no host escolhido; não envia ordem e não
   prova, sozinha, permissão de trading.

Se uma key ou secret aparecer em screenshot, terminal, log ou mensagem, revogue a chave na Binance
e cadastre outra. Considere comprometidos os valores visíveis no screenshot de credenciais enviado
nesta conversa.

## Configuração local

O `.env.example` traz os opt-ins desligados por padrão. No worker que deve executar Spot Demo:

```dotenv
ENABLED_EXCHANGES=binance,binance-usdm
TESTNET_TRADING_ENABLED=true
```

Esse opt-in autoriza modos de bot que enviam ordens a uma conta Demo/testnet, conforme a integração
e os bloqueios por produto. Ele não altera o host das conexões. Para simular USD-M Futures paper,
ative separadamente `FUTURES_PAPER_ENABLED=true` somente no worker local pretendido e cadastre uma
conexão ativa `binance-usdm` / `demo`. O simulador não envia ordens Futures. Em ambiente live, o
opt-in e as aprovações live são independentes; Futures live permanece bloqueado.

## Smoke test USD-M Futures Demo

O smoke test opt-in `tests/smoke/test_binance_usdm_demo.py` valida a conta real de Demo em dois
round trips, um long e um short: configura margem isolada e 2x para o símbolo escolhido, envia
uma entrada pequena (notional limitado a 50 USDT), recebe o evento privado
`ORDER_TRADE_UPDATE`, confirma a posição, arma e cancela um stop nativo e fecha com `reduce-only`.
Se uma asserção falhar depois da entrada, o `finally` tenta cancelar ordens abertas e fechar a
exposição residual. O teste recusa contas com posição/ordens prévias no símbolo e exige mark price
com até 15 segundos.

Use uma conta USD-M Demo dedicada, sem outras ordens no símbolo. As chaves ficam em variáveis de
ambiente temporárias e não devem ser salvas no repositório, `.env` ou histórico do terminal:

```powershell
$env:BINANCE_USDM_DEMO_API_KEY = "<demo-api-key>"
$env:BINANCE_USDM_DEMO_API_SECRET = "<demo-api-secret>"
$env:BINANCE_USDM_DEMO_ORDER_SMOKE = "I_UNDERSTAND_DEMO_ORDERS"
$env:BINANCE_USDM_DEMO_SYMBOL = "BTC/USDT:USDT"
cd api
uv run pytest tests/smoke/test_binance_usdm_demo.py -m smoke -s
```

Ou use `make test-demo-futures` dentro de `api`. Sem as duas chaves e o valor de opt-in exato,
o teste fica ignorado. Ele usa apenas o host Demo e não precisa de `TESTNET_TRADING_ENABLED`.
Mesmo passando, esse smoke isolado não substitui a validação completa de restart, funding,
recuperação e kill switch exigida pelo plano.

## Verificações de partida para USD-M

Antes de uma sessão USD-M, a aplicação valida produto linear ativo e liquidado em USDT, símbolo
canônico como `BTC/USDT:USDT`, tiers de alavancagem para o notional, conta legível, modo Single-Asset,
modo one-way, ausência de posição e de ordens abertas no símbolo, margem isolada e alavancagem
solicitada. Multi-Assets Mode não é convertido automaticamente e impede a inicialização. Uma
configuração que não possa ser confirmada no host Demo falha fechada. O produto não oferece cross
margin, hedge mode ou COIN-M nesta entrega. A resposta de conta diferencia os totais USDT de
Single-Asset dos totais em USD de Multi-Assets; consulte [Account Information](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account)
e [Get Current Multi-Assets Mode](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account#get-current-multi-assets-mode).

O cadastro da conexão e seu recheck são operações de leitura; eles não alteram margem/alavancagem e
não enviam ordens. Alterações de configuração USD-M e ordens de exchange seguem os gates do plano.

## Ordens, stops e resultados ambíguos

- Uma escrita que tenha resultado desconhecido não é reenviada automaticamente. Consulte a ordem
  pelo client order ID e reconcilie antes de qualquer nova tentativa.
- HTTP 503 não tem uma única semântica: a Binance distingue timeout com resultado desconhecido de
  indisponibilidade que falhou. Trate o texto/código retornado e não crie uma ordem duplicada.
- HTTP 429 requer backoff; insistir após limite pode resultar em HTTP 418 e bloqueio do IP.
- Stops condicionais USD-M usam a rota Binance Algo Order atual. O adaptador marca a ordem para o
  CCXT encaminhar a criação a `/fapi/v1/algoOrder`, usa `triggerPrice`/`MARK_PRICE` e consulta ou
  cancela pelo client algo ID. Verifique esse mapeamento ao atualizar a versão do CCXT.
- Antes de criar uma entrada Futures Demo, o sinal precisa produzir um stop-loss válido para
  long/short; sem stop ou com stop/target do lado errado, o bot rejeita o sinal antes de criar a
  ordem. Configure o stop na estratégia (por exemplo, `stop_loss_pct` na mean reversion).
- Uma posição, stop ou fechamento só é considerado confirmado depois de resposta/consulta da
  Binance e reconciliação com o estado persistido.

## Funding histÃ³rico para backtests

O endpoint USD-M `GET /fapi/v1/fundingRate` retorna `fundingTime`, `fundingRate`, `markPrice` e
`rateType` (`Regular` ou `Special`) em ordem ascendente; `startTime` e `endTime` sÃ£o inclusivos e
o limite por pÃ¡gina Ã© 1.000. A importaÃ§Ã£o e a consulta local mantÃªm o limite final inclusivo para
nÃ£o descartar um settlement exatamente no fechamento do Ãºltimo candle simulado. Veja a
[referÃªncia oficial do histÃ³rico de funding](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History).

`GET /fapi/v1/fundingInfo` expÃµe `fundingIntervalHours` para sÃ­mbolos com ajustes, mas nÃ£o inclui
uma sÃ©rie histÃ³rica datada desses intervalos. Por isso, eventos espaÃ§ados em uma hora sÃ£o aplicados
no seu horÃ¡rio observado, mas uma lacuna de duas horas nÃ£o prova se houve um settlement perdido ou
se o intervalo mudou. O backtest rejeita lacunas observadas maiores que oito horas e mantÃ©m a
cobertura histÃ³rica como `not_certified`; o intervalo reportado nÃ£o deve ser tratado como prova de
completude. Veja a [referÃªncia oficial de Funding Rate Info](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-Info).

## Funding efetivamente liquidado

Taxas históricas (`fundingRate`) são observações de mercado e servem à simulação paper. Para
reconciliar uma conta Demo, use o histórico de renda USD-M `GET /fapi/v1/income`, filtrado por
`incomeType=FUNDING_FEE` e pelo símbolo. O adaptador `binance-usdm` expõe essa leitura como
`fetch_funding_income(symbol, start, end, limit)`; preserva o valor assinado, horário, ativo e
`tranId` da Binance. Um valor negativo é funding pago e um positivo é funding recebido.

O consumidor deduplica por `tranId` e registra a liquidação real. O worker lê o evento
`ACCOUNT_UPDATE` com razão `FUNDING_FEE`, relaciona o símbolo e o horário ao histórico REST, e usa
o `isolatedWallet` informado para dividir a variação entre carteira e margem isolada. O total do
ledger muda pelo valor assinado efetivamente liquidado, uma única vez. A Binance mantém esse
histórico por apenas três meses. O backfill pagina até 1.000 itens por consulta e deduplica por `tranId`. Após queda ou reinício, o worker consulta até 89 dias e aplica entradas ausentes apenas quando a posição local não mudou depois dos eventos e a posição/margem atuais explicam o saldo. Ele não inventa snapshots históricos de margem isolada; se a história for ambígua, falha fechado e exige revisão. A reconciliação pausa o bot se a margem isolada divergir. Referências: [Get Income History](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Get-Income-History)
e [USD-M User Data Streams](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams).

## Stream privado Futures Demo e recuperação

O worker pede uma listen key no REST USD-M Demo e conecta ao caminho documentado
`wss://demo-fstream.binance.com/private/ws/<listenKey>`. O stream entrega eventos de conta,
posições, ordens comuns, ordens Algo, margin call e expiração da listen key; não há parâmetro
`events` nessa conexão. A listen key vale 60 minutos e o worker a renova a cada 30 minutos. A
conexão WebSocket dura no máximo 24 horas; após a desconexão, o worker reconcilia antes de conectar
novamente. A listen key é fechada ao encerrar o stream. Fontes:
[User Data Streams USD-M](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams)
e [informações gerais USD-M](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info).

Atualizações de ordem resolvem ordens pendentes e sincronizam stops rastreados no ledger antes de
comparar posições com a conta. `MARGIN_CALL`, alteração de configuração, expiração da listen key,
quebra do socket e falha de reconciliação pausam os bots Futures da conexão. A reconexão só ocorre
após pausa e reconciliação REST bem-sucedidas; uma ordem ainda ambígua mantém a recuperação fechada
até uma consulta REST conseguir resolvê-la ou o operador corrigir a divergência. Falhas são repetidas
com backoff. O worker não retoma um bot automaticamente depois da recuperação. Quando o operador
solicita retomada de uma sessão existente, o worker resolve ordens pendentes e exige reconciliação
limpa de posição, margem, modo e alavancagem. Se já existe posição própria confirmada, ele apenas lê
a configuração da conta e não altera margem/alavancagem; novas sessões continuam exigindo símbolo
sem posição nem ordem aberta.

A reconciliacao REST tambem inspeciona ordens USD-M abertas em toda a conta no startup, na recuperacao do stream e a cada 60 segundos. Isso detecta ordens manuais/sem dono em simbolos sem bot e pausa a conexao. A consulta global inclui ordens comuns e Algo; a Binance cobra peso 40 por endpoint quando `symbol` e omitido, entao essa verificacao nao roda a cada segundo. Contrato oficial: [Current All Open Orders](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade#current-all-open-orders) e [Current All Algo Open Orders](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade#current-all-algo-open-orders).

Toda inicializacao ou retomada de bot USD-M Demo resolve ordens pendentes da conexao e exige uma reconciliacao limpa antes de negociar. O preflight inclui posicoes e ordens em simbolos sem bot e bloqueia a inicializacao se houver qualquer ordem local pendente na conta. Bots Futures Demo que ainda nao estao totalmente parados compartilham a mesma carteira: a soma de `initial_capital` desses bots deve caber no saldo total USDT da conexao. Isso inclui bots pausados e pedidos de parada ainda nao concluidos. Cada bot novo tambem precisa do seu capital disponivel em USDT livre. Essa reserva conservadora evita que ledgers virtuais independentes comprometam duas vezes o mesmo saldo. Ela nao substitui limites de risco, margem isolada nem o monitoramento das ordens reais.

As consultas de bots para reconciliacao e alocacao sao filtradas no banco por conexao, sem limite global de pagina que possa omitir bots da mesma conta. A rota SAPI `/sapi/v1/account/apiRestrictions` tem host live `api.binance.com`; o adaptador USD-M recusa essa chamada em Demo/Testnet. O recheck de credenciais nesses ambientes usa leituras de conta autenticadas no host escolhido para a conexao, e a validacao de Futures exige permissao efetiva ao ler/configurar a conta USD-M. Fonte: [Get API Key Permission](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account#get-api-key-permission).

Os testes locais verificam rota Demo, eventos inscritos, renovação e fechamento da listen key,
sincronização de stop antes da reconciliação e espera por reconciliação após falha. Esses testes não
substituem a validação runtime contra uma conta Binance Demo. O gate de execução Futures Demo segue
aberto até confirmar ordem, stop, restart, evento, recuperação e reconciliação no ambiente Binance.

## Kill switch e fechamento manual

O kill switch normal pausa bots e bloqueia novas entradas. O modo explícito de fechamento Futures
rastreado cancela ordens de abertura e tenta fechar posições Demo com `reduce-only`, preservando a
auditoria. Em paper, encerra apenas a posição simulada. Se houver ordem ambígua, falha de cancelamento,
ou falha ao rearmar proteção, o sistema não declara a posição encerrada e requer reconciliação.

O fechamento manual USD-M pausa o bot. Em paper, simula o fill no mark price atualizado, incluindo taxa e slippage. Em Futures Demo, grava uma ordem `reduce-only` durável e envia pela Binance; o resultado só entra no ledger após fill confirmado. Resultado desconhecido permanece pendente para reconciliação. Esse fechamento assistido não equivale à liberação da execução automatizada completa.

## Referências oficiais e diagnósticos

- [Binance Spot Demo Mode](https://developers.binance.com/en/docs/products/spot/demo-mode/general-info)
- [Binance USD-M Futures: General Info](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info)
- [Binance USD-M Futures: User Data Streams](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams)
- [Binance USD-M Futures: New Algo Order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order)
- [Binance USD-M Futures: Get Income History](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Get-Income-History)
- [Binance USD-M Futures: Change Initial Leverage](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Initial-Leverage)
- [CCXT: Sandbox and testnet](https://github.com/ccxt/ccxt/wiki/Manual#testnets-and-sandbox-environments)

| Sintoma | Verificações |
|---|---|
| Key inválida ou permissão negada | Produto Demo correto, leitura habilitada, par key/secret correto e sem espaços extras. |
| Spot funciona e USD-M não | Exchange `binance-usdm`, chave com permissão Futures e saldo na carteira USDⓈ-M Demo. |
| Host inesperado | Ambiente da conexão deve ser `demo`; confira o exchange selecionado e os logs sem imprimir credenciais. |
| Erro de assinatura/horário | Sincronize o relógio do worker e verifique o secret correspondente à key. |
| HTTP 429 ou 418 | Pare tentativas repetidas, reduza chamadas e aplique backoff. |
| HTTP 503 ao enviar ordem | Determine se foi timeout desconhecido ou falha; consulte client order ID antes de reenviar. |
| Futures paper não inicia | Confira `FUTURES_PAPER_ENABLED`, conexão ativa USD-M Demo, símbolo ativo e leverage tiers. |

Não há garantia de rentabilidade nem paridade automática entre Demo e live. Mantenha as ordens
automatizadas USD-M e o live bloqueados enquanto qualquer gate do plano permanecer sem evidência.
