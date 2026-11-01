# Livro 4 · Capítulo 20 — Técnicas avançadas

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 845–871 (medição e uso da volatilidade, liquidez, tendências e ruído) foram lidas integralmente. Sistemas especialistas, lógica fuzzy, fractais/entropia, redes neurais (pp. 890–894) e algoritmos genéticos (pp. 901–902), além do início da replicação de hedge funds (p. 902), foram consultados superficialmente pelos títulos e páginas indicados. Os detalhes de lógica fuzzy (876–879) e entropia (883–885) **não foram lidos**.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | A volatilidade é o segundo fator mais importante depois do preço; serve para stops, alvos, filtros, dimensionamento e construção de carteira. Ela escala aproximadamente com o nível de preço (lognormal); dois ativos com o mesmo preço podem ter volatilidades muito diferentes, o que importa ao igualar o risco das posições. Janelas de medição maiores produzem valores de volatilidade maiores, mas com taxa de crescimento decrescente. | Por que medir a volatilidade corretamente. | 845–850 |
| C2 | **Cinco medidas práticas**: (1) variação em n dias; (2) máxima máxima − mínima mínima em n dias; (3) **amplitude verdadeira média (ATR)**; (4) soma das variações diárias absolutas; (5) **desvio-padrão anualizado dos retornos** × √P. (1) depende de apenas dois pontos e é sempre menor que as medidas baseadas em máxima/mínima; (2) pode dimensionar um stop se o período de permanência for conhecido; (3) é a mais popular e “oferece uma orientação razoável para a volatilidade futura” (muitas estratégias usam `k × ATR` para stops, alvos e risco); (4) ignora gaps em relação ao fechamento anterior. A ATR é mais suave que a volatilidade anualizada e apresenta saltos menores quando há gaps; ambas são convertidas em valores monetários multiplicando pelo preço. Medidas baseadas em amplitude usam mais dados (máximas e mínimas) e são mais robustas que medidas entre fechamentos. Retornos de futuros ajustados retroativamente são distorcidos. Também são listados outros estimadores (Bookstaber entre fechamentos, máxima-mínima e máxima-mínima-fechamento). | Escolher um estimador de volatilidade. | 850–854 |
| C3 | **Volatilidade relativa** `RV = V(n)/V(m)`, com a janela maior **defasada** para terminar antes do início da menor (sem sobreposição); isso evita que a janela longa “absorva” o pico recente e também ajuda após um período volátil. | Uma razão de volatilidade mais limpa. | 855 |
| C4 | **Volatilidade implícita / VIX**: em geral, inversamente relacionada ao S&P; o ditado “compre quando estiver alta, venda quando estiver baixa” é folclore. Em períodos de estresse, volatilidade implícita e histórica podem divergir (a implícita caiu mais rápido após outubro de 2008 e voltou a subir em novembro enquanto a volatilidade realizada caía). **Sistemas baseados no VIX** (reversão 9 de Connors: 5 regras; Connors RSI(2) do VIX > 90 com S&P acima da média móvel de 200 dias; EMA(10)/SMA(10) do VIX de MarketSci; Appel: comprar com VIX alto, sem sinal de venda confiável): todos dependem de dados de opções de índices acionários. | Usar volatilidade implícita. | 855–860 |
| C5 | **Volatilidade intradiária e volume compartilham o formato de U** (maiores na abertura, menores no meio da sessão, sobem no fechamento); correlação volatilidade–volume R = 0,595 no estudo do NASDAQ 100. A tabela de Brower reúne regras do S&P para prever a amplitude de amanhã (por exemplo, ATR de 3 dias alto é “um ótimo previsor de maior volatilidade”; RSI(3) < 40 prevê maior volatilidade; inside days preveem menor volatilidade; segunda-feira é o dia de menor volatilidade e terça/sexta os de maior); On-Balance True Range. | A volatilidade também é previsível (agrupamento). | 856–858 |
| C6 | **Rompimento de volatilidade** (Bookstaber): comprar se o próximo fechamento subir mais de `k × ATR` (k ≈ 3) em relação ao fechamento atual; vender se cair mais que isso. | Rompimento dimensionado pela volatilidade. | 860–861 |
| C7 | **Alvos de lucro e stops por ATR**: `PT = entrada ± k × ATR(t−1)` (k ≈ 3, disparado pela máxima/mínima intradiária); stops usam o mesmo `k × ATR`; acionados por máxima/mínima, mas saída no fechamento para aproveitar o ruído. Alvos são para operações de **curto prazo** (mais ruído); no acompanhamento de tendência de longo prazo, **realizar lucro ou ser expulso por stop elimina a cauda longa; é preciso reentrar** enquanto a tendência persistir. | Stops e alvos adaptativos. | 861 |
| C8 | **Seleção de operações por volatilidade**: volatilidade muito alta na entrada implica risco muito alto e pior relação retorno/risco; volatilidade extremamente baixa pode indicar falta de direção e pequenas perdas frequentes; sair quando a volatilidade dispara reduz lucro e risco, mas pode ocorrer tarde. Escolher entre **eliminar** uma operação filtrada e **adiá-la** até a volatilidade ficar aceitável (acompanhar a operação ignorada; curto prazo elimina, acompanhamento de tendência adia). **Limites em desvios-padrão da volatilidade de 20 dias** (1σ filtra os 16% maiores, 2σ os 2,5%, 3σ os 0,13%; testar valores acima de 3 porque a janela curta pode excedê-lo). | Volatilidade como filtro de entrada. | 861–863 |
| C9 | **Resultados dos filtros de entrada** (tendência por média de 40 dias, futuros ajustados retroativamente entre 1990 e julho de 2011, custo de US$ 15 por operação): o filtro de baixa volatilidade (limite otimizado em passos de 0,05 entre 0,05 e 1,0) melhorou o fator de lucro nos cinco mercados — por exemplo, Eurodólares 2,11 → 2,5; petróleo bruto 1,49 → 1,67; S&P 0,83 → 1,07 (um sistema perdedor “normalmente melhora quando se removem operações”); Amazon 1,16 → 1,51. O filtro de alta volatilidade (“operar somente acima do limite”) também melhorou os resultados, mas com limites diferentes por mercado (S&P escolheu o máximo 3,0 para remover operações; petróleo bruto, 2,55). Nos Eurodólares, o filtro de baixa volatilidade teve índice de informação **1,143 contra 0,867** no filtro alto e curva de capital mais suave. | Evidências sobre entradas em baixa volatilidade. | 863–865 |
| C10 | **Saídas em alta volatilidade** (média de 40 dias; sair quando o retorno de hoje excede a volatilidade dos 20 dias anteriores × fator; não reentrar até a tendência mudar), títulos do Tesouro de 30 anos, 2000–2011: sem saídas, fator de lucro 1,02 (líquido US$ 4.500, 350 operações); saída com fator 10: 1,07 (US$ 12.968); **sair e reentrar** quando a volatilidade retornar a um quarto do movimento do dia da saída: 1,16 (US$ 34.781, 387 operações). A intenção é realizar ganhos em mercados ruidosos e, em mercados tendenciais, deixar que um bom movimento seja seguido por outros. | Redução de risco ao sair de choques, com regra de reinício. | 865–866 |
| C11 | **Resumo da seleção de operações**: filtrar “sempre elimina boas operações, mas, espera-se, remove mais das ruins”; “não se elimina o risco, apenas se adia ou redistribui”; um sistema que parece não ter risco indica falha no processo de desenvolvimento. | Realismo sobre filtros. | 866 |
| C12 | **Liquidez**: muitos sistemas com bons backtests fracassam na operação real porque o backtest presume execução nas máximas/mínimas relativas do dia, onde o volume é mínimo (Ginter e Ritchie, 1980). O lucro de um sistema de reversão à média calculado com hipótese de volume uniforme se concentra nos extremos, onde **não era possível executar**; para sistemas de tendência, “não se deve esperar lucro quando as ordens são colocadas nos extremos”. | Backtests que presumem execução sem volume. | 867–868 |
| C13 | **Tendências e ruído**: o ruído (choques de preço, muitos participantes com horizontes diferentes) tem estatísticas próximas do acaso: cerca de metade dos movimentos muda de direção no dia seguinte, ~25% continua por dois dias, 12,5% por três; o tamanho dos movimentos também se aproxima de uma distribuição geométrica (50% pequenos, 25% duas vezes maiores, 12,5% quatro vezes maiores). Não é possível distinguir um movimento isolado do ruído até que ele continue; conforme o período de cálculo da tendência aumenta, menos choques provocam uma mudança, então **tendências mais longas são mais confiáveis, porém sofrem oscilações**. À medida que os mercados amadurecem, **o ruído aumenta**; assim, os mesmos retornos exigem períodos maiores ou produzem retornos menores. A reversão à média explora o ruído em horizontes curtos (“o ruído domina no curto prazo e as tendências, no longo prazo”). Os mercados diferem em ruído (Eurodólares baixo; índices acionários altos; razão de eficiência, cap. 1). | Por que a velocidade da tendência envolve uma troca com a confiabilidade. | 868–871 |
| C14 | **Carry de taxa de juros** (rolar futuros gera carry): não é relevante aqui. | | 871 |
| C15 | **Sistemas especialistas** (base de conhecimento + mecanismo de inferência, regras se-então; encadeamento progressivo) — “não há novos sistemas de negociação publicados; qualquer sucesso é mantido em sigilo”. **Redes neurais**: entradas precisam ser escolhidas e pré-processadas (“crítico”; mais entradas tornam a solução mais lenta e menos robusta); os critérios de sucesso devem ser explícitos; funcionam melhor prevendo **indicadores técnicos deslocados para o futuro** do que a direção bruta dos preços (Ruggiero); dividir os dados em cerca de **70% treino / 20% teste / 10% validação fora da amostra**; o treinamento é tentativa e erro, “portanto os melhores resultados podem ser encontrados por acaso”; **menos camadas e neurônios geram soluções mais robustas e generalizáveis; mais permitem padrões específicos e sobreajuste**; começar de forma geral e avançar para o específico. **Algoritmos genéticos**: cromossomos de genes de regras, aptidão, propagação, cruzamento e mutação (~10% mutados; menos de 5% de alterações converge para a população inicial, mais de 25% perde os melhores); convergência quando a aptidão média para de melhorar; usar 70–80% dos dados para busca e o restante fora da amostra (“normalmente piora, mas ainda deve satisfazer critérios mínimos”); **múltiplas inicializações** (vários inícios aleatórios para evitar um pico local). **Replicação de hedge funds**: regressão dos retornos do fundo sobre fatores de mercado com o Solver. | Métodos semelhantes a aprendizado de máquina na forma apresentada em 2013. | 871–902 |

