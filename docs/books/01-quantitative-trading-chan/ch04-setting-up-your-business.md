# Livro 1 · Capítulo 4 — Montando o seu negócio

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: **apenas análise**; nada implementado por este relatório. Diagnóstico revisado contra o código em 2026-10-31 (ver §2.1: a política de permissão das chaves já existia).

## 1. Resumo do capítulo (pp. 69–78)

Capítulo não técnico sobre o cenário de ações dos EUA (SEC Regulation T, NASD Series 7, SIPC). A maior parte não se transfere para um sistema cripto pessoal.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Corretora de varejo (gratuita, baixa alavancagem, com seguro) vs. mesa proprietária (alta alavancagem, regras impostas, sem seguro). Regras impostas podem funcionar como gestão de risco externa; liberdade irrestrita é um risco quando chega o "grande drawdown". | Escolher quem guarda o capital e quem impõe limites. | 69–71 |
| C2 | Escolher a corretora por mais que a comissão: velocidade de execução, acesso a liquidez, variedade de produtos e, acima de tudo, uma **API** para dados e ordens mais uma **conta de paper trading**. É possível usar várias contas para comparar a qualidade real da execução. | Custos de execução ocultos; impossibilidade de testar com segurança. | 71–74 |
| C3 | Risco de contraparte: verificar a solidez financeira da empresa, o registro e a reputação de devolver capital. | Perder capital por causa do custodiante. | 74 |
| C4 | A infraestrutura física pode começar leve (PC, banda larga, nobreak). Depois, **continuidade de negócio**: rodar os programas em servidor hospedado/colocalizado para evitar quedas de Internet/energia; monitorar remotamente. A latência soma slippage em mercados rápidos. | Indisponibilidade e latência. | 75–77 |
| C5 | Mais informação em tempo real não é automaticamente melhor (estudo de corridas de cavalos citado). | Excesso de informação. | 75–76 |

Sem conteúdo sobre cripto. Tudo sobre exchanges abaixo é **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C1 limites externos | ✅ | O live é protegido por limites do ambiente (`LIVE_MAX_ORDER_NOTIONAL`, `LIVE_MAX_TOTAL_EXPOSURE`, `LIVE_MAX_DAILY_LOSS`), kill switch, aprovação com nome digitado e `live_min_paper_days`. Ficam no ambiente do worker, não na API: o operador não os remove casualmente, como os limites de uma mesa proprietária. |
| C2 API + conta paper | ✅ | Binance spot e testnet atrás de `ExchangeRegistry`; venue paper (`execution/venues/paper.py`). |
| C2 comparar a execução | ❌ | Uma exchange só e nenhum registro de preço esperado × executado. Fica para o Cap. 5 (paridade paper × backtest, backlog B7). |
| C3 permissões das chaves | ⚠️ (parcial, **já existe**) | `permission_problem` (`exchanges/domain/connections.py`) recusa chaves live que **não podem negociar**, que **podem sacar**, que **podem transferir** ou, com `LIVE_REQUIRE_IP_RESTRICTION=true` (padrão), que não são restritas por IP. O worker verifica as chaves live criadas (`ConnectionResolver.verify_pending`): `pending → active` ou `invalid`. Lacunas: (a) a verificação acontece **uma única vez**; se alguém liberar o saque na Binance depois, o sistema não percebe; (b) o **motivo** da recusa vai só para a auditoria: `ConnectionOut` não o expõe e a tela de conexões mostra "inválida" sem dizer por quê; (c) as permissões verificadas não ficam guardadas; (d) chaves testnet não são verificadas (aceitável, sem dinheiro real). |
| C3 contraparte (quanto deixar na exchange) | ❌ | Nada orienta a deixar na exchange só o capital dos bots. Nenhuma tela mostra o saldo da conta contra o capital alocado. |
| C4 continuidade: processo | ⚠️ | `docker-compose.yml`: `restart: unless-stopped` em API e worker; healthcheck no Postgres e na API (`/health/live`); **o worker não tem healthcheck**. A reconciliação recupera ordens após uma queda. Os stops nativos (`native_stop_orders`, `trading/application/orders.py`) ficam na exchange e sobrevivem a uma queda do worker, **mas só se a estratégia mandou stop**: `require_stop_loss` é opcional, então pode haver posição aberta sem proteção nenhuma enquanto o host está fora. |
| C4 continuidade: dados | ❌ | Nenhum backup do Postgres, nenhum teste de restauração, nenhum runbook. `08-database.md` cita "backups encrypted" e "destructive migrations need a backup step", mas nada disso existe. |
| C4 monitoramento remoto | ⚠️ | O heartbeat do worker é gravado no banco e a tela Sistema mostra "worker parado" e bots sem heartbeat — mas só para quem abrir o app, e nada de fora da stack percebe a queda do host inteiro. `/health` só testa API + banco, não o worker. O canal de alertas do Cap. 1 (O1, in-app) está **decidido mas não implementado**. |
| C4 latência / relógio | ❌ | O trader decide "o candle fechou?" pelo relógio local (`clock.now()`), e a Binance recusa requisições com o relógio fora da janela (`recvWindow`). Ninguém mede a diferença entre o relógio do servidor e o da exchange. |
| C5 excesso de informação | n/a | Sem feeds de notícia; nada a fazer. |

