# Livro 1 · Capítulo 1 — O quê, quem e por quê do trading quantitativo

*Quantitative Trading*, Ernest P. Chan (Wiley, 2009). As páginas são **páginas do livro** (página do PDF = página do livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise, nada implementado.

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
| C6 dados | ⚠️ | O trader busca candles recentes por conta própria; a importação histórica é apenas manual. |
| C6 **alertas** | ❌ | Nenhum canal de notificação (busquei `alert`, `notif`, `webhook`, `telegram`, `email`, `smtp` em `api/src`: nada). O heartbeat do worker existe, mas só é lido pela UI. |
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

### O2 — Importação incremental automática de dados *(livro: C6, pp. 6–7 · adaptação)*
* **Problema:** lacunas nos candles armazenados só são reparadas por jobs manuais.
* **Proposta:** uma tarefa periódica no worker que estende a cobertura dos pares ativos até o presente, reutilizando o job de importação; recuar (backoff) em lacunas de manutenção da exchange.
* **Benefício:** backtests sempre rodam com dados atuais.
* **Complexidade:** baixa. **Riscos:** limites de taxa (rate limits); lacunas legítimas sendo tentadas para sempre.
* **Validação:** teste de integração com uma fonte falsa que deixa um buraco e espera que ele seja preenchido.

#### Detalhamento do O2 (proposta, nada aprovado nem implementado)

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
* O1: novo módulo `notifications` (porta `Notifier` + `in_app`, entidade/tabela de alertas com migração, repositório, endpoints de listar/contar não lidos/marcar como lido), `worker.py`, `container.py`, `core/config.py`, auditoria, `docs/openapi.json`; no app: indicador de não lidos no layout, lista de alertas e página de status (regras em `app/AGENTS.md`).
* O2: `modules/market_data/application/service.py`, `worker.py`, `container.py`.
* O3: `modules/bots/application/service.py`, router de bots, payload de auditoria, formulários de controle do app.

## 6. Plano incremental
1. O1a: porta `Notifier`, notifier falso, avaliador de condições com deduplicação, cooldown e recuperação (sem persistência).
2. O1b: canal `in_app`: tabela e repositório de alertas, endpoints (listar, contar não lidos, marcar como lido), integração ao worker e retenção/limpeza.
3. O1c: front: indicador de não lidos no layout, lista de alertas e alertas recentes na página de status.
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