Os exemplos são de futuros e ações; as observações sobre cripto abaixo são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| ATR / volatilidade realizada | ❌ | Não é calculada em `strategies`, `analytics` nem `risk_management`. |
| Stops por volatilidade | ❌ | Existe apenas `stop_loss_pct` percentual fixo (`risk_management/domain/stops.py`). |
| Filtro de entrada por volatilidade | ❌ | `max_candle_range_pct` rejeita um sinal se o candle do sinal for amplo (limite de volatilidade de uma barra) — é a única proteção relacionada à volatilidade (`assess_signal`). É percentual fixo e não se relaciona à volatilidade recente. |
| Dimensionamento da posição por volatilidade | ❌ | O risco por operação deriva da distância do stop, que é percentual fixo (o cap. 23 abordará isso). |
| Volatilidade relativa / razão de choque | ❌ | Nenhum. |
| Verificação de liquidez (limite de volume por tamanho da ordem) | ❌ | `Candle.volume` não é usado; execuções ocorrem na abertura seguinte com slippage fixo. |
| Realismo de execução nos extremos | ✅ (parcial) | Entradas são executadas na **abertura seguinte**, não no extremo do candle do sinal; stops executam no preço do stop ou na abertura em caso de gap (regra para gap além da abertura). Isso evita o erro de “executar no extremo” de C12. |
| Busca por aprendizado de máquina / algoritmo genético | ❌ | `sweeps` são buscas em grade (`MAX_SWEEP_RUNS`) sem correção. |
| Separação fora da amostra | ✅ (parcial) | Uma divisão cronológica treino/teste (`segments.py`); não há terceiro segmento bloqueado (cap. 3, O5). |

