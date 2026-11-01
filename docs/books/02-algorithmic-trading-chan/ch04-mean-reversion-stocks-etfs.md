# Livro 2 · Capítulo 4 — Reversão à média em ações e ETFs

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 87–106 foi lido.

O capítulo trata de ações e ETFs dos EUA (vendas a descoberto, arbitragem de índices, preços diários de abertura/fecho e universos do S&P 500). O autor volta a dizer que **os backtests excluem custos de transação e usam dados com viés de sobrevivência**; também usam preços consolidados de abertura/fecho, pelo que os resultados reais “serão inferiores” (p. 88). A maior parte não se aplica a um sistema cripto à vista, comprado apenas; as ideias transferíveis estão identificadas.

## 1. Resumo do capítulo (pp. 87–106)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Ações individuais quase nunca são estacionárias; **pares de ações cointegrados num período frequentemente deixam de o ser fora da amostra**, pois a situação das empresas diverge. Negociar muitos pares só ajuda se o retorno esperado fora da amostra for positivo por par; as perdas dos pares “maus” podem superar os pequenos ganhos dos “bons”. Outros atritos: *short squeeze* e chamadas de ações emprestadas, regra de uptick, pouca quantidade visível nas cotações (NBBO de 100 ações). Pares eram mais rentáveis quando o mercado era menos eficiente e antes da decimalização. | Por que a estratégia clássica de pares perdeu eficácia. | 89–91 |
| C2 | **Pares e trios de ETFs** são mais robustos porque a composição econômica de uma cesta muda lentamente (EWA/EWC; ETF de commodities versus produtores). GLD/GDX foram cointegrados de 2006 a julho de 2008 (99%) e não depois; adicionar o ETF de petróleo USO restaurou a cointegração entre 2006 e 2012, coerente com custos de mineração maiores quando o petróleo encarece. Lição: **quando uma estratégia deixa de funcionar, formule uma hipótese e teste-a empiricamente**; adicionar regra para parar de negociar o par se o petróleo ultrapassar um limite. USO detém futuros, não petróleo à vista (retorno da rolagem; cap. 5). | Escolha de pares e análise de falhas. | 91–92 |
| C3 | **Compra na lacuna** (*Buy-on-Gap*, reversão sazonal intradiária): na abertura, selecionar ações cujo retorno da mínima anterior até a abertura atual fique abaixo de −1 desvio-padrão (90 dias, fechamento a fechamento), **mas cuja abertura esteja acima da média móvel de 20 dias** (filtro de momentum num modelo de reversão: pequenas quedas revertem; grandes podem refletir notícias); comprar as dez piores e vender no fecho. Backtest: retorno anual 8,7%, Sharpe 1,5 (2006–2012, sem custos e com viés de sobrevivência); sem a regra 2, o retorno caiu desde 2009. Há “ruído de sinal”, pois o preço de abertura não é conhecido antes da abertura. A estratégia espelhada de venda na lacuna: retorno anual 46%, mas drawdown mais acentuado. Séries sem reversão em barras diárias podem reverter em **períodos específicos**. | Encontrar reversão sazonal. | 92–96 |
| C4 | **Arbitragem de índice/ETF**: a relação entre ações e futuros de índice ficou estreita; selecionar um *subconjunto* de ações que individualmente cointegravam com SPY (98 ações, depois retestadas em conjunto) amplia o spread. Estratégia linear (janela 5, escolhida retrospectivamente): retorno anual 4,5%, Sharpe 1,3, em declínio porque as razões de hedge não foram recalibradas. Johansen aceita no máximo 12 séries. | Explorar uma cesta em relação ao índice. | 96–102 |
| C5 | **Reversão à média transversal**: pesos `wᵢ = −(rᵢ − r̄) / Σ|rₖ − r̄|`, exposição bruta total sempre igual a US$ 1; sem parâmetros e quase neutra em dólares. S&P 500 (2007–2011): retorno anual 13,7%, Sharpe 1,3; versão abertura-fecho: 73% e Sharpe 4,7 antes dos custos, mas duplica os custos de transação e tem ruído de sinal. O lucro aparece somente no agregado da cesta. Outras variáveis de ordenação (P/L) podem evitar vender ações cuja variação se explica por fundamentos. | Valor relativo numa cesta. | 102–105 |
| C6 | Principais pontos: cuidado com fundamentos das empresas; carteiras de ETFs em vez de pares de ações; filtros de momentum podem tornar a reversão mais consistente. | – | 106 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Cointegração de pares/ETFs e arbitragem de índices | n/a | Exige posições vendidas e carteiras de vários ativos; há um ativo por bot e posições compradas. |
| Falha fora da amostra de relações ajustadas | ⚠️ conceito aplicável | Parâmetros ajustados a um par podem perder eficácia; o sistema não detecta isso (não recalibra nem monitora regimes). |
| Processo para analisar falhas | ❌ | Não há local para registrar hipótese sobre por que uma estratégia falhou e o resultado do teste. |
| Filtro de momentum numa entrada de reversão | ❌ | Não existe estratégia assim; a estrutura permite combinar condições apenas numa classe de estratégia. |
| Sazonalidade intradiária | ❌ | As estratégias só veem OHLCV; não há atributos de hora ou dia da semana. |
| Ordenação transversal de ativos | ❌ | Um símbolo por bot; não há motor de carteiras. |
| Ruído de sinal na abertura | n/a | Cripto negocia continuamente; as estratégias agem após o fecho do candle e executam na próxima abertura. Não há leilão. |
| Custos no backtest | ✅ | Sempre aplicados, ao contrário dos exemplos do livro. |

