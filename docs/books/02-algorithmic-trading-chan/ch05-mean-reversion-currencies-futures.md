# Livro 2 · Capítulo 5 — Reversão à média em moedas e futuros

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 107–131 foi lido.

O capítulo trata sobretudo de cruzamentos cambiais e futuros negociados em bolsa (retorno de rolagem, spreads de calendário e futuros de volatilidade). Lost Crypto opera à vista, comprado, um ativo por bot; **a maior parte não se aplica hoje**. O relatório registra o que é relevante agora e o que se tornaria relevante caso houvesse derivativos. Os backtests do capítulo excluem custos (aplica-se a ressalva da p. 64).

## 1. Resumo do capítulo (pp. 107–131)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Moedas e futuros tendem a favorecer momentum; reversão à média é exceção. Pares de moedas de países exportadores de commodities podem ser cointegrados. Moedas têm liquidez maior, não têm restrições de venda a descoberto e negociam quase 24 horas (domingo, 17h, a sexta, 17h, horário do leste dos EUA); por isso, **stops fazem sentido, pois não há lacunas após longos fechamentos**. | 107–108 |
| C2 | Mecânica cambial: moeda base e moeda de cotação; cruzamentos sintéticos (`USD.ZAR/USD.AUD`) geram P&L em duas moedas, que devem ser convertidas regularmente para evitar divergência entre resultados reais e backtest. Em Johansen/regressões, variações de pontos devem ter o mesmo valor (usar uma moeda de cotação comum); fórmulas de retorno variam conforme a estrutura base/cotação. Exemplo 5.1 (AUD.USD e CAD.USD, 250 dias de treino, razão de hedge Johansen): retorno anual 11%, Sharpe 1,6. | 108–113 |
| C3 | **Juros de rolagem** (financiamento overnight) acrescentam `log(1+i_B) − log(1+i_Q)` ao retorno de um cruzamento mantido, triplicado nos fins de semana por regras de liquidação. **Retorno excedente = retorno − custo de financiamento**; custo zero em posições intradiárias, ações neutras em dólares e futuros. Exemplo 5.2 (AUD.CAD): retorno anual 6,2%, Sharpe 0,54; ignorar a rolagem teria indicado 6,7%, embora a rolagem média fosse quase 5% ao ano. | 113–115 |
| C4 | **Retorno de futuros = retorno à vista + retorno de rolagem**; *backwardation* (contrato próximo > distante, rolagem positiva) versus *contango* (rolagem negativa); modelo `F(t,T) = c·e^{γt}·e^{λ(t−T)}`; retornos à vista e de rolagem estimados por regressão (exemplo 5.3). Para BR, C e TU, a magnitude da rolagem supera o retorno à vista (milho: −12,8% contra 2,8%). Reversão do preço à vista não implica reversão do futuro. O autor perdeu mais de US$ 100 mil em 2006 num par de ETF e fundo de futuros; VX fica em *contango* cerca de 75% do tempo, com rolagem média de aproximadamente −50% ao ano. | 115–122 |
| C5 | **Spreads de calendário** de ativos negociados só revertem por causa da rolagem: spread de 12 meses de CL, ADF 99%, meia-vida 36 dias, retorno anual 8,3%, Sharpe 1,3 (exemplo 5.4); spread VX pela razão: 17,7%, Sharpe 1,5, mas desempenho fraco antes de outubro de 2008. | 123–127 |
| C6 | **Spreads entre mercados** raramente revertem (spread de refino e CL/BZ falharam no ADF; há razões estruturais, como gargalos em oleodutos e sanções). É importante sincronizar horários de fecho. | 127–129 |
| C7 | **VX versus ES**: futuros de volatilidade têm correlação negativa com o índice; a relação tem **dois regimes** (2004–maio de 2008; agosto de 2008–2012). Regressão ou Johansen sobre regimes misturados seria um erro; o autor ajusta apenas o segundo regime (primeiros 500 dias para treino). No teste (julho de 2010–maio de 2012): retorno anual 12,3%, Sharpe 1,4. | 129–131 |

## 2. Diagnóstico

