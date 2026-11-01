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

## Ressalva

O autor afirma que as estratégias do livro não estão livres de armadilhas e podem falhar quando o regime de mercado muda (p. 187). Este relatório não faz afirmações sobre retornos esperados.