## 3. Oportunidades

### O1 — Ferramentas compartilhadas de volatilidade: true range, ATR, σ entre fechamentos e medidas por amplitude *(livro: C2, pp. 850–854)*

Implementar true range, ATR (Wilder ou simples, com documentação), desvio-padrão móvel dos retornos logarítmicos (com anualização de 365 dias do cap. 3, O1 do livro 1) e medida de amplitude máxima-mínima em um módulo helper usado por diagnósticos, estratégias, risco e dimensionamento. Orientação do livro: preferir medidas baseadas na amplitude (usam máximas e mínimas); ATR para stops; σ anualizado para relatórios de risco e comparações. **Complexidade:** baixa (compartilhada com O1 do cap. 18). **Validação:** fixtures calculadas manualmente, invariância de escala e tratamento de gaps (true range inclui o fechamento anterior).

### O2 — Distância de stop baseada em ATR (e alvo opcional) como alternativa ao percentual fixo *(livro: C7, p. 861)*

* **Proposta:** modo de stop `atr`, com `stop = entrada − k × ATR(n)` calculado na entrada a partir de candles fechados (o livro sugere k ≈ 3). Manter o modo percentual como padrão. Opcionalmente, `alvo = entrada + k_t × ATR` apenas para estratégias de horizonte curto, já que o livro restringe alvos a operações de curto prazo.
* **Motivo:** um stop fixo de 2% é apertado demais em fases voláteis e amplo demais em fases tranquilas; o stop por ATR adapta a distância de risco, e a fórmula de tamanho da posição (risco por operação ÷ distância do stop) dimensiona automaticamente as posições conforme a volatilidade.
* **Ressalvas do livro:** em acompanhamento de tendência de longo prazo, stops e alvos custam a cauda longa; é necessária lógica de **reentrada** ou o lucro da tendência se perde (ver ablação O7 do cap. 8). Stops nativos de corretora exigem que o nível seja fixado na entrada (um stop ATR móvel exige substituição da ordem; ver O2 do cap. 19).
* **Complexidade:** média (`StopMode` na configuração de risco, backtester e trader, campos de formulário e testes). **Riscos:** mais parâmetros; ATR do candle de entrada pode estar inflada por um candle de rompimento. **Validação:** ablação (percentual versus ATR) pelo pipeline; paridade entre backtest e paper; stop calculado determinístico e registrado em log.