| Conceito | Situação | Evidência |
|---|---|---|
| Cruzamentos cambiais, rolagem e pares sintéticos | n/a | Cripto à vista: não há juros overnight por manter o ativo comprado; a moeda de cotação é uma stablecoin ou BTC. |
| Futuros, retorno de rolagem, spreads de calendário e VX | n/a | `exchanges` não oferece derivativos, apenas mercados à vista e testnet à vista. |
| Retorno excedente líquido de financiamento | ✅ n/a | Posições à vista compradas sem alavancagem não têm custo de financiamento; as métricas já descontam taxas e slippage (`analytics/domain/metrics.py`). |
| Stops úteis devido à continuidade do mercado | ✅ | Cripto à vista negocia 24/7; stop atravessado por uma lacuna é executado na abertura (`risk_management/domain/stops.py`), abordagem conservadora para pares ilíquidos. |
| Regimes misturados num único ajuste | ❌ | Backtests abrangem intervalos inteiros sem separar regimes; `test_fraction` só divide cronologicamente. |
| Conversão do P&L realizado para moeda-base | ⚠️ | Cada bot informa P&L na moeda de cotação; o painel agrupa totais por moeda sem converter (`GET /bots/summary`). Não há conversão cambial/avaliação numa moeda comum. |

## 3. Oportunidades

### O1 — Avaliação por regime: não ajustar nem avaliar através de quebras estruturais *(livro: C7, pp. 129–130)*

* **Problema:** um backtest, uma meia-vida ou uma razão de hedge calculada em janela que atravessa mudança de regime pode ser inválida (exemplo VX/ES). Em cripto há períodos candidatos claros (ciclo 2017–2018, queda de maio de 2021, colapso de 2022).
* **Proposta:** permitir ao operador marcar **datas de quebra** (nomeadas, por corretora ou globais) e mostrar métricas por regime e no conjunto; permitir que diagnósticos (livro 2, cap. 2 O1) e varreduras usem só um regime escolhido; avisar se o intervalo do backtest atravessar uma quebra cadastrada. Não se propõe detecção automática (livro 1, cap. 7 explica por que prever regimes não é confiável).
* **Benefício:** evita combinar períodos incomparáveis e apoia a observação do livro 1, cap. 2 de que dados recentes importam mais. **Complexidade:** baixa a média (tabela pequena de quebras nomeadas e métricas por segmento; ampliar `segments.py`). **Risco:** escolher datas de quebra também é liberdade de pesquisa (seleção de dados); registrá-las antes dos experimentos. **Validação:** série sintética com quebra; métricas por regime devem corresponder ao cálculo direto.

### O2 — Manter conservador e testar o modelo de execução de stops *(livro: C1, p. 108 · confirma comportamento existente)*

Não se propõe alteração. Adicionar teste unitário (se ainda não houver) para garantir que um stop atravessado por lacuna executa na abertura e outro para slippage realista em pares pouco líquidos. Consultar `tests/unit` para evitar duplicação. **Complexidade:** muito baixa.

### O3 — Item futuro caso se adicionem derivativos: financiamento de futuros perpétuos e base como “retorno de rolagem” *(livro: C3–C5, pp. 113–127 · adaptação especulativa)*

Se houver suporte a perpétuos ou futuros com vencimento, três conceitos se aplicam: retorno total = variação de preço + financiamento/rolagem; retornos excedentes e Sharpe devem incluir o financiamento; intuição baseada no preço à vista (“se o ativo à vista reverte, o contrato também reverte”) pode falhar por causa do *carry*. Registrar como **B-DERIVATIVES**, sem ação no momento. Derivativos também reabririam os riscos de alavancagem (livro 1, cap. 6), venda a descoberto e liquidação, não cobertos pelas salvaguardas atuais.

### Não aplicável

Mecânica de moeda base/cotação, cruzamentos sintéticos, juros de rolagem, spreads de futuros de calendário e entre mercados, spread de refino e estratégias de futuros de volatilidade.

## 4. Prioridade

| # | Item | Qualidade do backtest | Confiabilidade | Gestão de risco | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 avaliação por regime | alta | – | – | baixa–média | livro 1, cap. 2 O5 (métricas por subperíodo) |
| 2 | O2 testes de execução de stops | baixa | média | baixa | muito baixa | – |
| 3 | O3 backlog de derivativos | – | – | – | n/a | decisão de produto |