## 3. Oportunidades

### O1 — Registro de análise pós-estratégia e monitor de deterioração *(livro: C2, pp. 91–92)*

* **Problema:** a principal lição reutilizável é metodológica: quando GLD/GDX deixou de funcionar, o autor formulou e testou a hipótese de custos do petróleo. Não há estrutura para registrar por que um bot/estratégia foi retirado, qual hipótese foi testada e com que resultado, nem sinal automático de que o desempenho recente saiu da faixa do backtest.
* **Proposta:** (a) nota simples anexada a bot/backtest (texto livre, registrada na auditoria; relacionada ao livro 1, cap. 1 O3 e cap. 6 O6); (b) **monitor de deterioração**, comparando resultados móveis de paper/operação real com a distribuição do backtest (reutiliza livro 2, cap. 1 O4 e livro 1, cap. 5 O1/O5).
* **Benefício:** memória institucional e alerta precoce de perda da vantagem. **Complexidade:** baixa para notas, média para o monitor. **Risco:** amostras curtas geram falsos alertas; mostrar o tamanho da amostra. **Validação:** séries de patrimônio com semente fixa, deteriorando para abaixo da faixa do backtest.

### O2 — Filtro de tendência na futura estratégia de reversão *(livro: C3, p. 93)*

Ao criar `bollinger_reversion` (livro 2, cap. 3 O1), incluir um filtro opcional de média móvel de longo prazo (entrar apenas se o preço estiver acima da média de N períodos), equivalente à regra 2 de Buy-on-Gap. A hipótese do livro: quedas pequenas revertem; quedas profundas muitas vezes refletem notícias. Vale testar em cripto, não pressupor. **Complexidade:** baixa (um parâmetro extra, que também pode gerar sobreajuste). **Validação:** comparar com/sem filtro em treino/teste e medir sensibilidade a N.

### O3 — Condicionamento por hora/dia da semana para pesquisa *(livro: C3, p. 96, “sazonalidade em horizonte curto”; aplicação cripto é adaptação nossa)*

Estender os diagnósticos (livro 2, cap. 2 O1) para calcular estatísticas de reversão/tendência **por hora e dia da semana** (UTC) para cada par. O livro não apresenta evidência sobre cripto; trata-se apenas de exploração. **Complexidade:** baixa a média. **Risco:** fácil ajustar aos dados (24×7 intervalos × muitos pares); exigir confirmação fora da amostra e aplicar o controle de número de tentativas do livro 1, cap. 3 O7. **Validação:** série sintética com efeito de horário inserido.

### O4 — Ordenação transversal de uma cesta de moedas *(livro: C5, pp. 102–105)*

Criar relatório **somente para pesquisa** que ordene pares importados por retorno relativo de curto prazo e teste se os piores se recuperam (versão comprada: comprar os últimos colocados e manter por N candles). A arquitetura não tem estratégia multiativo nem motor de carteira; implementação para negociação fica fora do escopo. O relatório pode usar candles armazenados e métricas existentes.

**Complexidade:** média para pesquisa; muito alta para negociação. **Riscos:** a versão apenas comprada remove a proteção que torna a abordagem do livro quase neutra em dólares; quedas generalizadas de cripto atingem todas as posições; viés de sobrevivência (só moedas ainda listadas foram importadas); ativos correlacionados reduzem a independência das observações. **Validação:** estatísticas de dados armazenados com período reservado; nunca apresentar como resultado negociável. Registrar a versão de negociação como **B-MULTI-ASSET** (ver backlog).

