# Livro 2 · Conclusão

*Algorithmic Trading*, Chan (2013), pp. 187–189. Páginas do livro (PDF = livro + 18). Referência de implementação: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. A bibliografia e as páginas sobre o autor e o site não foram analisadas.

## 1. Resumo

| ID | Conceito | Páginas |
|---|---|---|
| C1 | O livro ilustra conceitos, não oferece receitas: as estratégias podem conter as armadilhas do Capítulo 1 e falhar quando o regime de mercado muda. O leitor deve testá-las fora da amostra. | 187 |
| C2 | Primeiro, compreenda a **ineficiência**; depois, construa um modelo simples (linear) e evite regras arbitrárias. | 187 |
| C3 | Trate o trading de forma **científica**: hipótese → modelo → teste em dados não vistos → se falhar, investigue o motivo (GLD/GDX e petróleo), em vez de apenas acrescentar regras. | 187–188 |
| C4 | **Ainda é preciso exercer julgamento**: reduzir a alavancagem antes de um evento importante (o autor recomenda não fazê-lo se o modelo já resistiu a situações de estresse anteriores; a postura inicial deve ser conservadora); usar Kelly agregado ou por estratégia (segundo o autor, o cálculo por estratégia permite que as estratégias com pior desempenho sejam eliminadas rapidamente). | 188 |
| C5 | Divergências na operação real muitas vezes decorrem de **mudanças de regime**, não de erros no backtest. Cabe ao gestor avaliar se os modelos continuam válidos; segundo Kahneman, algoritmos superam o julgamento de especialistas quando há muita incerteza. | 188–189 |

## 2. Diagnóstico e oportunidades

Os pontos já estão cobertos por recomendações anteriores:

* C2/C3 → registros de hipóteses e análises pós-incidente ([cap. 4 O1](ch04-mean-reversion-stocks-etfs.md)), diagnósticos antes de criar estratégias ([cap. 2 O1](ch02-basics-of-mean-reversion.md)) e os IDs de hipótese `H-MOM-REV` e `H-RISK-INDICATOR`.
* C4 → políticas documentadas ([cap. 8 O7](ch08-risk-management.md)); o dimensionamento por estratégia já corresponde ao funcionamento dos bots ([cap. 8 O5](ch08-risk-management.md)).
* C5 → identificação de mudanças de regime e monitoramento da divergência entre operação real e backtest ([cap. 5 O1](ch05-mean-reversion-currencies-futures.md), [cap. 1 O4](ch01-backtesting-and-automated-execution.md)).

Não há novas oportunidades identificadas.

## 3. Plano de implementação do livro 2 (ordem entre capítulos)

Escrito em 2026-11-01, com o código verificado nessa data. A conclusão não traz oportunidade nova; esta seção só **ordena** o que os capítulos 1 a 8 propõem, para que as dependências entre eles fiquem num lugar só. Cada fase está detalhada (back-end, front-end, testes e aceite) na seção 8 do capítulo indicado. **Nada aqui foi aprovado nem implementado.**

