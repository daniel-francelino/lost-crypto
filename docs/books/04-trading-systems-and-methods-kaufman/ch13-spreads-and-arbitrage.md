# Livro 4 · Capítulo 13 — Spreads e arbitragem

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** lidas pp. 565–568, 572–574 e 596–598; títulos de pp. 568–572 e 574–616 percorridos. Mecânica detalhada de spreads em mercados específicos de futuros, arbitragem de opções, fórmulas de preço e estudos intermercado (pp. 568–572, 575–595, 598–616) **não** foram lidos nem resumidos.

## 1. Resumo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Termos: **spread/straddle** (posições opostas em mercados relacionados), **negociação de pares** (comprado/vendido em duas ações), **arbitragem** (dinâmica de spread calculável, por exemplo mesmo título/vencimento ou commodity em dois locais); **arbitragem de valor relativo** quando forças de mercado causam divergência entre produtos parecidos, mas não idênticos. Spreads removem risco direcional (pernas tendem a variar juntas; uma lucra e outra perde) e diversificam carteiras apenas compradas. | 565 |
| C2 | Spreads intramercado de futuros reduzem risco e podem lucrar; compensação de margem permite alavancagem, **ao contrário de ações, em que ambas as pernas precisam de financiamento integral**. Comportamento varia: futuros financeiros próximos do vencimento reagem mais rápido; metais preciosos seguem custo de carregamento; metais industriais invertem em escassez; câmbio a prazo reflete juros/política; safras têm carregamento no ano agrícola; pecuária não pode ser armazenada, então meses são independentes. | 566–567 |
| C3 | **Custo de carregamento** (estrutura a termo): juros, armazenamento, seguro; **contango** versus **backwardation** (carregamento negativo); custo de carregamento permanece implícito mesmo em estrutura invertida. | 567 |
| C4 | **Teste de relação entre spreads**: calcular desvio-padrão dos retornos do spread em relação às pernas; “quanto mais forte a relação entre A e B, menor o desvio-padrão de F”. | 572 |
| C5 | **Condições de arbitragem** (exemplo espacial: peso cotado por bancos em Tóquio e Frankfurt): diferença precisa superar bid-ask/custo de execução; deve haver crédito/acesso a ambas contrapartes; operações **simultâneas**. Arbitragem em larga escala é de instituições que monitoram cotações globais e operam alto volume por diferenças pequenas; oportunidades verdadeiras têm lucros baixos e pouca liquidez; risco cresce com tempo na posição. | 572 |
| C6 | **Preço de futuros**: rendimento de conveniência `CY = F − S − S·r·(T−t)/365` (exemplo ouro, 1,20% em seis meses); faixa de valor justo limitada por financiamento, armazenamento e conveniência, ampliada por taxas de empréstimo/aplicação distintas e custos. Fora da faixa → arbitragem. | 573–574 |
| C7 | **Carry trade**: tomar moeda de juros baixos e comprar moeda de juros altos; executar por contratos a prazo/futuros, dependendo de **viés a termo** (moedas de juros altos tendem a valorizar ou cair menos), não da captura direta do diferencial. Risco principal é variação cambial anular ganho de juros; exige diversificação entre moedas. | 596–597 |

Capítulo trata de instrumentos que o projeto não negocia; há quatro pontos de contato com cripto, como **adaptação nossa**.

## 2. Diagnóstico

| Conceito | Situação | Evidência |
|---|---|---|
| Spreads/pares | ❌ n/a | Um ativo, apenas comprado, sem perna vendida. |
| Arbitragem entre corretoras/triangular | ❌ n/a | Um adaptador por conexão; sem execução simultânea de duas pernas nem gestão de saldo intercorretoras. |
| Carry (taxa de financiamento/base) | ❌ n/a | Sem derivativos. |
| Verificar custos antes de agir numa diferença de preço | ✅ em princípio | Taxas/slippage sempre incluídos na simulação. |

## 3. Oportunidades

### O1 — Registrar condições de arbitragem como lista de triagem e manter arbitragem cripto fora do escopo *(livro: C5, p. 572 · adaptação)*

Condições do autor (diferença maior que bid-ask, acesso às duas contrapartes e execução simultânea) correspondem a fatos práticos de cripto: atrasos/taxas de transferência entre corretoras, níveis de taxa, limites de requisição e ordens não atômicas. Sistema varejista numa conta sem colocalização provavelmente não consegue capturá-las. **Decisão recomendada: não buscar arbitragem entre corretoras ou triangular**; incluir lista no modelo de ideia para exigir resposta a cada condição. **Complexidade:** apenas documentação.

### O2 — Carry de taxa de financiamento/base como dado para futura decisão de derivativos *(livro: C3, C7, pp. 567, 596–597 · especulativo)*

Se houver suporte a futuros perpétuos (**B-DERIVATIVES**, livro 2, cap. 5 O3), enquadrar pelo carry (incluindo que preço a termo já desconta diferencial e lucro depende de viés a termo) e risco de movimento à vista superar carry. Nenhuma ação agora.

### O3 — Verificar relação entre instrumentos antes de qualquer ideia de pares *(livro: C4, p. 572)*

Em relatório de pesquisa que compare símbolos (ex.: altcoin/BTC), usar teste rápido do livro: desvio-padrão dos retornos da razão/diferença versus pernas. Adição barata ao diagnóstico (livro 2, cap. 2 O1) e pré-requisito de `companion_symbol` (H-COMPANION, livro 3, cap. 8 O5). **Complexidade:** muito baixa.

### Não aplicável

Custos de carregamento de commodities, rendimento de conveniência, paridade de juros e execução de carry cambial, spreads de calendário.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 lista e decisão | – | média | – | documental | – |
| 2 | O3 teste de relação | baixa | – | – | muito baixa | diagnósticos |
| 3 | O2 enquadramento de carry | – | – | – | nenhuma | decisão de derivativos |

## 5–7. Arquivos, plano e aceitação

Documentação (`docs/`) e, para O3, função pura em `analytics/domain`; nenhuma mudança de negociação. Aceitação: O3 retorna razão de desvios em casos de teste; Ruff, mypy e testes passam.

## Ressalvas

A maior parte do capítulo trata de futuros e arbitragem institucional e não foi lida em detalhe. As páginas lidas não sustentam arbitragem varejista em cripto; recomendação de não persegui-la baseia-se nas condições do autor, não em dados medidos de cripto.