### Não aplicável ou adiado

Pares de ações/ETFs, trios, arbitragem de índices, limites do teste Johansen, venda na lacuna, ordenação por P/L, preços primários versus consolidados e preços pré-abertura.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 notas e monitor de deterioração | média | média | média | baixa–média | livro 1, cap. 5 O1; livro 2, cap. 1 O4 |
| 2 | O2 filtro de tendência opcional | baixa | – | – | baixa | livro 2, cap. 3 O1 |
| 3 | O3 diagnóstico por intervalo temporal | baixa | – | – | baixa–média | livro 2, cap. 2 O1 |
| 4 | O4 relatório de pesquisa transversal | baixa | – | – | média | dados de vários pares |

## 5. Arquivos afetados

Notas de bots e backtests: `bots/application/service.py`, `backtesting/application/service.py`, dados de auditoria e componente de notas no app. Diagnósticos: `analytics/domain/` (novas funções), `market_data/presentation/router.py`. Estratégia: `strategies/domain/` (arquivo futuro); página de dados de mercado do app.

## 6. Plano incremental

1. Campo de notas em bots/backtests com auditoria (baixo custo e útil nos próximos capítulos).
2. Monitor de deterioração após existirem métricas de paridade/Sharpe.
3. Diagnósticos por janela e relatório de pesquisa transversal após existir o módulo de diagnósticos.
4. Filtro de tendência com a futura estratégia de reversão à média.

## 7. Critérios de aceitação e testes