| Ordem | Fase | Capítulo | Migração | Depende de |
|---|---|---|---|---|
| 0 | Testes que faltam nos módulos já implementados (`half_life`, `regime`, `sizing`, `tail_risk`, `max_holding_candles`) | [2, Fase 0](ch02-basics-of-mean-reversion.md) | – | – |
| 1 | Significância gaussiana (campos aditivos em `Metrics`) | [1, Fase A](ch01-backtesting-and-automated-execution.md) | – | – |
| 2 | Contador de reutilização da janela de teste | [1, Fase B](ch01-backtesting-and-automated-execution.md) | – | – |
| 3 | Hurst e razão de variâncias; meia-vida como dica nos formulários | [2, Fases A e B](ch02-basics-of-mean-reversion.md) | – | 0 |
| 4 | Comparar horizontes de tempo (só front) | [7, Fase A](ch07-intraday-momentum.md) | – | 1 (coluna de significância, opcional) |
| 5 | Sharpe real × backtest do bot | [1, Fase D](ch01-backtesting-and-automated-execution.md) | – | – |
| 6 | Notas de análise em bots e backtests | [4, Fase A](ch04-mean-reversion-stocks-etfs.md) | – | – |
| 7 | Excursão adversa e aviso de stop | [8, Fase A](ch08-risk-management.md) | sim | – |
| 8 | Curvas de crescimento e drawdown por exposição | [8, Fase B](ch08-risk-management.md) | – | `sizing` do livro 1 (já feito) |
| 9 | Quebras de regime nomeadas e métricas por trecho | [5, Fases A e B](ch05-mean-reversion-currencies-futures.md) | sim (1 ou 2) | – |
| 10 | Grade de correlação defasada; sensibilidade à data inicial | [6, Fases A e B](ch06-interday-momentum.md) | – | 3 (compartilha a página de dados) |
| 11 | Defesa contra tick incorreto (`max_close_jump_pct`) | [3, Fase B](ch03-implementing-mean-reversion.md) | sim | – |
| 12 | Monitor de deterioração e alerta de saída protetora | [4, Fase B](ch04-mean-reversion-stocks-etfs.md), [8, Fase C](ch08-risk-management.md) | – | 5 |
| 13 | Teste de entradas aleatórias | [1, Fase C](ch01-backtesting-and-automated-execution.md) | sim | 1 |
| 14 | Estratégia de reversão à média (plano do livro 1, cap. 7, Fase 2) e filtro de tendência | [3, Fase A](ch03-implementing-mean-reversion.md), [4, Fase C](ch04-mean-reversion-stocks-etfs.md) | – | 3 (diagnósticos) e `StrategyStyle` do livro 1, cap. 6, Fase C |
| 15 | Modelo opcional de slippage | [7, Fase B](ch07-intraday-momentum.md) | sim | slippage realizado de semanas de paper |
| 16 | Encerrar em vez de pausar (`drawdown_action`), só em paper | [8, Fase D](ch08-risk-management.md) | sim | 7 e 8 |
| – | Documentar decisões de julgamento | [8, Fase E](ch08-risk-management.md) | – | – |
| – | Pesquisa transversal e pesquisa por horário | [4, Fases D e E](ch04-mean-reversion-stocks-etfs.md) | – | dados de vários pares |
| – | Walk-forward e validação cruzada | [1, Fase E](ch01-backtesting-and-automated-execution.md) | – | livro 5 |
| – | Verificação do volume do agressor | [7, Fase C](ch07-intraday-momentum.md) | só se positiva | – |

**Estado da implementação (2026-11-01).** Feito: 0 (testes), 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 (monitor de deterioração e alerta de saída protetora), 13, 14 (estratégia de reversão; o filtro de tendência **não**), 15, 16 e a documentação de julgamento. Não feito, por decisão ou por falta de insumo: o **filtro de tendência** (sexto parâmetro, estoura o limite de 5), a **pesquisa transversal** e a **pesquisa por horário** (precisam de vários pares importados), o **walk-forward** (depende do livro 5), o **volume do agressor** (verificado no `ccxt`, mas não implementado nem testado contra a API real) e a comparação **slippage previsto × realizado** do bot. Migrações criadas: `0015` a `0020`.

**Migrações:** cada uma usa o próximo número livre quando for implementada (hoje a última é `0014_backtest_regime`); as fases 7, 9, 11, 13, 15 e 16 são as que mexem no banco, e 9 pode ser uma migração só. **Nenhuma salvaguarda live é alterada por qualquer fase.**

**Decisões que atravessam capítulos:** o valor-p contínuo exigiria uma conversão `float` isolada (caps. 1 e 6; proposta: não), o limite de 5 parâmetros por estratégia (caps. 3 e 4) e o bootstrap em `Decimal` (cap. 8).

## Ressalva

O autor afirma que as estratégias do livro não estão livres de armadilhas e podem falhar quando o regime de mercado muda (p. 187). Este relatório não faz afirmações sobre retornos esperados.
