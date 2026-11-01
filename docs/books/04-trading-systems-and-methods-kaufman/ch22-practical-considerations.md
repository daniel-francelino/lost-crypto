# Livro 4 · Capítulo 22 — Considerações práticas

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foram lidas as pp. 983–1015. A parte final (pp. 1016–1026: demais relações de compromisso, limites de negociação em mercados futuros e semelhança entre sistemas/impacto dos sistemas técnicos nos mercados) **não foi lida**; não se fazem afirmações sobre ela.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Uso e abuso do computador**: automatizar um processo claro; plataformas de desenvolvimento previnem look-ahead (“o software impede que você veja o preço de amanhã”); usar ferramentas de terceiros (salvar tabelas de otimização em uma planilha para ordenar, calcular médias e criar gráficos). **“Poder demais”**: jogar indicadores em um caldeirão e deixar força bruta, redes neurais ou algoritmos genéticos encontrar o melhor é sobreajuste; menos poder computacional força o raciocínio antecipado. | Disciplina no uso de ferramentas. | 984–988 |
| C2 | **Precisão e limpeza dos dados**: fontes diferem (máximas/mínimas), ocorrem erros de deslocamento decimal e escalas distintas entre fornecedores. **Verificações diárias**: outliers (>4% em relação ao valor anterior ou a uma porcentagem predefinida), **datas ausentes** (mais de 4 dias sem dados sinalizados), **abertura/fechamento fora da faixa máxima-mínima** (impossível; corrigir ou remover). **Verificações intradiárias**: frequência dos dados versus média por intervalo de 5 minutos (períodos sem dados); grandes saltos que revertem em segundos (erro ou ordem que não poderia ser absorvida). Dilema: um sistema criado com dados limpos pode gerar muitos sinais extras ao vivo por causa de preços ruins; às vezes é melhor desenvolver com dados sujos para reduzir a sensibilidade do sistema. | Integridade dos dados. | 985–986 |
| C3 | **Começar pelas técnicas padrão**: a velocidade da tendência importa mais que a fórmula; combinar tendência com oscilador para timing de entrada é um conceito amplo, atendido por muitos indicadores; aprender com ferramentas padrão antes de programar algo personalizado. | Evitar novidade desnecessária. | 986–987 |
| C4 | **Mais dados é melhor**, a menos que uma mudança estrutural invalide dados antigos; se anos antigos tinham baixa volatilidade que provavelmente não voltará, a estratégia “ao menos não deveria registrar perdas” nesse período. | Extensão do histórico. | 988 |
| C5 | **Paper trading**: o conjunto fora da amostra sempre acaba sendo usado mais de uma vez, então paper trading é a verificação mais segura; **documentar expectativas primeiro** (frequência de operações, permanência, porcentagem de acertos, tamanho dos lucros e perdas); no paper, assumir o **pior preço nos 5 minutos após um sinal intradiário** (ou o pior da faixa de fechamento para ordens no fechamento); começar com valor pequeno. | Verificação da realidade antes de arriscar capital. | 988 |
| C6 | **“Deveria funcionar, mas não funciona”**: resultados possíveis — lucrativo, não lucrativo, impossível de implementar, demorado ou caro demais. Construir aos poucos e comprovar cada parte antes de adicionar a próxima; parar se o desempenho piorar conforme os recursos são adicionados. Desenvolvimento **vertical (em etapas) versus integrado**: na abordagem vertical, a regra principal deve ser lucrativa sozinha e cada recurso é testado sobre ela; uma solução integrada que só dá lucro com o filtro é sofisticada ou sobreajustada — decidir **comparando a porcentagem de combinações de parâmetros lucrativas com e sem o recurso** (medida de robustez do cap. 21). Sistemas **transparentes versus complexos**: os complexos são difíceis de depurar e não podem ser confirmados visualmente em um gráfico. | Como desenvolver e diagnosticar. | 988–990 |
| C7 | **Isolar problemas**: (1) regra ambígua interpretada incorretamente (por exemplo, “volume confirma” implementado como volume de hoje > ontem em vez de > média de 10 dias); (2) técnica não funciona na faixa testada — resultados negativos são feedback (combinar tendência longa com média: a longa identifica direção e a média captura movimentos dentro dela); (3) funciona em alguns mercados, mas não em outros (ativos semelhantes de um setor deveriam ter comportamento parecido; em futuros, renda fixa tem as tendências mais longas e índices acionários são os mais ruidosos); (4) pressupostos feitos sobre dados selecionados; (5) **ignorar algumas grandes perdas** (LTCM: remover as maiores perdas históricas reduziu o risco aparente e justificou alavancagem; “o histórico não mostra risco suficiente”); (6) **avaliar mal a volatilidade**: usar o mesmo número de contratos em 2000 e 1996 significava seis vezes a volatilidade; stops e tamanhos devem se adaptar; (7) **evolução dos mercados**: mais participantes adicionam ruído, sistemas de tendência entram/saem mais tarde e mostram deterioração em testes longos. | Lista de verificação de depuração. | 990–991 |
| C8 | **Sistemas simples podem funcionar** (tendência de longo prazo; um cruzamento duplo teria saído depois do pico de 2000 e antes de 2008) e “ser proativo pode fazer perder uma pequena oportunidade, mas evitar uma grande perda”. | Simplicidade. | 992 |
| C9 | **Eventos extremos**: choques de preço são a causa mais provável de perdas catastróficas e criam a maior diferença entre resultados de teste e reais. **Durante um choque, a diversificação falha (correlações vão a 1)** porque o dinheiro, e não os fundamentos, move os mercados; backtests tratam choques como dias normais e **a seleção é a maior beneficiária dos choques**, o que explica resultados piores fora da amostra e ao vivo. Quatro estudos de caso (Gorbachev, 1991; eleição britânica, 1992; Guerra do Golfo, 1990–91; 11 de setembro): choques nem sempre prejudicam seguidores de tendência; **os preços costumam mudar de direção após o choque ser absorvido**; a volatilidade **sempre aumenta**; um salto de 16% no suco de laranja reverteu 15% em dois dias (2012). Identificação: amplitude de 1 dia ≥ 5× ATR. | Risco de eventos. | 992–997 |
| C10 | **Gestão de crise**: reservas para sobreviver a reversão extrema costumam reduzir o retorno abaixo do rendimento de títulos, então são necessárias táticas: (1) após um **ganho inesperado** com o choque, **sair ou reduzir**; (2) após **grande perda**, manter a posição esperando reversão (pode levar dias e elevar o risco); (3) com reservas suficientes, adicionar no pico de volume ou quando a volatilidade cai; quando a ordem de saída poderia ser enviada, a operação já absorveu a maior parte do risco. | Regras para choques. | 997–998 |
| C11 | **Desconexão do sistema em crise**: linhas de tendência (50/100/200 dias) viram para baixo no preço mínimo do crash de 1987 e ficam dessincronizadas por muito tempo; “manter dogmaticamente uma posição vendida porque a linha de tendência está descendente deixa o operador fora de sintonia com a realidade”. Suspender regras de tendência, usar regras de crise predefinidas e **reinicializar as tendências** quando a volatilidade cair. A queda lenta de 2008 foi diferente (não um choque isolado) e seguidores de tendência lucraram. | Regras falham durante choques. | 998–1000 |
| C12 | **Teoria das sequências** (jogos de azar): probabilidade de uma sequência de n é (1/2)^(n+2); em 256 lançamentos, espera-se uma sequência máxima de 7–8; cada duplicação dos testes acrescenta 1 à sequência máxima. **Martingale** (dobrar após perda) ganha pequenas quantias frequentemente, mas arrisca ruína; o limite da aposta só impede a ruína se o teto da duplicação for maior que a sequência máxima; **anti-Martingale** (dobrar após ganhos) lucra muito se uma sequência longa ocorrer cedo. | Dimensionamento com base em sequências. | 1000–1003 |
| C13 | **Sequências aplicadas à negociação**: sequências de dias de alta/baixa em 15 mercados futuros (2000–2011) diferem do acaso (DAX tem reversões de 1 dia demais; Eurodólares, de menos: esperar versus entrar imediatamente). **Martingale dentro da tendência** (adicionar após fechamento em baixa dentro de tendência de alta, limite de 8 contratos): Eurodólares (muito tendencial) melhorou a razão (6,67 → 8,28); S&P (ruidoso) não melhorou (razão 1,18; versão limitada teve desempenho inferior). **Anti-Martingale dentro da tendência**: versão sem limite perdeu dinheiro (−16.443) porque a maior posição teve perda; versões com limites de 2/4/8 melhoraram a razão (10,95; 10,36; 9,81) nos Eurodólares, mas não no S&P; também são descritos Martingale fracionário (×1,5) e entrada contrária atrasada. **Regra de persistência de Gustafson** (comprar após 4 fechamentos em baixa, sair após 5 em alta ou 8 dias; 78% de acertos e US$ 35 mil de lucro na amostra; teste mais longo, 76% e US$ 348 mil, em mercado de alta e somente comprado). | Apostar em sequências funciona? | 1004–1011 |
| C14 | **Negociação seletiva**: substituir discricionariamente sinais do sistema costuma favorecer manter posições perdedoras até que fiquem lucrativas; “princípios de negócio devem prevalecer sobre as emoções”. **Filtrar operações perdedoras**: confirmação por vários indicadores ou mercados produz “a aparência de um sistema muito bom”, mas é sobreajuste; “a solução simples, mesmo com risco maior que o desejado, costuma ser a melhor”; **nunca misturar sistemas caixa-preta** que não se pode testar. | Disciplina e sobreajuste. | 1011–1012 |
| C15 | **Relações de compromisso entre sistemas**: seguimento de tendência tem muitas pequenas perdas e poucos grandes ganhos (30–35% de acertos é normal; 40–45% é irreal); períodos longos capturam mais da cauda longa, mas atrasam mais; a sequência de perdas faz parte do risco. **Reversão à média** tem muitos pequenos lucros e poucas grandes perdas, exige timing, usa alvos definidos e, por isso, não deve limitar perdas. Há relação de compromisso entre distância de entrada (limiar), número de oportunidades e risco por operação (figs. 22.14–22.15). | Entender o formato de retorno de cada estilo. | 1012–1015 |