### 2.1 Correções em relação à versão anterior deste relatório
* **O2 (política de permissão) já estava implementado** para chaves live: saque, transferência, falta de permissão de trade e falta de restrição de IP são recusados. A proposta passa a ser completar o que falta: reverificar periodicamente, mostrar o motivo e as permissões, e não derrubar um bot no meio de uma posição.
* **Achado novo:** posição aberta sem stop nativo fica desprotegida durante uma queda do worker, e nada mostra isso.
* **Achado novo:** o worker é o único serviço sem healthcheck, e é o que mais importa.
* **Achado novo:** nenhuma medição de diferença de relógio com a exchange.

## 3. Oportunidades

Convenções (como nos Caps. 2 e 3): campos novos na API opcionais e aditivos; `openapi.json` + `npm run api:types` + `check:consistency` a cada mudança de contrato; textos da UI em português; nenhuma ação com dinheiro real é necessária para testar.

### O1 — Permissões das chaves: reverificar, explicar e guardar *(livro: espírito de C3, p. 74 · adaptação)*
* **Problema:** a chave é conferida só na criação; uma mudança posterior na exchange (liberar saque, tirar a restrição de IP) passa despercebida, e o operador não vê por que uma chave foi recusada.
* **Back-end:**
  * Guardar o resultado de cada verificação na conexão: novas colunas em `exchange_connections` — `permissions JSONB` (`can_read`, `can_trade`, `can_withdraw`, `can_transfer`, `ip_restricted`), `status_reason TEXT`, `last_checked_at`.
  * `ConnectionResolver.recheck_active()`: o worker reverifica as conexões live **ativas** uma vez por dia (mesmo padrão de agendamento do registro de listagens do Cap. 3). Se aparecer um problema, a conexão **não** vira `invalid` (isso bloquearia também as saídas de bots com posição): ela ganha `permission_warning` e
    * novas entradas live e novos starts de bot com essa conexão são recusados com o motivo;
    * saídas e stops continuam permitidos;
    * evento de auditoria `connection.permissions_changed` e alerta (quando o Cap. 1 O1 existir).
  * Ação `POST /exchange-connections/{id}/recheck` para verificar na hora (admin).
  * `ConnectionOut` ganha `status_reason`, `permissions`, `last_checked_at`, `permission_warning`.
* **Front-end:**
  * Tela de conexões: coluna "Permissões" com selos (negociar ✓, sacar ✗, transferir ✗, IP restrito ✓), "Última verificação" e o **motivo** da recusa ou do aviso em texto, além do botão "Verificar agora".
  * Formulário de nova conexão live: passo a passo curto de como criar a chave na Binance (só Spot trading, sem saque, sem transferência, IP do servidor) e o aviso de contraparte: "deixe na exchange só o capital que os bots usam".
  * Detalhe do bot: aviso quando a conexão está com `permission_warning` ("novas entradas bloqueadas até corrigir a chave").
* **Complexidade:** média. **Risco:** a Binance pode falhar na consulta de permissões; erro transitório não muda nada (como hoje no `verify_pending`). **Validação:** teste com exchange falsa cuja chave passa a permitir saque depois de ativa (aviso, entrada recusada, saída permitida); teste da API e do front para motivo e permissões.

### O2 — Posições desprotegidas numa queda *(livro: C4, pp. 75–77 · adaptação)*
* **Problema:** se o host cair, só o stop **na exchange** protege a posição; posição sem stop nativo fica exposta, e nada mostra isso.
* **Back-end:**
  * `SystemStatus.unprotected_positions`: bots testnet/live com quantidade > 0 e sem `stop_order_client_id` (o paper não conta: não há dinheiro). Cada item com bot, par, quantidade e há quanto tempo está aberto.
  * Configuração opcional `LIVE_REQUIRE_NATIVE_STOP` (padrão `true` em produção): bots live só podem ser aprovados com `require_stop_loss` ligado e uma estratégia que proponha stop; o worker recusa a aprovação live caso contrário, com mensagem clara.