### O3 — Filtro de entrada por volatilidade, com modos “adiar” e “eliminar” *(livro: C8, C9, pp. 861–865)*

* **Proposta:** filtro de configuração de risco que suprime (ou adia) uma entrada quando a **volatilidade de 20 barras** estiver acima/abaixo de limites expressos em desvios-padrão de seu próprio histórico (método probabilístico do livro). Duas políticas: **eliminar** (ignorar o sinal) e **adiar** (manter a entrada pendente até a volatilidade voltar à faixa aceitável, exigindo ainda que a condição de tendência continue válida).
* **Evidência no livro:** o filtro de baixa volatilidade melhorou todos os cinco mercados testados, e o índice de informação e a suavidade melhoraram nos Eurodólares. **Porém:** (a) os limites foram otimizados por mercado (0,05–1,0 em passos de 0,05), logo a melhoria é dentro da amostra; (b) o livro relata limites inconsistentes para o filtro de alta volatilidade; (c) o resultado do S&P mostra que filtrar um sistema perdedor o “melhora” sem torná-lo bom; (d) os mercados eram futuros ajustados retroativamente, 1990–2011, com custo de US$ 15.
* **Observação sobre cripto (nossa):** essa relação não é garantida; tendências cripto muitas vezes começam em **compressões de baixa volatilidade** (rompimentos), então “entrar apenas quando a volatilidade é baixa” pode cancelar rompimentos bons, enquanto “entrar apenas com volatilidade alta” pode levar a persegui-los. Tratar como **H-VOL-FILTER**, testar as duas direções e a sensibilidade a custos pelo pipeline de evidências (cap. 3 do livro: melhor de N e segmento bloqueado).
* **Complexidade:** média (estado de entrada pendente no motor e no trader). **Validação:** teste de truncamento; entradas adiadas usam apenas dados até o candle de entrada; contabilizar sinais eliminados/adiados.