As observações sobre cripto abaixo são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Prevenção de look-ahead | ✅ (projeto) | Estratégias recebem o histórico até o candle do sinal; o motor executa na abertura seguinte (`engine.py`). Ainda falta teste de truncamento (livro 1, cap. 3, O2; cap. 17, O2). |
| Validação de candles (outliers, intervalos ausentes, integridade OHLC) | ❌ | `market_data/domain/models.py` não valida integridade OHLC; `_check_candles` exige apenas ≥1 candle; gaps são ignorados. |
| Paper trading com expectativas documentadas | ⚠️ | Há paper trading e uma etapa mínima de dias antes do ao vivo; não se registra o perfil esperado nem se faz comparação. |
| Execuções pessimistas no paper | ❌ | O ambiente paper executa pelo preço/slippage simulado; não há modo “pior preço dos próximos N minutos”. |
| Evidência de desenvolvimento vertical versus integrado | ❌ | Não há comparação de robustez de filtros (porcentagem de combinações lucrativas com/sem o recurso). |
| Tamanho/stop adaptado à volatilidade | ❌ | Ver cap. 20, O2. |
| Detecção de choque e regras de crise | ❌ | Não há. O módulo de risco tem `max_candle_range_pct`, `kill switch` e limites ao vivo; não há modo de crise sensível à volatilidade. |
| Stops nativos ao vivo | ✅ | A operação ao vivo usa ordens stop da corretora (protege contra desconexão, mas não contra gaps/slippage além do stop). |
| Dimensionamento Martingale ou anti-Martingale | ❌ | Não existe e não é recomendado (ver O6). |
| Intervenção discricionária | ⚠️ | Existem controles manuais (parar/pausar bot, kill switch); não há regra para documentar intervenções. |
| Mistura de sistemas caixa-preta | n/a | Estratégias têm código aberto no registro. |

