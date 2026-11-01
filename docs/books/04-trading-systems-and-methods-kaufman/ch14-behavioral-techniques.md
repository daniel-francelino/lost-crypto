# Livro 4 · Capítulo 14 — Técnicas comportamentais

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** lidas pp. 617–620 (notícias), 623–628 (**negociação de eventos**) e 648–649 (Fibonacci). Restante de pontuação de notícias (620–622), relatório Commitment of Traders, opinião/opinião contrária (635–647), ondas de Elliott, alvos Fibonacci, bússola de Fischer, Gann e astrologia financeira (649–684) **não** foram lidos em detalhe. Elliott/Fibonacci/Gann/astrologia são métodos subjetivos ou não testáveis, excluídos pelo projeto (ver [livro 3, cap. 1](../03-evidence-based-technical-analysis-aronson/ch01-objective-rules-and-their-evaluation.md)).

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Sistemas de curto prazo miram **comportamento do investidor** mais que fatores macro. Notícias são “o maior elemento individual na formação de preços”; quantificá-las por pontuação (+/−; ex. dados programados) é difícil. Estudo que pontuou artigos do Wall Street Journal achou notícias alinhadas à direção atual do mercado ~70% das vezes perto de viradas e concluiu que mercado reflete em grande parte as notícias. Mercados reagem à antecipação e relatórios de economias importantes em períodos de estresse. | Notícias como entrada. | 617–619 |
| C2 | **Cobertura da mídia é indicador atrasado e consensual** (manchetes de seca ou alta aparecem em extremos). | Sinais contrários. | 623 |
| C3 | **Negociação de eventos**: dois casos — relatórios programados (movimentos moderados, geralmente revertidos) e **choques de preço** por notícias inesperadas (maior volatilidade, “desproporcional ao risco normal”; muitos não planejam para eles). Lucro não vem de posicionar-se antes do relatório (50% de chance, alto risco), mas de **estudar padrão após reação inicial**. Depois de choque pode haver continuação (reação insuficiente/mudança estrutural) ou reversão (reação excessiva) nos ~3 dias seguintes; relação entre tamanho inicial e padrão posterior deve ser medida (choque pequeno → continuação; grande → possível excesso). Eventos candidatos precisam de volatilidade suficiente, probabilidade favorável e/ou utilidade de hedge. | Negociar consequência, não evento. | 623–625 |
| C4 | **Expectativas já estão no preço antes do relatório**; surpresa = resultado real menos esperado. **Medida de evento**: `razão de volatilidade = true range_t / ATR médio dos n dias anteriores, defasado m dias`, em geral `n=60`, `m=30`; **razão >3,0 indica possível choque noticioso**; usar amplitude verdadeira porque choque pode abrir com lacuna. | Detectar choques objetivamente. | 625–626 |
| C5 | **Regras (Warwick)**: comprar no fecho se mercado fechar no **terço superior da amplitude diária** em dia de evento e histórico mostrar continuação; manter número de dias pré-definido conforme defasagem; usar stop. Estudo antigo de milho: 81% da variação no dia do evento, reversão típica de 8% em quatro dias e saldo de 27% na direção original em 45 dias. Sequência típica: choque afeta juros, depois câmbio e ações, com defasagens instáveis. | Regra concreta e limites. | 627–628 |
| C6 | **Sequência e razões Fibonacci** aparecem na análise de preços; livro apresenta coincidências (“interessantes para uns, significativas para outros”), mas afirmações não são testáveis como formuladas. | Apenas contexto. | 648–649 |

Referências a cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Detecção de choque (razão de volatilidade) | ❌ | Só existe filtro de candle suspeito (`max_candle_range_pct`, 25% padrão) em `risk_management/domain/models.py`, proteção grosseira contra amplitude muito grande; sem razão versus volatilidade recente. |
| Estudo do comportamento pós-choque | ❌ | Nenhum. |
| Plano para choques de preço | ⚠️ | Stops nativos, kill switch, pausas por perda/drawdown e limites globais; sem análise de estratégias em choques cripto históricos. |
| Notícias/eventos | ❌ | Nenhum (B-EVENTS). |
| Métodos subjetivos | n/a | Excluídos. |

