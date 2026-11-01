# Livro 3 · Capítulo 8 — Estudo de caso: mineração de regras no S&P 500

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 389–402, 419–422 e 437–439 foram lidas na íntegra. O catálogo extenso de 40 séries de entrada, fórmulas de indicadores (volume em saldo, fluxo monetário, volume negativo, razões de alta/baixa etc., pp. 403–418) e tipos de regras de cruzamento de limites (pp. 422–436) foram percorridos pelos títulos. Tratam de amplitude do mercado de ações dos EUA e dados intermercado, por isso não são resumidos.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Projeto do estudo**: 6.402 regras individuais para o S&P 500, nov. 1980–jul. 2005, para demonstrar testes de significância que corrigem seleção de dados (Reality Check de White aprimorado e permutação Monte Carlo de Masters, ambos com ganho de poder Romano–Wolf). | Exemplo aplicado. | 389–390 |
| C2 | **Evitar seleção de dados**: regras publicadas por terceiros foram excluídas deliberadamente, pois não se sabe quanto foram pesquisadas. Exemplo: regra de volume 9:1 dupla de Zweig, com parâmetros livres 9, 2 e 3 meses, só é significativa se o autor não pesquisou esses valores; o autor admite que leituras anteriores podem ter influenciado suas escolhas. | Contar o universo verdadeiro. | 390–391 |
| C3 | **Definição estatística**: população = retornos diários da regra no futuro prático imediato; parâmetro = retorno anual esperado; estatística = retorno médio anualizado em dados **sem tendência**; `H₀`: todas as regras não têm poder preditivo (bootstrap: todos os retornos esperados ≤0; permutação: pareamento aleatório); nível 0,05. **Significância prática difere da estatística**: com mais de 6.000 observações, vantagem irrelevante pode ser significativa; limite econômico depende do operador (retorno esperado de 5% ou 20%). | Plano de inferência pré-definido. | 391–394 |
| C4 | **Famílias de regras**: (1) tendência por operador de **rompimento de canal** de n períodos (CBO: comprado acima da máxima de n dias, vendido abaixo da mínima, excluindo barra atual); (2) **extremos e transições** por normalização de canal (estocástico) de média móvel ponderada linear de 4 dias, com cruzamento de limites; (3) **divergência** entre série auxiliar e S&P 500 por indicador duplamente normalizado. Todas binárias ±1; incluem-se **regras inversas**. Regras complexas combinadas não foram testadas, embora o autor observe que combinações podem agregar valor quando componentes isolados não lucram. | Famílias de regras. | 391–392, 419–439 |
| C5 | **Operadores**: média móvel é filtro passa-baixas, com atraso `(n−1)/2` dias para SMA versus `(n−1)/3` para média ponderada linear; **normalização de canal** `CN = (S_t − min_n)/(max_n − min_n) × 100` remove tendência (visão passa-altas); há concessão entre atraso e falsos sinais; não foram usadas janelas retrospectivas adaptativas. | Mecânica dos indicadores. | 396–402, 419 |
| C6 | **Projeto da grade de parâmetros**: 11 janelas em progressão aproximadamente **geométrica com razão ≈1,5** (3, 5, 8, 12, 18, 27, 41, 61, 91, 137, 205 dias); convenção de nomes como `TT-15-137` (tipo–entrada–janela) por causa da quantidade de regras; 858 regras de tendência = 39 entradas × 11 janelas × (tradicional + inversa). | Grade sistemática sem redundância excessiva. | 419–420 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Regra de rompimento de canal | ✅ | `donchian_breakout` (canal de entrada das máximas anteriores em `entry_period`; saída pelas mínimas de `exit_period`; barra atual excluída) corresponde a CBO long/flat com canal de saída separado. |
| Cruzamento de médias | ✅ | `ema_crossover` (exponencial; o livro usa simples/ponderada linear). |
| Projeto da grade retrospectiva | ⚠️ | Varreduras aceitam listas arbitrárias (`create_sweep` com dicionário `grid`); sem orientação, usuário pode criar grades lineares densas, muitas regras correlacionadas e N inflado sem informação nova. |
| Retornos sem tendência/significância prática | ❌ | Não aplicado; não há limite mínimo de vantagem econômica significativa. |
| Contagem de regras de fontes externas | ❌ | Não registrada (livro 3, cap. 6 O2). |
| Normalização de canal/regras osciladoras | ❌ | Não consta no catálogo. |
| Série intermercado/auxiliar | ❌ | Bot vê candles de um símbolo. |
| Regras complexas/combinadas | ❌ | Não há estrutura (ver também cap. 9). |