## 3. Oportunidades

### O1 — Validador de qualidade dos dados de candles (integridade, gaps e outliers) *(livro: C2, pp. 985–986)*

* **Proposta:** função pura executada na importação e antes de cada backtest/varredura para verificar: (1) `low ≤ min(open, close)` e `high ≥ max(open, close)`, `low ≤ high`, preços positivos; (2) **intervalos ausentes**: horários de abertura consecutivos separados exatamente por um passo do timeframe (relatar cada gap e duração); (3) **outliers**: variações entre fechamentos acima de um limite configurável (o livro sugere sinalizar >4% em dados diários; para cripto, definir por timeframe e informar contagens, pois movimentos grandes são reais); (4) candles de volume zero e timestamps duplicados; (5) frequência dos dados intradiários (candles por hora/dia versus esperado). Saída: relatório associado ao hash do conjunto; backtests informam “N gaps / M candles sinalizados” e podem recusar ou avisar.
* **Benefício:** previne dados inválidos para todas as métricas e o pipeline de evidências; contempla o dilema do livro — desenvolver com dados realistas, inclusive ruins, quando os dados ao vivo também serão ruins. Em dados de corretora, o problema principal são gaps (manutenção), não erros decimais. **Complexidade:** baixa. **Riscos:** sinalizar movimentos extremos genuínos; o relatório não pode excluir dados silenciosamente. **Validação:** fixtures com defeitos conhecidos (máxima/mínima invertidas, um intervalo ausente, fechamento com deslocamento decimal) e contagens exatas; dados limpos geram relatório vazio. Relaciona-se às propostas anteriores (livro 1, caps. 3 e 4).