* **Front-end:**
  * Tela Sistema: tile "Posições sem stop na exchange" e lista com link para cada bot.
  * Detalhe do bot (testnet/live): selo "sem stop na exchange — exposto se o worker cair" quando for o caso.
  * Fluxo de aprovação live: o motivo da recusa quando faltar stop.
* **Complexidade:** baixa–média. **Validação:** teste do status com uma posição sem stop; teste da recusa de aprovação live sem `require_stop_loss`.

### O3 — Checagem de vida de fora da stack *(livro: C4 monitoramento remoto, p. 77 · liga com Cap. 1 O1)*
* **Problema:** se o host inteiro cair, ninguém é avisado; o worker nem tem healthcheck.
* **Back-end:**
  * `GET /health/worker`: 200 com o tempo desde o último heartbeat; **503** quando passa de `WORKER_STALE_AFTER_SECONDS` (o mesmo limite da tela Sistema). Sem autenticação e sem dado sensível, para um monitor externo (UptimeRobot, Healthchecks.io, cron em outra máquina).
  * `python -m worker --healthcheck`: sai com código ≠ 0 se o heartbeat estiver velho; usado como `healthcheck` do serviço `worker` no `docker-compose.yml`.
  * Runbook (O4) explica como apontar um monitor externo para `/health/worker` — o único jeito de saber da queda do host com o app fechado.
* **Front-end:** na tela Sistema, um bloco "Monitoramento externo" com a URL a monitorar e o estado atual dela (copiar para a área de transferência).
* **Complexidade:** baixa. **Validação:** teste de API (200 e 503 com o relógio falso); teste do comando de healthcheck.

### O4 — Backup, restauração testada e runbook *(livro: C4, pp. 75–77 · adaptação)*
* **Back-end / operação:**
  * `python -m manage backup`: `pg_dump` em formato custom para um diretório configurável (`BACKUP_DIR`), nome com data, e registro numa nova tabela `backups` (momento, arquivo, tamanho, checksum SHA-256, resultado). Retenção configurável (`BACKUP_KEEP=14`).
  * `python -m manage restore-check <arquivo>`: restaura num banco temporário, roda `alembic current` e compara contagens das tabelas principais (bots, ordens, fills, auditoria) com o banco de origem no momento do dump; grava o resultado na mesma tabela. Um backup só conta como bom depois de uma restauração testada.
  * `make backup`, `make restore-check`; serviço opcional `backup` no `docker-compose.yml` (cron diário).
  * `SystemStatus.backup`: último backup, último teste de restauração e se estão "atrasados" (mais de 26 h).
  * **Runbook** novo em `api/docs/operations/runbook.md`: onde rodar (servidor sempre ligado, não um notebook que entra em repouso), política de reinício, como fazer e restaurar backup, monitor externo (O3), sincronização de relógio (O5), o que acontece com posições abertas se o host cair (stops nativos, O2), o kill switch e como trocar as chaves e a `CREDENTIAL_MASTER_KEYS` (rotação já suportada por `key_id`).
* **Front-end:** tela Sistema: tile "Backup" ("há 5 h · restauração testada há 2 dias"), em alerta quando atrasado ou quando o último teste falhou.
* **Complexidade:** média. **Risco:** o dump contém credenciais criptografadas: o arquivo precisa ficar fora do servidor e com acesso restrito; sem a chave mestra ele não serve para restaurar conexões (o runbook explica). **Validação:** teste de integração que faz backup e `restore-check` num banco temporário; a primeira restauração real documentada no runbook.

### O5 — Diferença de relógio com a exchange *(livro: C4 latência, p. 77 · adaptação)*
* **Back-end:**
  * Método `fetch_server_time()` no adaptador (ccxt `fetch_time`); o worker mede a diferença a cada reconciliação e grava junto do heartbeat (`clock_skew_ms`).
  * `SystemStatus.clock_skew_ms`; acima de 1 s é aviso; acima de 5 s o worker **não envia novas ordens live** (saídas continuam) e grava um evento de auditoria, porque a decisão de "candle fechado" e a janela de assinatura da Binance dependem do relógio.
* **Front-end:** tile "Relógio" na tela Sistema ("diferença com a Binance: 120 ms"), em alerta acima de 1 s, com a dica de ativar NTP.
* **Complexidade:** baixa. **Validação:** teste com exchange falsa adiantada 10 s (ordem live nova recusada, saída permitida).