### O4 — Saída por choque com reinício de reentrada (experimento) *(livro: C10, pp. 865–866)*

Sair quando o retorno da barra exceder `f ×` a volatilidade das 20 barras anteriores; reentrar na mesma tendência somente quando a volatilidade barra a barra cair para um quarto do movimento da barra de saída. A melhora do livro (fator de lucro 1,02 → 1,16) foi em um único mercado (títulos de 30 anos, 2000–2011), com fator 10 escolhido pelo autor; portanto, a evidência é fraca. Para cripto spot comprado, interessa apenas o **choque de queda** (candle vermelho extremo durante a posição). Combinar com a detecção O1 do cap. 14 e limites de risco de gap. **Complexidade:** média. **H-SHOCK-EXIT.** **Riscos:** a saída acontece depois do dano (como reconhece o livro); lógica de reentrada complexa; stops já protegem contra risco de gap na corretora.

### O5 — Realismo de execução: limite de volume e proteção contra execução no extremo *(livro: C12, pp. 867–868)*

* **Proposta:** (a) limite opcional de volume: rejeitar ou reduzir execuções simuladas cuja quantidade exceda uma fração (por exemplo, 1–5%) do volume negociado no candle e informar a contagem; (b) teste de regressão/auditoria para assegurar que execuções do backtest nunca ocorram na máxima ou mínima do candle do sinal (o motor atual executa na abertura seguinte; isso previne regressões caso sejam adicionadas ordens limitadas ou execuções intrabar).
* **Benefício:** contas pequenas raramente atingem esse limite, mas o usuário pode escalar `capital`; a advertência de Ginter–Ritchie será relevante se ordens limitadas e execuções intrabar forem adicionadas (O2 do cap. 5, livro 2, cap. 7). **Complexidade:** baixa. **Validação:** uma execução acima do limite é reduzida/rejeitada de modo determinístico; comportamento padrão inalterado.

### O6 — Agrupamento de volatilidade como expectativa documentada e teste *(livro: C5, pp. 856–858)*

As regras de Brower (ATR de 3 dias alta prevê volatilidade maior; inside days preveem menor volatilidade) reafirmam o **agrupamento de volatilidade**: a volatilidade é muito mais previsível que a direção. Adicionar aos diagnósticos da série medidas como “autocorrelação dos retornos absolutos” e “a ATR das últimas 3 barras prevê a amplitude da próxima barra?”, para confirmar que stops/filtros por ATR usam uma variável previsível. **Complexidade:** baixa. Os números por dia da semana (segunda menor, terça/sexta maiores) são do S&P entre 1987–95 e não devem ser presumidos para cripto, que negocia 7 dias por semana.

### O7 — Regra de projeto de tendência que considera o ruído *(livro: C13, pp. 868–871)*

Documentar e exibir na interface a troca descrita pelo livro: regras de tendência mais rápidas reagem a mais ruído (mais operações e maior impacto de taxas); regras mais lentas são mais confiáveis, mas atrasam. Conforme o ruído aumenta, a mesma estratégia gera retornos menores (nossa adaptação: o ruído cripto também muda entre regimes; um parâmetro que funcionou em regime muito tendencial pode piorar). Entrega concreta: mostrar a razão de eficiência (cap. 1, O1 do livro 4) ao lado de cada resultado de varredura, para visualizar **ruído versus período** antes de escolher um parâmetro. **Complexidade:** baixa.

### O8 — Disciplina para busca com ML/genética (apenas orientação, sem implementação) *(livro: C15, pp. 890–902)*