## 3. Oportunidades

### O1 — Predefinições de janelas geométricas para varreduras *(livro: C6, pp. 419–420)*

* **Problema:** grade linear (ex.: 5, 6, 7,…, 50) gera muitas regras quase duplicadas, aumentando N para correção de multiplicidade (livro 3, cap. 6) sem informação independente e consumindo processamento.
* **Proposta:** no formulário e auxiliar da API, oferecer gerador de “grade geométrica” (`start`, `end`, razão ≈1,5), com sequência do livro como predefinição e nota de que razão ~1,5 diferencia janelas adjacentes de forma relevante. Manter grades livres.
* **Benefício:** menos execuções e mais informativas, correção menor. **Complexidade:** muito baixa (interface/auxiliar). **Risco:** grade grosseira pode perder ótimo estreito, aceitável porque ótimo estreito indica fragilidade (livro 1, cap. 3 C10). **Validação:** teste do gerador; predefinição gera ≤11 valores por dimensão.

### O2 — Definir previamente limite de significância prática *(livro: C3, p. 394)*

Permitir que operador declare, antes da execução, retorno anual líquido mínimo (após custos) e drawdown máximo para considerar útil um resultado; mostrar **significância estatística e prática lado a lado** (vantagem pequena, embora significativa, é marcada “não vale negociar”). Amplia tolerância do livro 1, cap. 2 O3. **Complexidade:** baixa.

### O3 — Registrar origem de cada conjunto de parâmetros *(livro: C2, pp. 390–391)*

Adicionar `source` às configurações de backtest (ideia própria, artigo/post publicado, vencedor de varredura anterior, padrão) e contar escolhas de parâmetros publicadas ou herdadas no universo, pois o histórico de busca é desconhecido (exemplo Zweig). **Complexidade:** baixa. **Validação:** teste da API para o campo e contagem do universo com entradas externas.

### O4 — Indicador reutilizável de oscilador/normalização de canal *(livro: C4, C5, pp. 401–402, 421)*

Criar função pura `channel_normalize(series, n)` (estilo estocástico) e WMA em `strategies/domain`, como auxiliares compartilhados para facilitar estratégia de reversão (livro 2, cap. 3 O1) e oscilador neutro à tendência com limite fixo, preferido pelo livro para séries sem tendência. **Complexidade:** baixa. **Risco:** ampliar conjunto de auxiliares; manter testes unitários. Não constitui estratégia por si só.

### O5 — Entrada de série auxiliar/intermercado no bot *(livro: C4, pp. 391, 437–439 · aplicação cripto proposta por nós)*

A família de divergência compara série auxiliar com a negociada. Em cripto, BTC é referência natural para altcoins; pares de cotação como ETH/BTC já são mercados à vista. Parâmetro `companion_symbol` exige candles de várias séries no contexto (`StrategyContext` hoje recebe um candle). Hipótese **H-COMPANION**, mudança grande; apenas registrar.

### Não aplicável

Indicadores de amplitude/volume de ações dos EUA e de títulos, regras inversas long/short e especificidades do S&P 500.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 predefinições de grade geométrica | média | – | – | muito baixa | – |
| 2 | O3 origem dos parâmetros | média | – | – | baixa | livro 3, cap. 6 O2 |
| 3 | O2 significância prática | média | média | – | baixa | métricas |
| 4 | O4 auxiliares de indicadores | baixa | – | – | baixa | livro 2, cap. 3 O1 |
| 5 | O5 série auxiliar | – | – | – | alta | H-COMPANION |

## 5. Arquivos afetados

Formulário de varredura (`routes/backtests/new`, `components/backtests`), `backtesting/application/service.py` (auxiliar opcional e `source`), `analytics/domain`, auxiliares em `strategies/domain`, `docs/openapi.json` e testes.

## 6. Plano incremental

1. Gerador e predefinição de grade geométrica.
2. Campo `source` e contagem de universo.
3. Limites de significância prática e exibição.
4. Auxiliares de indicadores quando a estratégia de reversão for criada.

## 7. Critérios de aceitação e testes

* Gerador reproduz 3, 5, 8, 12, 18, 27, 41, 61, 91, 137, 205 (considerado arredondamento) com a razão indicada.
* Varreduras atuais não mudam sem opção nova; Ruff, mypy e testes passam.

## Ressalvas

Tudo depende de um único estudo num índice; o livro informa que nenhuma das 6.402 regras foi significativa após correção (ver cap. 9). A razão de grade 1,5 é escolha do autor.
