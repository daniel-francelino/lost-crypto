# Livro 1 · Capítulo 1 — O quê, quem e por quê do trading quantitativo

*Quantitative Trading*, Ernest P. Chan (Wiley, 2009). As páginas são **páginas do livro** (página do PDF = página do livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **O1 (alertas no app) e O2 (atualização incremental de candles) implementados em 2026-10-31**; O3 a O5 não implementados. Ver "Estado da implementação" abaixo.

## 1. Resumo do capítulo (pp. 1–8)

Introdutório. Sem fórmulas. As afirmações são opiniões e anedotas do autor, não evidência.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Trading quantitativo = operações decididas estritamente por algoritmos testados no histórico; fundamentos e notícias contam se virarem números; padrões gráficos subjetivos não. | Separar estratégias codificáveis de opinião. | 1–2 |
| C2 | Estratégias simples; a matemática avançada não ajudou o autor (relato próprio de perdas em instituições). | Complexidade como fonte de perdas. | 2–3 |
| C3 | Manter poupança; não precisar de lucro imediato; os retornos têm seu próprio ritmo. | Pressão por resultados rápidos. | 4 |
| C4 | Escalar mudando a alavancagem; alerta contra alavancagem excessiva. | Escalonamento descontrolado. | 5 |
| C5 | A interferência manual muitas vezes piora os resultados; o autor admite a vontade de sair nas oscilações de P&L. | Intervenção humana. | 5–6 |
| C6 | Automatizar passo a passo: baixar dados, iniciar e parar programas, **alertar um celular/suporte quando algo der errado**. | Operar sem ficar olhando a tela. | 6–7 |
| C7 | A pesquisa deve continuar porque a concorrência corrói os lucros. | Decaimento da vantagem (edge). | 6–7 |
| C8 | Começar pequeno, crescer com o conhecimento. | Risco de ruína no início. | 4–5 |

O livro não discute cripto, mercados 24/7 nem taxas de corretora. Tudo sobre cripto abaixo é **adaptação nossa**.

## 2. Diagnóstico

| Conceito | Status | Evidência |
|---|---|---|
| C1 | ✅ | As estratégias são classes registradas; os sinais são intenções explícitas. |
| C2 | ⚠️ | Catálogo pequeno; não há medida comparando estratégias simples e complexas. |
| C3/C8 | ✅ | Paper → testnet → live, limites no live, mínimo de dias em paper, aprovação digitando o nome. |
| C4 | n/a | Apenas spot; sem alavancagem. Existem limites de exposição, mas não uma política de alavancagem. |
| C5 | ⚠️ | `pause`/`stop`/`reset` são auditados, mas nenhum motivo é registrado e não existe métrica de intervenção. |
| C6 dados | ✅ parcial (O2) | O worker agora estende os candles gravados até o último candle fechado; a importação histórica segue manual e os bots ainda buscam candles direto da exchange. |
| C6 **alertas** | ✅ in-app (O1) | Antes: nenhum canal de notificação (busca por `alert`, `notif`, `webhook`, `telegram`, `email`, `smtp` em `api/src` não achou nada). Agora: módulo `notifications`, endpoints `/alerts` e indicador no app. Não há canal externo. |
| C7 | ✅ | Backtest, sweep e comparação existem. |

## 3. Oportunidades

### O1 — Alertas de falha *(livro: C6, p. 7 · canal e gatilhos são adaptação nossa)*
* **Problema:** worker parado, heartbeat de bot desatualizado, kill switch acionado, divergência na reconciliação, ordem live rejeitada e limite diário atingido passam despercebidos sem alguém olhando.
* **Decisão do operador:** o **canal inicial é a própria aplicação**: os alertas são vistos no front, sem serviço externo (sem webhook, chat ou e-mail) e, portanto, sem segredo de canal novo. Canais externos continuam possíveis depois, pela mesma porta, mas não fazem parte do primeiro escopo.
* **Proposta:** uma porta `Notifier` com uma implementação por canal, um arquivo por integração. A primeira implementação, `in_app`, **grava o alerta no banco**; a API expõe a lista (mais recentes primeiro), a contagem de não lidos e a ação de marcar como lido; o front mostra um indicador de não lidos (ícone/contador no layout) e uma lista de alertas, atualizados por polling como o restante do app. Um avaliador no worker emite eventos de alerta com deduplicação, cooldown e mensagem de recuperação. Os críticos também vão para o log de auditoria.
* **Dados do alerta (rascunho):** tipo, severidade, bot/par quando houver, mensagem, momento de criação, momento de recuperação (quando o problema some), lido/não lido. Um alerta por episódio: o mesmo problema não cria alertas repetidos enquanto estiver aberto; a recuperação fecha o episódio.
* **Benefício:** falhas percebidas em minutos por quem está com o app aberto, sem depender de serviço externo.
* **Complexidade:** média (tarefa periódica no worker, tabela, endpoints e interface no front). Mais simples que um canal externo por não ter segredo, mas com trabalho de front.
* **Riscos:** **só avisa quem está olhando o app**; com o app fechado, o alerta fica esperando no banco e ninguém é chamado (limitação aceita nesta decisão). O caminho do alerta morre junto com o worker (precisa de uma checagem externa de vida, por exemplo healthcheck do container, que no canal in-app só aparece quando o app for aberto); fadiga de alertas e crescimento da tabela (prever retenção/limpeza de alertas antigos).
* **Validação:** testes unitários de limites e deduplicação; teste de integração que para o worker e espera um alerta gravado e visível na API; teste de que marcar como lido e a recuperação do episódio funcionam; teste do front para o contador e a lista; nenhum dado sensível em logs/API.

#### Detalhamento do O1: o que implementar (planejamento original; implementado, ver "Estado da implementação")

**Pontos verificados no código que moldam o desenho**
* O worker é um laço em `worker.py` que chama `JobRunner.run_once()` (`container.py`): uma passada do supervisor e depois no máximo um job. O avaliador de alertas entra como mais uma etapa nessa passada, na mesma linha do supervisor.
* O status de saúde já existe: `GET /system/status` devolve `worker` (vivo, último heartbeat, idade) e `stale_bots` (`risk_management/presentation/router.py`). O avaliador deve **reaproveitar essa lógica**, não duplicá-la.
* **O worker não consegue avisar que ele mesmo parou.** O alerta "worker parado" precisa ser calculado no processo da **API** (por exemplo ao listar/contar alertas, ou numa tarefa na própria API); os demais (bot parado, divergência na reconciliação, ordem rejeitada, limite diário, kill switch, cobertura de candles defasada) podem ser emitidos pelo worker. **Decisão tomada na implementação (ver abaixo):** onde avaliar "worker parado".
* O módulo `audit` (`models.py`, `orm.py`, `repository.py`, `service.py`, `router.py`) é o molde mais próximo: tabela com `BigInteger` autoincremento, `occurred_at` com `server_default=func.now()`, `bot_id` sem FK, `payload` JSONB, listagem mais recente primeiro com `limit`/`offset` e total em `X-Total-Count` (`core.pagination`). O módulo `bots` usa o layout `domain/application/infrastructure/presentation`; como o de alertas tem regras (episódios, deduplicação), seguir o layout maior.
* Rotas protegidas em `api_router.py`: `require_access` libera leitura para qualquer papel e exige `admin` para alterar estado. Marcar como lido é uma alteração; **decisão tomada:** só o `admin` marca como lido (o `viewer` cairia em 403).
* A última migração era a `0007_live_trading.py`; a das alertas foi criada como `0008` e, depois do merge com as migrações `0008` a `0011` dos capítulos 2 a 5, renumerada para `0012_alerts`. O ORM novo precisa ser importado em `orm_models.py`.

**Backend**
1. **Domínio** (`modules/notifications/domain`): `Alert` (id, `kind`, `severity`, `bot_id` opcional, `dedupe_key`, mensagem, `payload`, `opened_at`, `resolved_at` opcional, `read_at` opcional), enums `AlertKind` e `AlertSeverity`, e a regra de episódio: existe no máximo um alerta **aberto** por `dedupe_key`; reemitir enquanto aberto não cria outro; a recuperação preenche `resolved_at`.
2. **Porta e avaliador** (`application`): `Notifier` (porta) com `in_app` e um falso para testes; `AlertEvaluator` recebe as condições (worker/bots parados, kill switch, divergência da reconciliação, ordem live rejeitada, limite diário atingido, cobertura defasada do O2, peso de requisição alto do O2), com **cooldown** e mensagem de recuperação. Falha ao gravar ou notificar é capturada e registrada em log, nunca derruba o worker.
3. **Persistência** (`infrastructure`): tabela `alerts` com índice parcial/único para "um alerta aberto por `dedupe_key`" e índice por `opened_at`; repositório SQLAlchemy; **retenção** (limpar alertas resolvidos e lidos após N dias, valor em `core/config.py`).
4. **API** (`presentation/router.py`, registrado em `api_router.py` com `_protected`): `GET /alerts` (filtros `unread`, `severity`, `bot_id`, `limit`, `offset`, total em `X-Total-Count`), `GET /alerts/unread-count`, `POST /alerts/{id}/read` e `POST /alerts/read-all`. Resposta sem dado sensível. Atualizar `api/docs/openapi.json`.
5. **Integração:** `container.py` (construir o serviço e o avaliador e passá-los ao `JobRunner`), `worker.py` (nada a mudar além de a passada chamar o avaliador), `core/config.py` (intervalo do avaliador, cooldown, retenção), `orm_models.py` (importar o novo ORM), migração `0008`.
6. **Auditoria:** alertas de severidade crítica também geram evento em `audit_events` (como já está previsto no O1).
7. **Testes:** unitários (episódio, deduplicação, cooldown, recuperação, retenção), integração (parar o worker simulado e esperar o alerta; marcar como lido), de API (papéis, paginação, `X-Total-Count`), e que o fluxo de ordens e as salvaguardas do live seguem inalterados.

**Frontend** (regras de `app/AGENTS.md`; UI em português do Brasil, código e rotas em inglês)
1. **Contrato:** rodar `npm run api:types` depois de atualizar o OpenAPI; adicionar `AlertKind` e `AlertSeverity` em `lib/shared/enums.ts` (`as const`, `z.nativeEnum`) e conferir com `npm run check:consistency`.
2. **Constantes:** `AppRoute.Alerts = "/alerts"` em `lib/shared/routes.ts`; chaves `QueryKey` para a lista e para o contador (`lib/shared/api/query-keys.ts`); o contador usa `Poll.Status` (5 s) e a lista `Poll.Overview` (10 s), de `lib/shared/polling.ts`.
3. **Camada de dados compartilhada** (o contador aparece na barra do layout, que só pode importar de `shared`): `lib/shared/alerts/alerts.api.ts` (schemas zod, chamadas e tipos) e `hooks/shared/use-alerts.ts` (consulta da lista, do contador e as mutações de marcar como lido), no mesmo molde de `lib/shared/system/system.api.ts` e `hooks/shared/use-system.ts`.
4. **Indicador de não lidos:** novo componente em `components/shared/layout` ao lado da `safety-strip.tsx`, com contador **em número e texto acessível** (estado nunca só por cor), levando à tela de alertas; mostra o tempo desde a última atualização e a marca de dado desatualizado quando o polling falha.
5. **Tela de alertas:** `routes/_app/alerts/index.tsx` (a rota só monta a tela) e `components/alerts/alerts-page.tsx` com `DataTable` (severidade, tipo, bot, mensagem, aberto em, resolvido em, lido), filtros "não lidos" e severidade, ações "marcar como lido" e "marcar todos", paginação com "mostrando os últimos N" quando aplicável. Estados obrigatórios: esqueleto, erro com nova tentativa, vazio, sem resultados e dados. Datas apenas por `lib/shared/dates.ts`, com UTC explícito.
6. **Navegação e permissões:** entrada "Alertas" na seção "Sistema" em `components/shared/layout/nav-config.tsx`, `breadcrumbs.ts`, e a regra de papéis (visualização para todos; marcar como lido conforme a decisão tomada acima (só admin), com o botão ausente para quem não pode, como no restante do app).
7. **Resumo no painel e na página de status:** o painel "Atenção" do dashboard e a página `/system` passam a mostrar os alertas abertos mais recentes (o painel hoje já lista bots em erro, bots parados, kill switch e conexões inválidas).
8. **Módulo novo:** `alerts` não está na lista de módulos de `app/AGENTS.md`; adicionar o módulo ali, em `docs/02-project-structure.md` e na regra de fronteira do ESLint, ou colocar a tela dentro de `system`. **Decisão tomada na implementação (ver abaixo):** a tela ficou no módulo `system`.
9. **Testes e documentos:** vitest (schemas, formatação, hook do contador), teste de ponta a ponta no Playwright (alerta aparece, contador sobe, marcar como lido zera) e verificação visual a 360 px; `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`. Atualizar na mesma mudança `app/docs/06-screens.md` (nova seção da tela e do indicador), `app/docs/02-project-structure.md` e `app/docs/09-roadmap.md`.

**Decisões que estavam pendentes (resolvidas na implementação, ver "Estado da implementação")**
* Onde avaliar "worker parado" (processo da API) e quais condições entram no primeiro corte.
* Se o `viewer` pode marcar alertas como lidos.
* Módulo `alerts` novo no front ou tela dentro de `system`.
* Prazo de retenção e cooldown padrão.

#### Estado da implementação (2026-10-31)

**O que foi feito.** Backend: módulo `api/src/modules/notifications` (domínio, avaliador de episódios, condições puras, serviço e monitor, ORM e repositório, router), migração `0012_alerts`, atualizador de candles `market_data/application/updater.py`, tratamento de 429/418 no cliente CCXT, novas configurações em `core/config.py` (documentadas em `api/.env.example`) e `docs/openapi.json` atualizado. Frontend: enums, rota, chaves de consulta, camada compartilhada (`lib/shared/alerts`, `hooks/shared/use-alerts.ts`), indicador na barra de segurança, tela `/alerts` e entrada "Alertas" no menu "Sistema".

**Decisões que eu tomei no lugar das pendentes** (padrões conservadores, fáceis de mudar):
* **Worker parado** é calculado no processo da **API** (tarefa em segundo plano iniciada no `lifespan`, a cada 15 s). As demais condições são avaliadas pelo **worker**.
* **Condições do primeiro corte:** worker parado, bot sem heartbeat, bot em erro, kill switch ativo, candles atrasados e exchange limitando requisições (429/418). **Ficaram de fora:** ordem live rejeitada, divergência na reconciliação e limite diário atingido, que exigem novos pontos de emissão no trader e no reconciler.
* **Severidade:** crítico para worker parado e para bots em modo live; aviso para o resto. Episódios críticos geram os eventos de auditoria `alert.opened` e `alert.resolved`.
* **`viewer`:** só leitura; marcar como lido é ação de `admin` (a regra existente: qualquer escrita exige admin).
* **Front:** a tela fica no módulo `system` (sem módulo novo `alerts`); a camada de dados fica em `shared` porque o indicador faz parte do layout.
* **Números:** avaliação a cada 15 s, cooldown de 5 min (uma condição que volta dentro desse prazo reabre o mesmo alerta, como não lido), retenção de 30 dias para alertas resolvidos e já lidos.

**Diferenças em relação ao plano acima:**
* O contador é `GET /alerts/summary` (`unread`, `open`, `critical_open`), no lugar de `/alerts/unread-count`.
* O2: a verificação roda a cada **30 s**, mas cada série só faz requisição quando o candle seguinte fechou (mais 5 s de folga), ou seja, cerca de uma requisição por minuto por série de 1 minuto.
* O2: são atualizadas as séries **já gravadas** cujo último candle tem até 7 dias, ou que são usadas por um bot não parado; uma série vazia nunca é preenchida automaticamente. Lacunas na janela recente (500 candles) são refeitas a cada 10 min.
* O2: um 429/418 vira `RateLimited` e a exchange fica pausada pelo `Retry-After` (60 s se ele não vier). Isso **muda o comportamento do cliente CCXT para todas as leituras**: antes, um 429 era repetido depois de 1, 2 e 4 s.
* O2: o peso usado (`x-mbx-used-weight-1m`) só gera **aviso em log** a partir de 3.000 (50% do limite de 6.000); **não há alerta por peso**, apenas por 429/418 e por candle atrasado.
* Os bots continuam buscando candles direto da exchange; a leitura pelo banco segue como etapa posterior.

**Verificação:** `ruff` e `mypy` (strict) limpos; backend com 323 testes passando contra o banco de teste (26 novos: episódios, condições, atualizador, 429, API e worker); app com `lint`, `typecheck`, `format:check`, `check:consistency`, 52 testes `vitest` e `build` passando. A tela foi aberta em um Chromium real (desktop e 360 px) contra uma API descartável: listagem, marcar como lido e o indicador funcionaram. **Não rodei** os testes Playwright do projeto (`npm run e2e`) nem testei contra a Binance real. Na barra do topo a 360 px sobra um estouro de ~3 px quando o worker está parado; ele já existia antes dos alertas e não foi tratado aqui.

**Para usar no ambiente de desenvolvimento** (nada disso foi feito por mim): reconstruir as imagens `api` e `worker` e rodar `alembic upgrade head` no banco de desenvolvimento (a migração `0012_alerts` e as `0008` a `0011` só foram aplicadas no banco de teste). Alertas só avisam quem abre o app.

### O2 — Importação incremental automática de dados *(livro: C6, pp. 6–7 · adaptação)*
* **Problema:** lacunas nos candles armazenados só são reparadas por jobs manuais.
* **Proposta:** uma tarefa periódica no worker que estende a cobertura dos pares ativos até o presente, reutilizando o job de importação; recuar (backoff) em lacunas de manutenção da exchange.
* **Benefício:** backtests sempre rodam com dados atuais.
* **Complexidade:** baixa. **Riscos:** limites de taxa (rate limits); lacunas legítimas sendo tentadas para sempre.
* **Validação:** teste de integração com uma fonte falsa que deixa um buraco e espera que ele seja preenchido.

#### Detalhamento do O2 (planejamento original; implementado, ver "Estado da implementação")

**Situação verificada no código**
* O trader busca candles direto da exchange a cada ciclo (`trader.py:128`, `FETCH_LIMIT = 1000`) e os usa só na memória; eles não são gravados na tabela de candles. O banco só tem o que foi importado à mão (`market_data/application/service.py`, `BATCH_SIZE = 1000`).
* O trader já evita chamadas à toa: só busca quando o próximo candle deve ter fechado (`trader.py:121`).

**Frequência**
* **Uma vez por minuto**, com uma pequena folga depois do fechamento do candle. O menor timeframe é 1 minuto e as estratégias só agem em candle fechado, então 30 segundos não traria candle fechado a mais.
* Candle em formação (gráfico ao vivo) fica **fora do escopo**: exige distinguir candle aberto de fechado e há risco de gravar candle incompleto. Só tratar se for pedido.

**Escopo da tarefa**
1. Tarefa periódica no worker: para cada par e timeframe ativo, buscar desde o último candle gravado até agora e gravar **apenas candles fechados**.
2. Gravação idempotente (sem duplicar candles); se houver buraco no meio, completar a partir do primeiro candle faltante, não só do último.
3. Reaproveitar o job de importação existente em vez de criar um segundo caminho de gravação.
4. Backoff crescente em lacunas de manutenção da exchange; lacunas legítimas não são tentadas para sempre.
5. A leitura dos candles pelos bots a partir do banco fica como **etapa separada e posterior** (mudança maior no trader).

**Limites de requisição da Binance (verificado em 2026-10-31)**
* Spot: **6.000 de peso por minuto, por IP** (lido em `rateLimits` do `exchangeInfo` da mainnet; a documentação manda consultar o endpoint, então o valor pode mudar). O `GET /api/v3/klines` custa **2 de peso**, até 1.000 candles por chamada.
* Atualizar N pares por minuto custa cerca de 2 × N de peso: 50 pares = ~100 de peso/min (~1,7% do limite). Para estourar seriam necessários mais de ~2.900 pares.
* O maior consumo é a importação histórica: um ano de candles de 1 minuto são ~526 lotes (~1.050 de peso) por par.
* **429:** esperar o tempo do cabeçalho `Retry-After`. **418:** banimento automático do IP (de 2 minutos a 3 dias) se insistir depois de um 429; como é por IP, derrubaria também os bots que operam.
* O cliente já usa CCXT com `enableRateLimit` (`ccxt_exchange.py:64`), mas isso só enxerga o próprio processo; API e worker no mesmo IP contam separadamente na Binance. Erros de limite viram `TransientExchangeError` no caminho de ordens (`ccxt_exchange.py:245`); **não verifiquei** se a leitura de candles faz o mesmo. Não encontrei espera baseada em `Retry-After` nem leitura do cabeçalho de peso usado.
* Não consultei os limites da testnet.

**Medidas de proteção previstas**
* Em caso de 429, aguardar o `Retry-After` e **nunca** tentar de novo antes; sem esse tempo, não repetir a chamada.
* Ler `X-MBX-USED-WEIGHT-1M` e registrar o peso usado; alertar (ligado ao O1) se passar de, por exemplo, 50% do limite.
* Importação histórica em fila separada, com limite de concorrência, para não competir com a atualização por minuto.
* Alerta (O1) se a cobertura de um par ficar mais de N minutos defasada.

**Riscos adicionais**
* Gravar candle incompleto; separar testnet de mainnet na mesma tabela (confirmar como a tabela distingue as duas antes de gravar).
* Duplicação de busca enquanto os bots ainda buscam por conta própria (some quando os bots lerem do banco).

**O que implementar no backend**
1. `market_data/application/service.py`: serviço de atualização incremental (último candle gravado → agora, só candles fechados, idempotente, completando buracos), reaproveitando o importador de `BATCH_SIZE = 1000`.
2. `container.py`: uma etapa nova no `JobRunner.run_once()` (hoje: passada do supervisor e depois um job da fila), executada no máximo uma vez por intervalo (~60 s) para não rodar a cada volta do laço do worker (`worker_poll_seconds = 2.0`).
3. `exchanges/infrastructure/ccxt_exchange.py`: tratar 429/418 na leitura de candles (`fetch_candles`, linha 99) como erro transitório com espera pelo `Retry-After`, e ler o peso usado.
4. `core/config.py`: intervalo da atualização, folga após o fechamento do candle, limiar de alerta de peso e tolerância de defasagem.
5. Condições de alerta (O1): cobertura defasada e peso alto.
6. Testes: fonte falsa com buraco, resposta 429 falsa, idempotência, nenhum candle em formação gravado.

**O que implementar no frontend**
* Nada é obrigatório: a página de dados de mercado já consulta a cobertura (`market-data-page.tsx`) e passaria a mostrar a cobertura mais recente sem mudança de código. Opcional: exibir na tela de dados de mercado o horário do último candle gravado por par, para o operador ver que a atualização está viva. Os avisos de defasagem aparecem pelo canal de alertas do O1.

**Arquivos afetados (além dos já listados)**
* `exchanges/infrastructure/ccxt_exchange.py` (tratamento de 429/`Retry-After` e peso usado na leitura de candles), `core/config.py` (intervalo e limiar de alerta de peso).

**Critérios de aceite**
* Com um par ativo, o banco acompanha a exchange com atraso de no máximo ~1 candle fechado.
* Nenhum candle em formação é gravado; reexecutar a tarefa não cria duplicatas.
* Um buraco injetado numa fonte falsa é preenchido; uma resposta 429 falsa faz a tarefa esperar o `Retry-After` sem nova chamada antes disso.
* O peso usado fica visível em log/métrica; nenhum segredo vaza.
* Fluxo de ordens e salvaguardas do live inalterados; testes, ruff e mypy verdes.

### O3 — Motivo das intervenções manuais *(livro: C5, pp. 5–6 · adaptação)*
* **Problema:** não dá para saber se um stop/pause/reset foi reação a oscilações de P&L.
* **Proposta:** motivo opcional nesses comandos, guardado no payload de auditoria, mais um indicador de "intervenções por bot".
* **Benefício:** dados sobre o nosso próprio comportamento. **Complexidade:** baixa. **Risco:** um campo ignorado.
* **Validação:** teste de que o motivo chega ao evento de auditoria.

### O4 — Política de alavancagem/exposição *(livro: C4, p. 5 · adiado)*
Não existe alavancagem. Só passa a ser prioridade alta se futuros/margem forem adicionados; revisitar com o Capítulo 6.

### O5 — Comparação simples vs. complexo *(livro: C2, p. 3 · não acionável)*
Apoia-se em uma frase de opinião. Capítulos posteriores dão critérios concretos; não agir sobre este item.

## 4. Prioridade

| # | Item | Confiabilidade | Gestão de risco | Qualidade do backtest | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O1 alertas (canal in-app) | alta | alta | – | média | agendador do worker, tabela de alertas, front |
| 2 | O2 importação incremental | média | – | média | baixa | job de importação existente |
| 3 | O3 motivo da intervenção | baixa | média | – | baixa | auditoria existente |
| – | O4, O5 | adiados | | | | |

## 5. Arquivos afetados
* O1 backend: novo módulo `api/src/modules/notifications` (domínio, porta `Notifier` + `in_app`, avaliador, ORM e repositório, router), migração `0012_alerts`, `orm_models.py`, `api_router.py`, `container.py`, `core/config.py`, `api/docs/openapi.json`, testes em `api/tests`.
* O1 frontend: `lib/shared/enums.ts`, `lib/shared/routes.ts`, `lib/shared/api/query-keys.ts`, `lib/shared/alerts/alerts.api.ts`, `hooks/shared/use-alerts.ts`, indicador em `components/shared/layout` (ao lado de `safety-strip.tsx`), `components/shared/layout/nav-config.tsx` e `breadcrumbs.ts`, `routes/_app/alerts/index.tsx`, `components/alerts/alerts-page.tsx`, dashboard e `/system`, testes (vitest e Playwright), `app/AGENTS.md` e `app/docs/` (06, 02, 09) se o módulo `alerts` for criado.
* O2: `modules/market_data/application/service.py`, `container.py` (etapa no `JobRunner`), `exchanges/infrastructure/ccxt_exchange.py`, `core/config.py`; frontend opcional (horário do último candle por par).
* O3: `modules/bots/application/service.py`, router de bots, payload de auditoria, formulários de controle do app.

## 6. Plano incremental
1. O1a (backend): domínio do alerta, porta `Notifier`, notifier falso, avaliador de condições com deduplicação, cooldown e recuperação (sem persistência).
2. O1b (backend): canal `in_app`: migração `0012_alerts` (criada como `0008`), tabela e repositório, endpoints (listar, contar não lidos, marcar como lido), integração ao `JobRunner`/`container.py`, retenção, atualização do OpenAPI.
3. O1c (frontend): `api:types`, enums, rota e chaves de consulta, camada compartilhada (`alerts.api.ts` e hook), indicador de não lidos no layout, tela `/alerts`, entrada de navegação, resumos no dashboard e em `/system`, testes e atualização dos documentos do app.
4. (Opcional, depois) canal externo (webhook/chat) pela mesma porta, se o operador sentir falta de aviso com o app fechado.
5. O2: importação incremental periódica.
6. O3: campo de motivo.

## 7. Critérios de aceite e testes
* Um alerta por episódio em até N segundos após o rompimento do limite, mais uma mensagem de recuperação.
* O alerta fica gravado e aparece no front (contador de não lidos e lista) mesmo que o app seja aberto só depois; marcar como lido atualiza o contador.
* Um canal com falha (inclusive falha ao gravar o alerta) nunca derruba o worker; a falha é registrada em log.
* Nenhum dado sensível em logs, auditoria ou respostas da API.
* Fluxo de ordens e salvaguardas do live inalterados; testes unitários, de integração, ruff e mypy continuam verdes.

## Ressalva
As anedotas de lucro do autor (pp. 3, 8) são relatos pessoais e não devem ser usadas como expectativa de retorno.