## 5. Arquivos afetados

`backtesting/domain/segments.py`, `backtesting/application/service.py`, tabela/ORM pequena para quebras nomeadas (módulo `backtesting` ou `market_data`), rotas e schemas, `docs/openapi.json`, formulário e detalhes de backtest no app e testes.

## 6. Plano incremental

1. Métricas por subperíodo (livro 1, cap. 2 O5).
2. Datas de quebra nomeadas, métricas por regime e avisos.
3. Testes de execução de stops.

## 7. Critérios de aceitação e testes

* Métricas por regime correspondem às calculadas diretamente na mesma sub-série.
* Uma execução que atravessa quebra registrada mostra aviso, sem alterar o comportamento de negociação.
* Ruff, mypy e testes existentes passam.

## 8. Plano de implementação detalhado (back-end e front-end)

Escrito em 2026-11-01, com o código verificado nessa data. Convenções do projeto: `Decimal` no domínio (sem `float`), números como **strings decimais** na API e no app, `api/src` é a raiz de imports, sem `__init__.py` vazio, texto de tela em português do Brasil. A última migração é `0014_backtest_regime`. **Nada aqui foi aprovado nem implementado.**

### 8.1 O que mudou desde a análise (verificado no código em 2026-11-01)

| Item | Antes | Agora |
|---|---|---|
| Métricas por subperíodo (pré-requisito do O1) | ❌ | ✅ `backtesting/domain/periods.py` (métricas por ano e trimestre, livro 1, cap. 2) e `components/backtests/periods-card.tsx`. |
| Regimes misturados num único ajuste | ❌ | ⚠️ `analytics/domain/regime.py` descreve a execução por tercis de volatilidade e de eficiência (migração `0014_backtest_regime`, `regime-card.tsx`). É **automático e descritivo**: não há datas de quebra nomeadas pelo operador, que é o que este capítulo pede. |
| O2 stops: execução na abertura após lacuna | ✅ | ✅ coberto: `test_gap_through_the_stop_fills_at_the_worse_open`, `test_stop_wins_when_both_levels_are_inside_the_candle` e os dois testes de backtest com stop e alvo em `tests/unit/test_risk_and_stops.py`. Falta só o caso de **slippage em saída protetora** (ver Fase C). |
| O3 derivativos | n/a | n/a (`exchanges` só tem spot). |

**Achados que moldam o plano:**
* Uma quebra é **conhecimento do operador**, não dado do mercado, e escolher datas depois de ver os resultados é liberdade de pesquisa. Por isso cada quebra guarda `created_at`, e as telas mostram quando ela foi criada **depois** do backtest em exame.
* Execuções guardam o que foi usado em colunas JSONB (`risk_limits`, `regime`, `periods`...). Gravar um **instantâneo das quebras no momento da execução** mantém o resultado reproduzível mesmo se as quebras mudarem depois.

### Fase A — Quebras de regime nomeadas (O1, parte 1: cadastro) · prioridade 1 · migração própria

* **A.1 Modelo e tabela:** módulo novo `modules/regimes` seria demais para uma tabela pequena; colocar em `market_data` (os dados descrevem o mercado). Migração `NNNN_regime_breaks`: tabela `regime_breaks(id uuid pk, name text not null, occurred_at timestamptz not null, exchange text null, symbol text null, note text null, created_by text not null, created_at timestamptz not null)`; `exchange` e `symbol` nulos significam "global". Domínio: `RegimeBreak` em `market_data/domain/models.py`; porta `RegimeBreakStore` em `market_data/application/ports.py`; ORM e repositório em `market_data/infrastructure/`; ligar no `Container` (`container.py`) e no `orm_models.py` (importação para o Alembic ver a tabela).
* **A.2 API (todas sob `/api/v1/market-data/regime-breaks`):** `GET` (lista, filtros `exchange`, `symbol`), `POST` (`require_admin`; `name` 1–60, `occurred_at` com fuso, `note` ≤ 500; duplicata de nome+data → 409), `DELETE /{id}` (`require_admin`, grava auditoria `regime_break.deleted`). Cada criação grava auditoria `regime_break.created` com o autor. Sem `PATCH`: corrigir uma data é apagar e recriar, o que deixa rastro, coerente com o objetivo anti-seleção.
* **A.3 Testes:** integração (admin cria, viewer 403, filtro por símbolo, duplicata 409, `DELETE` audita); unitário do validador (`occurred_at` sem fuso é 422).
* **A.4 Front-end:** `lib/market-data/market-data.api.ts` (schema e funções), `QueryKey.MarketData.regimeBreaks()`, componente `components/market-data/regime-breaks-card.tsx` na página de dados de mercado: lista (nome, data UTC, escopo, quem criou e quando) e formulário de criação (admin). Esqueleto, erro com nova tentativa, vazio ("Nenhuma quebra cadastrada: marque as datas **antes** de rodar os experimentos"), dados; 360 px; `vitest` do schema.