## 3. Oportunidades

### O1 — Detector de choque por razão de volatilidade e estudo posterior *(livro: C3–C5, pp. 624–627)*

Implementar razão de volatilidade do livro (amplitude verdadeira atual dividida pelo ATR médio defasado; padrões 60/30 e limite 3,0) como função pura. Relatório de diagnóstico por par/intervalo identifica candles de choque e mede, em horizontes de 1–5 candles, retorno futuro **condicionado à direção do choque e à posição do fecho na faixa (20% superior/inferior)**, com amostra, eras e benchmark incondicional. Replica estudo sem feed de notícias (choque = candle anormal, qualquer causa).

**Benefício:** verifica se choques cripto tendem a continuar ou reverter no horizonte operado; informa stops/dimensionamento e validade de pausar ou negociar após choque. **Complexidade:** baixa a média. **Riscos:** páginas tratam de datas de relatórios; choques cripto têm causas mistas (liquidação, invasão, listagem); amostras pequenas; testes múltiplos entre horizontes, limites e posições do fecho. **Validação:** série sintética com choques e continuação/reversão inseridas.

### O2 — Gestão de risco após choque: pausar/reduzir *(livro: C3, C4, pp. 623, 626)*

Limite opcional: após candle com razão de volatilidade acima do limite, bloquear entradas por `k` candles (amplia `max_candle_range_pct`, que só observa candle atual) ou reduzir tamanho. Livro trata choques como principal risco de sobrevivência e observa que muitos não se preparam; proteção barata e compatível com módulo atual. Desligada por padrão; avaliar via O1 e modo do backtester atento a risco (livro 1, cap. 5 O2).

**Riscos:** pode bloquear melhores entradas (rompimentos ocorrem durante choques); efeito líquido desconhecido. **Complexidade:** baixa. **Validação:** testes unitários e comparação de backtest com/sem proteção.

### O3 — Cenários de estresse: repetir choques históricos com limites de risco atuais *(livro: C3, p. 623; relacionado aos caps. 21–22)*

Criar biblioteca pequena de janelas históricas de choque cripto a partir de candles armazenados (identificados em O1) e testar cada configuração de bot sob essas janelas, reportando drawdown máximo de 1 e 3 candles e slippage nos piores candles versus limites configurados. **Complexidade:** média. Relaciona-se ao teste de choques do cap. 21 de Kaufman.

### O4 — Não usar sinais de mídia; sem pipeline de notícias por enquanto *(livro: C2, p. 623)*

O próprio livro observa que cobertura é atrasada. Nenhum trabalho além de manter B-EVENTS para eventos programados.

### Não aplicável

Relatório CFTC Commitment of Traders, pesquisas de opinião contrária, retrações/alvos Fibonacci, ondas de Elliott, Gann e astrologia.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 detector/estudo de choques | média | média | – | baixa–média | módulo de diagnóstico |
| 2 | O3 cenários de estresse | – | **alta** | média | média | O1 |
| 3 | O2 proteção após choque | – | média | – | baixa | O1 |
| 4 | O4 não usar mídia | – | – | – | nenhuma | – |

## 5. Arquivos afetados

`analytics/domain/` (amplitude verdadeira, razão de volatilidade, estudo de eventos), endpoint de diagnósticos, `risk_management/domain/models.py` (proteção opcional), `backtesting` (executor de estresse), página de diagnósticos e testes.

## 6. Plano incremental

1. Funções de amplitude verdadeira/razão e relatório de estudo de eventos.
2. Cenários de estresse das janelas detectadas.
3. Proteção opcional avaliada pelo fluxo de validação.

## 7. Critérios de aceitação e testes

* Razão confere com cálculo manual; choques inseridos são detectados no limite 3; contagens do estudo por classe fecham corretamente.
* Proteção desligada por padrão; risco não muda sem habilitação; Ruff, mypy e testes passam.

## Ressalvas

Números de milho/títulos vêm de 1960–1990 e o autor diz que defasagens variam conforme estado econômico. Páginas lidas não demonstram padrão cripto pós-choque explorável.