* Notas são armazenadas e auditadas, sem alterar a negociação.
* Diagnósticos por janela retornam a contagem de cada grupo e não exibem resultado quando a amostra é inferior ao mínimo.
* O relatório transversal é somente de leitura e identificado como pesquisa.
* Ruff, mypy e testes existentes passam.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`), números como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil, fronteiras entre módulos protegidas por `tests/unit/test_architecture.py`. A última migração é `0014_backtest_regime`. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| C2 registro de análise (por que um bot saiu, qual hipótese) | ❌ | ⚠️ comandos e edições de bot já gravam **autor e motivo** na auditoria (livro 1, cap. 1 O3 e cap. 6 O6), e `GET /bots/{id}/interventions` conta intervenções. Falta texto livre ligado a um bot ou backtest. |
| C2 monitor de deterioração | ❌ | ❌ continua; as peças existem: métricas de bot iguais às do backtest (`BotService.performance`), paridade (`/bots/{id}/parity`) e o módulo de alertas (`notifications/application/conditions.py`, com `worker_down`, `kill_switch`, `bots`, `candles`). |
| C3 filtro de tendência na entrada | ❌ | ❌ continua; depende da estratégia ([cap. 3](ch03-implementing-mean-reversion.md)). |
| C3 sazonalidade por hora/dia | ❌ | ❌ continua; o desenho está na [Fase 5 do livro 1, cap. 7](../01-quantitative-trading-chan/ch07-special-topics.md) (`analytics/domain/calendar.py`, Bonferroni), adiada. |
| C5 ordenação transversal | ❌ | ❌ continua (um símbolo por bot). Os dados existem: candles de vários pares podem estar armazenados e `/market-data/listings` registra o que saiu da listagem daqui para a frente. |

**Achados que moldam o plano:**
* A auditoria já filtra por tipo de evento (`/audit-events?event_type=`) e tem autor; uma nota pode ser **um evento de auditoria** (`note.added`), **sem tabela nova e sem migração**.
* `AlertKind` e `Condition` (`notifications/domain/models.py`) já modelam um alerta com chave estável; uma condição nova não precisa de infraestrutura nova.
* Escrever (editar bot) é de admin (`require_admin` em `core/security/auth.py`); leitura é `require_access`.

### Fase A — Notas de análise em bots e backtests (O1a) · prioridade 1 · sem migração

* **A.1 Back-end:** `POST /api/v1/bots/{bot_id}/notes` e `POST /api/v1/backtests/{run_id}/notes` com `{text: 1–2000 caracteres}`, `require_admin`; gravam um evento de auditoria `note.added` com `bot_id` (ou `backtest_id` no *payload*), o autor autenticado e o texto. Leitura: o `GET /audit-events?event_type=note.added&bot_id=` existente, sem endpoint novo. Onde mora cada rota: `bots/presentation/router.py` e `backtesting/presentation/router.py`; o caso de uso chama o serviço de auditoria já injetado em `Container`; **conferir** como `BotService` registra os eventos de intervenção (livro 1, cap. 8, Fase 1) e seguir o mesmo caminho para o autor. O texto é tratado como **texto puro**; nunca vira HTML.
* **A.2 Front-end:** `components/shared/notes/notes-panel.tsx` (lista de notas com autor e data UTC, campo "Registrar nota" com contador de caracteres, só para admin), usado na aba "Auditoria" do bot (`BotTab.Audit`) e no detalhe do backtest. Schema e funções em `lib/shared/audit/audit.api.ts`, `QueryKey` por bot/backtest. O app não executa nada do texto (regra de `app/AGENTS.md`: sem `dangerouslySetInnerHTML`). Esqueleto, erro, vazio ("Registre por que esta estratégia foi pausada ou aposentada"), dados; 360 px.
* **A.3 Testes:** integração (admin cria, viewer recebe 403, leitura devolve autor/data, 422 acima de 2.000 caracteres, bot inexistente 404, texto com `<script>` volta como texto); `vitest` do painel.
* **Aceite:** nenhuma mudança em negociação, risco ou estado de bot; a nota aparece na linha do tempo de auditoria.

### Fase B — Monitor de deterioração (O1b) · prioridade 2 · sem migração · depende do [cap. 1, Fase D](ch01-backtesting-and-automated-execution.md)

Objetivo: avisar, **sem pausar nada**, quando o desempenho recente de um bot ativo (paper ou live) saiu da faixa do backtest equivalente.

* **B.1 Regra pura** em `trading/domain/deterioration.py` (ao lado de `diagnosis.py` e `parity.py`): `deterioration(realized, backtest, min_periods) -> Deterioration | None`. Sinais, todos com a amostra visível: (a) Sharpe real abaixo de metade do Sharpe do backtest (a regra prática de Chan; é observação do autor) e (b) drawdown atual **maior** que o máximo do backtest. Abaixo de `min_periods` retornos reais (proposta: 30, o mesmo de `MIN_RETURNS`), **não alerta**: devolve `None` com o motivo "amostra curta".
* **B.2 Alerta:** `AlertKind.PERFORMANCE_DEGRADED` e uma função `performance(...)` em `notifications/application/conditions.py` com chave estável por bot (a mensagem não leva contadores que mudem a cada checagem, como a convenção do arquivo exige). A avaliação roda no mesmo ciclo do `evaluator.py`; a comparação reaproveita o serviço de comparação do cap. 1 (que fica em `trading/application/`). Severidade `WARNING`; **nunca** altera o estado do bot.
* **B.3 Front-end:** o indicador de alertas do topo (`alerts-indicator.tsx`) e `alerts-page.tsx` já listam por `kind`; acrescentar o rótulo em `lib/shared/labels.ts` e o `AlertKind` em `lib/shared/enums.ts` (o `check:consistency` falha se faltar). O card do cap. 1 (Fase D) ganha a frase "deterioração detectada: veja a nota de análise" com atalho para o painel de notas da Fase A.
* **B.4 Testes:** `tests/unit/test_deterioration.py` (série de patrimônio com semente fixa que piora abaixo da faixa → alerta; dentro da faixa → nada; amostra curta → `None` com motivo; backtest com Sharpe ≤ 0 → sem comparação); integração com o `evaluator` (alerta abre e **fecha** quando volta à faixa, sem duplicar, respeitando `alert_cooldown_seconds`).
* **Aceite:** nenhum bot muda de estado por causa do alerta; amostra curta nunca alerta; o alerta some sozinho quando a condição some.

### Fase C — Filtro de tendência opcional na estratégia de reversão (O2) · prioridade 3 · espera a estratégia

Depende de `mean_reversion_zscore` existir ([cap. 3, Fase A](ch03-implementing-mean-reversion.md)). O parâmetro seria `trend_filter_period` (inteiro opcional ≥ 2): só entra se o fechamento estiver **acima** da média simples de N candles (a regra 2 de Buy-on-Gap, p. 93). Impacto: o estado da estratégia precisa guardar a janela longa (hoje guarda só `lookback`), e o parâmetro seria o **sexto**, o que estoura `too_many_parameters` (limite 5): **decisão pendente** (ver cap. 3). Testes: com e sem filtro em treino × teste, sensibilidade a N, teste de truncamento (já cobre toda a estratégia do catálogo). Não implementar antes do cap. 3.

### Fase D — Pesquisa por hora do dia e dia da semana (O3) · adiada

É a Fase 5 do [livro 1, cap. 7](../01-quantitative-trading-chan/ch07-special-topics.md): `analytics/domain/calendar.py`, 24 grupos de hora UTC e 7 de dia da semana, **31 testes** com correção de Bonferroni e contagem de tentativas, página de pesquisa somente leitura. Este capítulo não acrescenta nada, só a ressalva: sem confirmação fora da amostra, um efeito de horário é quase certamente acaso.

### Fase E — Relatório de ordenação transversal (O4) · prioridade 4 · só pesquisa, sem migração

* **E.1 Função pura** `analytics/domain/cross_section.py`: entrada, os fechamentos alinhados de ≥ 5 símbolos (todos importados, mesmo intervalo e período); para cada barra de formação, ordena por retorno dos últimos `formation` candles e mede o retorno dos `holding` candles seguintes do **grupo pior** e do **grupo melhor** (quartis, só comprado). Saída: retorno médio por grupo, `n` de formações **não sobrepostas** por grupo e uma linha "comprar o pior grupo × comprar tudo". Sem custos no resultado, e a tela diz isso. Limites fixos (`MAX_SYMBOLS = 20`, `MAX_ANALYSIS_CANDLES` já existente).
* **E.2 API:** `GET /api/v1/market-data/cross-section?symbols=...&timeframe&start&end&formation&holding` em `market_data/presentation/router.py`; serviço lê os candles de cada par (`store.candles.get_range`) em `asyncio.to_thread`. Resposta marcada `research_only: true`, com o aviso de **viés de sobrevivência** (só pares ainda listados foram importados; `/market-data/listings` mostra o que saiu) e de que a versão só comprada perde a neutralidade do livro.
* **E.3 Front-end:** card "Ordenação transversal (pesquisa)" na página de dados de mercado, só leitura, com a faixa de data e a lista de pares já importados (`useCoverage`); tabela com os números **escritos**. Nunca oferece "criar bot"; **B-MULTI-ASSET** (negociar uma cesta) fica no backlog, sem motor de carteira.
* **E.4 Testes:** série sintética de 6 pares em que o pior grupo realmente se recupera (grupo pior > melhor) e a mesma com passeio aleatório (diferença ≈ 0 na tolerância); formações não sobrepostas contadas certo; menos de 5 símbolos → 422.

### Ordem, dependências e estimativa

A → (cap. 1 Fase D) → B; C espera a estratégia; D adiada; E é independente. Estimativa grosseira: A ≈ 1,5 dia (1 back, 0,5 front); B ≈ 2 (1 back, 1 de integração com alertas); E ≈ 2,5; C e D fora do corte. Nenhuma fase mexe no banco.

### Decisões pendentes (para o operador)

* Quem pode escrever notas (proposta: admin) e o tamanho máximo (proposta: 2.000 caracteres).
* Limites do monitor: metade do Sharpe e 30 retornos (propostas apoiadas no livro e no `MIN_RETURNS`).
* Se o monitor de deterioração deve, no futuro, sugerir pausa (proposta: **nunca automático**).
* Se a pesquisa transversal vale o custo antes de existir mais de um punhado de pares importados.

### Fora do escopo (decidido)

Pares de ações e ETFs, arbitragem de índice, venda na lacuna, ordenação por P/L e qualquer negociação transversal (exige motor de carteira e posição vendida).

### Critérios de aceite gerais

Nenhum estado de bot, ordem ou salvaguarda live é alterado por notas, monitor ou relatório; nenhum `float` no domínio; `make check`, integração, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas em 1366 px e 360 px. Os números de desempenho do livro (8,7%, 13,7%, 46%, 73%) são de ações dos EUA e não valem para cripto.

## Ressalvas

Os números de desempenho (retornos anuais de 8,7%, 13,7%, 46%, 73%; Sharpe até 4,7) vêm de backtests de ações dos EUA, brutos de custos e sujeitos a viés de sobrevivência. Alguns têm falhas reconhecidas pelo autor (janelas escolhidas retrospectivamente e ruído do preço de abertura). Não são expectativas para cripto. A conclusão de que pares de ETFs superam pares de ações é do autor e refere-se ao mercado americano em 2013.