### Fase B — Métricas por regime e aviso de travessia (O1, parte 2) · prioridade 2 · migração própria

* **B.1 Função pura** `backtesting/domain/break_segments.py` (reaproveita `compute_metrics`, como `periods.py` e `segments.py`): dada a curva de patrimônio, os fills e a lista de quebras que caem **dentro** de `[start, end]`, devolve uma lista de trechos `{from, to, label, bars, metrics}` entre quebras consecutivas, mais o trecho "tudo". Trechos com menos de `MIN_RETURNS` retornos saem com `metrics = None` (herdam a regra de `risk_ratios.py`). Nenhuma quebra no intervalo → `None`.
* **B.2 Execução e persistência:** em `BacktestExecutor._execute` (`backtesting/application/service.py`), ao lado de `regime_report`, ler as quebras aplicáveis (globais ou do símbolo/exchange da execução) e gravar `break_metrics` JSONB com **o instantâneo das quebras usadas** (id, nome, data, `created_at`). Migração `NNNN_backtest_breaks` (`ADD COLUMN break_metrics JSONB NULL`; `downgrade` remove; `alembic check`), pelo caminho do `regime` (`ports.py`, `orm.py`, `repository.py`, `service.py`, `router.py` com `BreakMetricsOut` em `BacktestOut`, OpenAPI). Execuções antigas ficam `null`. Se as migrações A e B couberem juntas, melhor uma só.
* **B.3 Aviso de travessia, sem bloquear:** `POST /backtests` e `POST /backtests/sweeps` passam a devolver, em campo aditivo `warnings: list[str]`, "o período atravessa a quebra X (data)". Nunca recusam. O mesmo vale para `GET /market-data/half-life`, que ganha `crosses_breaks: list[...]` (aditivo), porque a meia-vida calculada através de uma quebra pode ser inválida (VX/ES do livro).
* **B.4 Front-end:** `lib/backtests/backtests.api.ts` (schema nullish); em `backtest-detail-page.tsx` um `BreaksCard` depois de `RegimeCard` com a tabela por trecho; selo "quebra criada depois deste backtest" quando `created_at` da quebra é posterior à execução. Em `backtest-form-page.tsx` e `half-life-card.tsx`: aviso inline quando o intervalo escolhido cruza uma quebra e botão **"limitar a este regime"** que só **ajusta as datas do formulário** (início e fim) para o trecho clicado; nada é aplicado sem clique. `vitest` da função que acha as quebras dentro do intervalo.
* **B.5 Testes:** `tests/unit/test_break_segments.py`: série sintética com uma quebra no meio, cujo trecho da esquerda e da direita têm métricas **iguais ao cálculo direto na mesma sub-série**; duas quebras → três trechos; quebra fora do intervalo ignorada; trecho curto → `None`; os trechos cobrem todo o período sem sobrepor. Integração: execução com quebra cadastrada grava o bloco e o aviso; sem quebras, `null`.
* **Aceite:** nenhuma execução existente muda de resultado; o aviso não bloqueia; o instantâneo mantém o resultado de uma execução antiga estável quando uma quebra é apagada.

### Fase C — Teste de slippage em saída protetora (O2) · prioridade 3 · só testes

Conferir em `execution/domain/fills.py` e `risk_management/domain/stops.py` se a saída protetora passa por `slipped_price` (a escolha de **não** aplicar slippage a stop seria um otimismo a registrar). Acrescentar a `tests/unit/test_risk_and_stops.py`: (a) stop atravessado por lacuna preenche na abertura **pior** que o nível e depois leva o slippage adverso; (b) com `max_order_pct_of_volume` ligado, uma saída protetora **não é recusada** (saídas sempre são permitidas). Se o teste (a) revelar que stop não leva slippage, abrir item no relatório em vez de mudar o comportamento neste corte.

