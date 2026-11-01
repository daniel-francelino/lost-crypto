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

## Ressalvas

Os números de desempenho (retornos anuais de 8,7%, 13,7%, 46%, 73%; Sharpe até 4,7) vêm de backtests de ações dos EUA, brutos de custos e sujeitos a viés de sobrevivência. Alguns têm falhas reconhecidas pelo autor (janelas escolhidas retrospectivamente e ruído do preço de abertura). Não são expectativas para cripto. A conclusão de que pares de ETFs superam pares de ações é do autor e refere-se ao mercado americano em 2013.