### O2 — Ficha de expectativas e comparação com paper trading *(livro: C5, p. 988)*

Na criação do bot (ou promoção para paper/ao vivo), registrar o **perfil esperado** do backtest de validação: operações por mês, tempo de permanência, taxa de acerto, ganho/perda médios, drawdown máximo e maior duração de drawdown. No paper trading, mostrar real versus esperado e alertar se sair da faixa de tolerância (por exemplo, acertos ou drawdown além da faixa testada). A etapa mínima de dias no paper já existe; isso lhe dá conteúdo. Incluir a ideia de execução pessimista do livro como modo opcional de paper (**“pior preço nos próximos N segundos do sinal”** — exige dados intrabar; somente com candles, usar máxima para compras e mínima para vendas como teste de custo-limite superior). **Complexidade:** média. **Validação:** comparação determinística em reprodução de dados; sem alterar o comportamento ao vivo por padrão.

### O3 — Comparação de robustez de filtros (“evidência de desenvolvimento vertical”) *(livro: C6, p. 989)*

Ao adicionar qualquer filtro/recurso (volatilidade, regime, confirmação de tendência), exigir comparação na mesma grade de parâmetros: **porcentagem de combinações lucrativas e resultado médio com e sem o recurso**. Se o filtro ajudar em um único ponto da grade, é sobreajuste; se elevar amplamente a proporção lucrativa, é melhoria. Encaixa no relatório de robustez de varredura (cap. 21, O1) como modo de “varredura pareada”. **Complexidade:** baixa–média.

### O4 — Lista de depuração prática e definições documentadas das regras *(livro: C6, C7, pp. 989–991)*

Manter em `docs/` uma lista para resultados decepcionantes: interpretação ambígua de regras (por exemplo, “volume confirma” precisa de definição precisa, como “volume > média dos 10 candles anteriores”, registrada na documentação e nos testes); faixa de parâmetros errada; comportamento em ativos semelhantes; pressupostos sobre dados selecionados; grandes perdas ignoradas; mudança da volatilidade; evolução do mercado. Acrescentar “definição” e “exemplo de sinal” para cada parâmetro da estratégia no catálogo (`strategies/catalog.py`), para que usuários leiam a mesma regra executada pelo código. **Complexidade:** baixa (documentação e texto no catálogo).

### O5 — Consciência de choques: detecção, relatório e projeto de modo de crise *(livro: C9, C10, C11, pp. 992–1000)*