### Fora do escopo agora
* **Comparar a qualidade de execução entre exchanges (C2):** depende de registrar preço esperado × executado, tema do Cap. 5 (backlog B7).
* **Mostrar o saldo da conta contra o capital alocado (C3):** útil, mas exige ler saldo da exchange na tela; avaliar junto com a reconciliação do Cap. 5.
* Corretora × mesa proprietária, Series 7, SIPC, Regulation T, dark pools, colocalização perto da bolsa, feed de notícias.

## 4. Prioridade

| # | Item | Confiabilidade | Gestão de risco | Esforço back | Esforço front | Depende de |
|---|---|---|---|---|---|---|
| 1 | O2 posições sem stop na exchange | alta | **alta** | baixo–médio | baixo | – |
| 2 | O1 reverificação e motivo das permissões | média | **alta** | médio | baixo–médio | – |
| 3 | O3 checagem de vida externa | alta | média | baixo | baixo | – |
| 4 | O4 backup + restauração + runbook | alta | média | médio | baixo | – |
| 5 | O5 relógio | média | média | baixo | baixo | – |

O2 primeiro: é o único item em que uma queda comum (reinício do host) já pode custar dinheiro hoje.

## 5. Arquivos afetados

**Back-end (`api/`)**
* `src/modules/exchanges/domain/connections.py`, `application/connections.py` (reverificação, `permission_warning`), `infrastructure` (colunas novas), `presentation` (`ConnectionOut`, `/recheck`), `infrastructure/ccxt_exchange.py` (`fetch_server_time`).
* `src/modules/trading/application/status.py` (`unprotected_positions`, `clock_skew_ms`, `backup`), `trading/application/trader.py` e `orders.py` (bloqueio de entradas com aviso de chave ou relógio), `bots` (aprovação live exige stop).
* `src/modules/health/router.py` (`/health/worker`), `src/worker.py` (`--healthcheck`, agenda da reverificação e da medição de relógio), `src/manage.py` (`backup`, `restore-check`).
* `docker-compose.yml` (healthcheck do worker, serviço de backup), `Makefile`, `core/config.py` (`BACKUP_DIR`, `BACKUP_KEEP`, `LIVE_REQUIRE_NATIVE_STOP`).
* Migração `0010_operations.py`: colunas de conexão, tabela `backups`.
* Docs: novo `api/docs/operations/runbook.md`; `08-database.md` (backup deixa de ser promessa).
* Testes: unidade (política, relógio, healthcheck), integração (reverificação, posições sem stop, `/health/worker`, backup + restore-check).

**Front-end (`app/`)**
* `src/components/exchanges/connections-page.tsx` e `connection-form-page.tsx` (permissões, motivo, verificar agora, guia da chave), `src/lib/exchanges` (schemas).
* `src/components/system/system-page.tsx` (posições sem stop, monitoramento externo, backup, relógio), `src/lib/shared/system` (schema do status).
* `src/components/bots` (selos de posição sem stop e de aviso de chave; motivo na aprovação live).
* `app/docs/06-screens.md`.

## 6. Plano incremental
1. **O2:** posições sem stop no status + tela Sistema + selo no bot; exigência de stop na aprovação live.
2. **O3:** `/health/worker`, healthcheck do worker no compose, bloco de monitoramento externo.
3. **O1:** colunas de permissão, motivo na tela, reverificação diária com `permission_warning`, "Verificar agora".
4. **O4:** backup + restore-check + tabela + tile; runbook.
5. **O5:** medição de relógio, tile e bloqueio de entradas live acima de 5 s.

## 7. Critérios de aceite
* Uma posição testnet/live sem stop na exchange aparece na tela Sistema e no bot; uma aprovação live sem stop é recusada com motivo.
* `/health/worker` responde 503 com o worker parado; o container do worker fica `unhealthy`.
* Uma chave que passa a permitir saque depois de ativa gera aviso: novas entradas live recusadas, saídas permitidas, motivo visível na tela de conexões.
* Um backup é restaurado num banco limpo pelo `restore-check`, com contagens iguais, e o resultado aparece na tela Sistema.
* Uma diferença de relógio acima de 5 s bloqueia novas ordens live, não as saídas.
* Nenhuma ação com dinheiro real é necessária para testar; `make check`, integração, `npm run lint`, `typecheck`, `test`, `build` verdes; telas conferidas em 1366 px e 360 px.

## Ressalva
Os valores de custo e hardware de Chan (2008) estão desatualizados e são específicos de ações; não usar como estimativas.
