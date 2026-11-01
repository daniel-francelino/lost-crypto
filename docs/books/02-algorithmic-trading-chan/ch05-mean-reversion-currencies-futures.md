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

## Ressalvas

Os números citados (retorno anual de 6,2% a 17,7%, Sharpe de 0,54 a 1,6 e retornos de rolagem) são exemplos de moedas e futuros de 2002–2012, sem custos e parcialmente dentro da amostra; não dizem nada sobre cripto à vista.