* **Detecção e relatório** (baixa complexidade; ver também cap. 14, O1, e cap. 21, O5): sinalizar candles com `range ≥ 5 × ATR(10)` e relatar posições abertas nesses momentos, P/L nos candles de choque e dependência dos resultados em relação a eles.
* **Modo de crise (somente projeto; requer aprovação):** regras predefinidas para um choque com posição aberta — (a) se gerar **lucro inesperado**, reduzir ou sair (regra 1 do livro); (b) se gerar **grande perda** (spot comprado, queda), manter o stop da corretora (que já limita a perda), **não** aumentar a posição e não reentrar até normalizar a volatilidade (não adotar a regra 3 do livro, “adicionar no pico de volume”, pois presume reservas e reversão que cripto não garante); (c) após um choque, **reinicializar indicadores de tendência** ou pausar o bot até a volatilidade cair (linhas ficam dessincronizadas), notificando a pausa.
* **Adaptação a cripto:** spot somente comprado não lucra com choque de queda; portanto, a parte assimétrica da recomendação do livro (ganho inesperado → sair) aplica-se a picos de alta. Em crashes, a defesa é tamanho da posição, stops e ficar fora do mercado (cap. 21, tempo no mercado). Stops nativos podem sofrer gap em crash: dimensionar posições considerando perda por gap (`max_candle_range_pct` existente cobre isso parcialmente). **Complexidade:** média para detecção/relato; alta para modo de crise. **Riscos:** modo de crise também é regra não testada — primeiro testar em backtest ajustado por choques. **Validação:** séries sintéticas com choques inseridos; gaps nos stops; bloquear reentrada até a condição de volatilidade ser satisfeita.

### O6 — **Não** implementar dimensionamento Martingale; permitir apenas pesquisa de anti-Martingale com limite *(livro: C12, C13, pp. 1000–1010)*

* Martingale (dobrar após perdas) arrisca ruína. O livro mostra resultados limitados bons apenas no mercado extremamente tendencial (Eurodólares), não no S&P ruidoso; o capital precisa sustentar o limite a todo momento. Em conta spot de varejo, aumentaria exposição justamente quando a conta perde; **recomendamos rejeitá-lo**, em linha com os limites de risco da plataforma.
* Anti-Martingale (adicionar a vencedoras, reiniciar após perda) é o padrão de piramidação em seguimento de tendência; versões limitadas melhoraram a razão nos Eurodólares (até 10,95), mas a versão sem limite desabou; resultado no S&P foi fraco. Se for pesquisada, tratar como experimento de dimensionamento com **limite rígido**, testar vários ativos e relatar sensibilidade (os resultados do livro dependem do ruído do mercado). **Complexidade:** média. **Não recomendado agora.** Estatísticas de sequências podem alimentar diagnósticos: O1 do cap. 15 já cobre sequências de candles de alta/baixa, e a **tabela da teoria das sequências** (número esperado de sequências de comprimento n para moeda justa) é um modelo nulo útil. **Validação, se algum dia implementado:** comparar ao modelo nulo e verificar que nenhuma aposta excede o limite.

### O7 — Regra de persistência/reversão à média no estilo Gustafson como hipótese, não recurso *(livro: C13, pp. 1010–1011)*

“Comprar após 4 fechamentos consecutivos em baixa; sair após 5 fechamentos em alta ou 8 barras” é regra explícita, simples e testável. É contrária à tendência, somente comprada, e foi proposta com base na tendência de alta das ações de 1982–2001, algo que o próprio livro salienta (“ainda no mesmo mercado de alta”). Em cripto, testá-la como **H-DOWN-RUN-BUY** pelo pipeline completo (melhor de N, sensibilidade a custos, truncamento, segmento bloqueado) e esperar forte dependência da deriva da amostra. **Complexidade:** baixa (estratégia de reversão parametrizada já proposta nos livros 1/2). Não implementar antes de existir o pipeline.

### O8 — Registro de intervenções seletivas *(livro: C14, p. 1011)*

Registrar cada intervenção manual (pausar/parar bot, kill switch, fechamento manual) com campo de motivo e exibi-la no histórico do bot, permitindo comparar a intervenção discricionária com o que o sistema faria (alerta do livro: intervenções tendem a manter posições perdedoras). **Complexidade:** baixa–média (verificar se já existe tipo de evento de auditoria: há logs de auditoria/segurança para autenticação; conferir ações por bot antes do projeto).