Se as ferramentas de otimização forem além da busca em grade: (1) manter a busca separada dos dados fora da amostra; (2) as divisões do próprio livro (70/20/10 para redes neurais; 70–80% para busca genética e o restante fora da amostra) são um **mínimo**, e o segmento final de 10% bloqueado deve ser usado uma única vez; (3) **múltiplas inicializações**: repetir a busca com vários pontos iniciais aleatórios e comparar soluções para detectar picos locais; (4) preferir menos parâmetros (“menos camadas e neurônios produzem soluções mais robustas e gerais”); (5) tratar o resultado de uma busca como hipótese, pois “o melhor resultado pode ter sido encontrado por acaso”. Essas práticas correspondem ao pipeline já proposto (melhor de N, permutação, validação bloqueada) e aos métodos de validação cruzada do livro 5; não há implementação a fazer agora. **Complexidade:** nenhuma.

### Não aplicável

Sistemas de VIX (não há neste escopo índice equivalente de volatilidade implícita com instrumento negociável; há índices derivados de opções para BTC, mas estão fora dos dados disponíveis), carry de taxa de juros, lógica fuzzy (não lida), sistemas especialistas, entropia (não lida), replicação de hedge funds, procedimentos do Excel Solver e negociação intradiária de gamma/theta de opções.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Ferramentas de volatilidade O1 | média | alta | – | baixa | – |
| 2 | Ruído junto aos resultados de varredura O7 | média | – | – | baixa | helper ER (caps. 1/17) |
| 3 | Diagnóstico de agrupamento de volatilidade O6 | baixa | média | – | baixa | O1 |
| 4 | Modo de stop ATR O2 | – | alta | média | média | O1; projeto de stop ao vivo |
| 5 | Limite de volume e proteção contra execução no extremo O5 | média | média | – | baixa | – |
| 6 | Filtro de entrada por volatilidade O3 | média | média | – | média | O1; pipeline |
| 7 | Saída por choque e reentrada O4 | baixa | média | – | média | O1; O1 do cap. 14 |
| 8 | Disciplina de busca O8 | – | – | – | nenhuma | livro 5 |

## 5. Arquivos afetados

`strategies/domain/` ou um novo helper compartilhado `indicators` (verificar a convenção de nomes existente; não criar `__init__.py` vazio), `risk_management/domain/` (modo de stop, configuração de filtros, dimensionamento a partir do stop), `backtesting/domain/engine.py` (entradas pendentes, limite de execução), `trading/application/trader.py` e `execution` (stop na entrada), `analytics` (diagnósticos), `docs/openapi.json`, formulários e gráficos do app, testes.

## 6. Plano incremental

1. Ferramentas O1 e diagnósticos (O6, O7) — somente leitura, sem mudar o comportamento.
2. Proteção O5 (desativada por padrão).
3. Stop ATR O2 no backtest e paper, com ablação percentual versus ATR; operação ao vivo somente após comprovar paridade.
4. Experimentos O3/O4 pelo pipeline com variantes explícitas de eliminar/adiar.

## 7. Critérios de aceitação e testes

* ATR, true range e σ correspondem a fixtures calculadas manualmente, inclusive com gaps; são invariantes à escala e reproduzíveis.
* O modo de stop `atr` é determinístico e registrado em log; o modo percentual não muda; o dimensionamento varia de forma coerente com a distância do stop.
* O filtro de volatilidade nunca usa dados posteriores ao candle da decisão (teste de truncamento); informar contagens de entradas eliminadas/adiadas.
* Limite de execução: execuções grandes demais são reduzidas/rejeitadas com motivo contabilizado; desativado por padrão, reproduz os resultados atuais bit a bit.
* ruff, mypy e todos os testes existentes aprovados.

## Ressalvas

Todas as tabelas de desempenho (20.2, 20.3) vêm de futuros ajustados retroativamente e uma ação, foram otimizadas dentro da amostra e usam custos pequenos fixos; o resultado da saída por alta volatilidade depende de um mercado. O autor não aplica correções para testes múltiplos. Os exemplos do VIX e a ideia de “comprar quando o VIX está alto” referem-se a índices acionários e volatilidade implícita. As seções sobre lógica fuzzy, entropia e os capítulos completos de redes neurais/algoritmos genéticos não foram lidos integralmente; portanto, não se fazem afirmações sobre eles além das páginas citadas.