### Fase D — Derivativos (O3): backlog · sem trabalho

Registrar **B-DERIVATIVES**. Qualquer suporte a perpétuos reabriria alavancagem, venda a descoberto, liquidação e financiamento no retorno, nada coberto pelas salvaguardas atuais.

### Estado da implementação (2026-11-01)

* **Fases A e B implementadas** com **uma só migração** (`0017_regime_breaks`: tabela `regime_breaks` e a coluna `backtest_runs.break_metrics`). `GET/POST/DELETE /market-data/regime-breaks` (POST e DELETE só admin; sem edição; nome + data únicos, 409 em duplicata; cada criação e remoção grava auditoria `regime_break.created/deleted`). `RegimeBreak` guarda `created_at`. O executor do backtest lê as quebras do mercado dentro do período e grava `break_metrics`: o **instantâneo** das quebras usadas e as métricas de cada trecho (`backtesting/domain/break_segments.py`, mesma construção de `periods.py`, trecho com menos de 2 candles é ignorado). Execuções antigas e execuções sem quebra ficam `null`.
* **Aviso de travessia no front, não no servidor** (desvio do plano): `BreaksWarning` compara as datas do formulário com a lista de quebras, no formulário de backtest e na página de dados de mercado, e oferece "Limitar a este regime", que só ajusta as datas. Nunca bloqueia. O card "Resultado entre as quebras de regime" (`breaks-card.tsx`) marca quebras **registradas depois** da execução.
* **Fase C implementada só com testes:** stop leva slippage no motor (o take-profit não), um gap além do stop preenche na abertura e depois escorrega, e o teto de volume nunca recusa uma saída. Os testes passaram sem mudar código de produção.
* **Fase D (derivativos):** registro **B-DERIVATIVES**, sem trabalho.
* **Decisões adotadas:** quebras globais ou por símbolo (`NULL` = todos); sem edição; só aviso. Testes: `test_break_segments.py`, integração (criar, duplicata, 422, filtro por símbolo, auditoria, execução com quebra, instantâneo preservado depois de apagar a quebra) e `test_risk_and_stops.py`.

### Ordem, dependências e estimativa

A → B (B depende de A para ler as quebras); C é independente e barata. Estimativa grosseira: A ≈ 2 dias (1,5 back, 0,5 front); B ≈ 3 (2 back, 1 front); C ≈ 0,5. A e B somam duas migrações, ou uma só se feitas juntas.

### Decisões pendentes (para o operador)

* Quebras globais, por símbolo ou ambas (proposta: ambas, `NULL` = global).
* Se a quebra pode ser editada (proposta: não, só apagar e recriar, para deixar rastro).
* Se o aviso de travessia vira bloqueio com confirmação (proposta: só aviso).
* Se o selo "criada depois do backtest" deve esconder o trecho da leitura padrão (proposta: só marcar).

### Fora do escopo (decidido)

Detecção automática de quebra estrutural (o livro 1, cap. 7 explica por que prever regimes não é confiável), ajuste por regime em varreduras (fica para depois da Fase B), e qualquer derivativo.

### Critérios de aceite gerais

Nenhum comportamento de negociação, risco ou ordem muda; execuções antigas continuam abrindo; nenhum `float` no domínio; `make check`, integração com `alembic upgrade head` e `downgrade -1` em banco com dados, `npm run lint`, `typecheck`, `test`, `format:check`, `check:consistency` e `build` verdes; telas em 1366 px e 360 px. Os números do livro (6,2% a 17,7% ao ano, Sharpe 0,54 a 1,6) são de moedas e futuros de 2002–2012, sem custos, e não valem para cripto à vista.

## Ressalvas

Os números citados (retorno anual de 6,2% a 17,7%, Sharpe de 0,54 a 1,6 e retornos de rolagem) são exemplos de moedas e futuros de 2002–2012, sem custos e parcialmente dentro da amostra; não dizem nada sobre cripto à vista.