### O9 — Expectativas conforme o estilo (formato de retorno de tendência versus reversão à média) *(livro: C15, pp. 1012–1015)*

Exibir na documentação da estratégia e nos resultados de backtest o **formato de retorno esperado**: tendência — baixa taxa de acerto (30–40%), relação ganho/perda > 1 e longas sequências de perdas; reversão à média — alta taxa de acerto, ganho/perda < 1 e perdas grandes raras. Adicionar métrica de “sequência de perdas” (maior sequência e distribuição de perdas consecutivas) e usar probabilidades da teoria das sequências para estimar **a maior sequência de perdas esperada** dada a taxa de acerto e o número de operações, oferecendo expectativa psicológica e de capital realista. **Complexidade:** baixa. **Validação:** comparar fórmula fechada com simulação.

### Não aplicável

Compra de hardware/software, fornecedores de dados, rolagem/ajuste retroativo de futuros, limpeza de tick data de mercados viva-voz, choques históricos específicos (Gorbachev, eleição britânica, Guerra do Golfo, 11 de setembro, suco de laranja), aritmética da roleta além do uso como modelo nulo.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Validador de qualidade de candles O1 | muito alta | – | alta | baixa | – |
| 2 | Expectativas por estilo + métrica de sequências O9 | média | média | – | baixa | métricas |
| 3 | Definições de regras + checklist O4 | média | – | – | baixa | catálogo |
| 4 | Varredura pareada de filtros O3 | alta | – | – | baixa–média | cap. 21, O1 |
| 5 | Ficha de expectativas + comparação paper O2 | média | alta | alta | média | métricas |
| 6 | Relatório de choques (depois projeto de modo de crise) O5 | alta | alta | – | média → alta | helper ATR |
| 7 | Registro de intervenções O8 | – | média | média | baixa–média | projeto de auditoria |
| 8 | Hipótese de sequência de quedas O7 | baixa | – | – | baixa | pipeline |
| 9 | Martingale O6 | – | – | – | – | **rejeitado** (somente pesquisa anti-Martingale) |

## 5. Arquivos afetados

`market_data/domain/` (validador) e fluxo de importação em `market_data/application`; `backtesting/application/service.py` (relatório de qualidade dos dados); `analytics/domain/` (métrica de sequências, maior sequência esperada de perdas, varredura pareada); `strategies/catalog.py` e documentação; `trading` e `reconciler` para comparação de expectativas e alertas (Notifier); `docs/openapi.json`; telas do app; testes.

## 6. Plano incremental

1. Validador O1 com relatório por conjunto de dados; métricas O9; definições no catálogo O4.
2. Varredura pareada e relatório de choques (O3 e relato de O5).
3. Ficha de expectativas e comparação paper (O2) quando houver alertas.
4. Discutir o projeto do modo de crise com o usuário antes de qualquer código.

## 7. Critérios de aceitação e testes

* Validador informa contagens exatas para fixtures com defeitos e nenhuma para dados limpos; relatórios são determinísticos e associados ao hash dos dados; nenhum dado é alterado.
* Maior sequência de perdas esperada corresponde à simulação dentro da tolerância para taxa de acerto e número de operações fornecidos.
* Varredura pareada informa a proporção de combinações lucrativas com e sem o recurso.
* Todo comportamento novo permanece desativado ou somente leitura por padrão; ruff, mypy e testes existentes aprovados.

## Ressalvas

As regras de crise de Kaufman (adicionar no pico de volume, manter perdedoras após choque) vêm de futuros com grandes reservas e pressupõem reversões observadas em apenas quatro exemplos; quatro exemplos não constituem evidência. Testes Martingale usam somente dois mercados futuros. Os limites “4% de outlier” e “4 dias sem dados” referem-se a dados diários de futuros. As pp. 1016–1026 não foram lidas. Vários itens repetem propostas anteriores (alertas, validação de dados, detecção de choque, pipeline) e devem ser consolidados no backlog geral.
