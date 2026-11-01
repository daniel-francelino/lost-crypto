# Livro 4 · Capítulo 21 — Teste de sistemas

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 905–954 e 970–976 foram lidas integralmente. A comparação ampliada de cinco estratégias de tendência entre mercados (pp. 954–969; comparação de Colby, “Comparing the Five Strategies”, tabelas de consistência por mercado) foi consultada superficialmente pelos títulos. A lista de robustez final (pp. 977–982) **não foi lida** além do primeiro item. As afirmações abaixo se limitam às páginas lidas.

Este é o capítulo mais relevante do livro para os módulos de backtest e varredura da plataforma; há forte sobreposição com o livro 3 (Aronson) e livros 1/2 (Chan).

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Testar é uma disputa entre capacidade computacional e bom senso.** Ferramentas melhores não significam resultados melhores. **Otimização é a técnica mais mal utilizada**: “os melhores resultados de teste nunca correspondem às expectativas e muitas vezes viram uma tragédia financeira quando negociados”; quem testa em computador acaba cometendo sobreajuste. | Sobreajuste por busca. | 905–906 |
| C2 | **Expectativas primeiro**: definir ideia, horizonte, risco relativo e porcentagem esperada de acertos **antes** de testar; caso contrário, não se distingue boa ideia de sobreajuste. **“O teste deve ajudar a decidir entre relações de risco e recompensa, não descobrir estratégias.”** Definir o **objetivo** (somente lucro gera um ou dois grandes vencedores e muitas pequenas perdas: ouro caiu por 20 anos e depois disparou; mercado de alta dos anos 1990 pode esconder perdas posteriores); o setor prefere Sharpe/índice de informação; considerar também drawdown máximo e lucro por operação (custos). | Objetivo e plano antes da busca. | 907–908 |
| C3 | **Parâmetros e faixas**: exemplos — período, constante de suavização, largura de banda, período RSI, stop, permanência máxima. Otimizações de 1, 2 e n parâmetros; 250×30×30 = 225 mil testes; a 0,01 s cada, ~36 min. “Limitar o teste força uma decisão antecipada sobre faixas razoáveis; sem limites, o teste se aproxima de exploração indiscriminada.” | Dimensão combinatória e faixas pré-definidas. | 908–909 |
| C4 | **Distribuição dos valores testados**: não espaçar períodos uniformemente; diferença entre 49 e 50 dias é 2%, mas entre 2 e 3 é 50%. Usar todos os valores pequenos e menos valores grandes, ou **incrementos percentuais (multiplicar por 1,5 a cada etapa)**, reduzindo o tempo de teste e melhorando a distribuição dos resultados. | Passos iguais dão peso excessivo ao extremo longo. | 909 |
| C5 | **Ordem dos testes**: testar primeiro o componente mais importante (período da tendência), depois o indicador de timing e então stop-loss; “é irreal pensar que o tamanho do stop-loss deveria comandar uma estratégia”. **Tipos de variáveis**: contínuas, discretas e **codificadas (regra/regime)**; análise de padrões e médias só fazem sentido para variáveis contínuas/discretas, não codificadas (uma MA versus duas MAs versus regressão). | Ordem de busca interpretável. | 909–910 |
| C6 | **Dados**: séries contínuas de futuros (vencimento mais próximo, ajustadas retroativamente, indexadas, n dias constantes); dados ajustados retroativamente invalidam regras percentuais e podem ficar negativos; a melhor série é a realmente negociada; manter outra série sem ajuste para máximas/mínimas reais. **Dados sintéticos**: embaralhar blocos foi abandonado por separar uma alta de sua queda inevitável; séries aleatórias parecem preços em períodos laterais, mas não têm tendências reais, sazonalidade ou volatilidade variável; propõe-se dado sintético baseado em modelo (regressão kernel de Wolberg, “Fraction Same Sign”); estratégia encontrada em dado sintético pode explorar o gerador. | Dados reais e sintéticos. | 910–916 |
| C7 | **Integridade dos testes**: cerca de **50%** dentro da amostra e restante fora (primeira metade, última metade, blocos alternados ou **blocos aleatórios alternados fixados no início**, com duração aleatória, por exemplo 2–8 anos); em blocos alternados, avaliar **retornos diários, não lucro total**. “Dados dentro da amostra podem ser torturados sem misericórdia; fora da amostra é usado **uma vez**.” Resultado fora costuma ser ~50% do retorno dentro; queda do índice de informação de 2,0 → 1,0 é “razoavelmente boa”. Ajustar sistema após ver os dados fora da amostra é **feedback** (“sempre sobreajuste”). | Disciplina de holdout. | 916–917 |
| C8 | **Teste step-forward (walk-forward)**: escolher parâmetros numa janela (exemplo: 2 anos), aplicar aos 6 meses seguintes, avançar 6 meses e acumular somente resultados fora da amostra. **Viés de curto prazo**: janelas curtas favorecem sistemas rápidos; sinal de problema: ótimo salta entre períodos curtos e longos em janelas sucessivas (10, 50, 15…); correção: janelas mais longas (5 anos). Novamente há feedback: execuções repetidas consomem os dados fora da amostra, então é necessário um conjunto final intocado. | Projeto e vieses do walk-forward. | 918–919 |
| C9 | **Buscar o melhor resultado**: melhor é o conjunto de parâmetros **mais robusto**, não o máximo. Otimização **sequencial** (um parâmetro por vez) reduz testes de n1×n2×n3 para n1+n2+n3, mas pode perder o pico (exemplo de mapa 2D encontra 300 em vez de 400); corrigir com **inicializações aleatórias** (varrer linha/coluna desde inícios aleatórios; mesma resposta em várias sementes sugere que o pico foi encontrado); descida mais íngreme para superfícies contínuas; otimização automática só faz sentido para resultados contínuos. | Busca eficiente sem se enganar. | 919–922 |
| C10 | **Visualização**: examinar gráfico de preços (erros de dados) e **mapa de parâmetros**. Padrões 1D: platô lucrativo amplo (bom); dois platôs (rápido versus lento; preferir lento por custos/erros); pico estreito cercado de perdas (provável choque passageiro; lucro alto sem custos também é suspeito). Usar tabelas 2D, superfícies e dispersão por parâmetro. **Padrões erráticos indicam sistema não confiável ou erro no teste**; stop importa menos que período da tendência; “se as médias são iguais, o menor desvio-padrão do fator de lucro indica maior estabilidade”. | Ver robustez, não somente o máximo. | 922–929 |
| C11 | **Padronizar resultados** para comparar sistemas: anualizar, ajustar ao risco (lucro/risco ≈ índice de informação) e **ao erro-padrão** (duas operações e 50 operações com 50% de acerto não têm a mesma confiabilidade). **Média dos vizinhos** (média de 9 células do mapa; bordas com 6 e 4) suaviza picos. | Comparabilidade. | 930–932 |
| C12 | **Busca em larga escala**: 8 parâmetros podem gerar **2.332.800.000** combinações (mais de 7 anos a 10 testes/s). Receita de **algoritmo genético**: populações de 1.000–5.000 strings; propagação; cruzamento (10–15%); mutação (célula em 10% das strings); parar na convergência; **repetir até 5 vezes com sementes diferentes**; guardar as **20 melhores strings** — agrupamento indica robustez, divergência põe integridade em dúvida. **Amostragem Monte Carlo** de parâmetros (1.000 strings aleatórias; conferir frequência aproximadamente igual de cada valor; repetir várias vezes); diferentemente do algoritmo genético, também mostra a **profundidade** do sucesso necessária para avaliar robustez e evita visar valores já conhecidos como bons. | Busca em grades grandes sem perder informação de robustez. | 932–936 |
| C13 | **Refinar regras**: uma regra nova que transforma apenas uma perda específica em lucro eleva o pico, mas torna vizinhos em perdas maiores; **curtose muito alta** da distribuição desempenho-parâmetros sinaliza sobreajuste; mudança boa melhora todos os casos (“ajuste de regra que afeta um ou dois casos dificilmente funcionará no futuro”). | Remendos de regras como sobreajuste. | 937–938 |
| C14 | **Resultados válidos**: “aceitamos resultados bons, mas procuramos erros quando são ruins — verificar tudo cuidadosamente”. Estratégia ajustada a um evento único (crash de 1987) não é geral; longa alta distorce parâmetros. **Omissões**: sem choque no histórico não se sabe se o sistema sobreviveria; dados inclinados para um lado (ações nos anos 1990, títulos desde os anos 1990) geram estratégia enviesada. | Reconhecer vieses. | 938–939 |
| C15 | **Critérios de robustez**: (1) **premissa sólida** (cada regra explora fenômeno real); (2) **adaptação** a mudanças (stops ajustados por volatilidade, tamanho pelo risco, sem níveis/dólares fixos); (3) **teste apropriado** (maior parte dos dados, dentro/fora da amostra ou paper trading até haver operações suficientes). Futures Truth constatou que melhores sistemas têm **quatro ou menos variáveis**. “Sistema robusto tem desempenho consistente com o mínimo de parâmetros testado em mais dados.” | Como reconhecer robustez. | 939–940 |
| C16 | **Referências de comparação** (retorno de 20% versus média de 25%); referências publicadas têm **viés de sobrevivência** e retornos assimétricos (−50% e depois +50% = −25%). **Fixar a faixa de cada parâmetro antes de testar** (RSI 3–10, não 3–50; se RSI de 45 dias vencer, o conceito provavelmente está sobreajustado). | Comparação honesta. | 940–941 |
| C17 | **Dez critérios de desempenho**: fator de lucro/razão de retorno; lucro líquido; **número de operações** (poucas não são confiáveis); **porcentagem lucrativa** (30–40% normal em tendência; >60% costuma indicar pequenos lucros recorrentes); **retorno líquido médio por operação** versus custos (média de US$ 50 por operação em moeda é consumida por ~US$ 100 de slippage); **drawdown máximo** (errático, não representa o maior futuro; drawdown surpreendentemente pequeno indica sobreajuste ou teste curto; preferir **média dos drawdowns máximos entre testes**; capital típico é 3× esse valor); retorno anualizado; **tempo de recuperação**; **tempo no mercado** (com mesmo desempenho, menor exposição a choques é melhor); **inclinação de retornos periódicos** (queda indica deterioração). Slippage citado é específico a futuros. | O que relatar. | 941–942 |
| C18 | **Avaliar pela média, não pelo melhor**: esperar a **média de todos os testes**; `retorno ajustado = média de todos os testes − 1 desvio-padrão dos retornos` (84% de probabilidade de alcançá-lo sob normalidade). **Rever outliers**: resultado não deve depender de um movimento grande, especialmente choque (50% de chance de o mesmo lucro ser perda); estudar maiores ganhos/perdas; “vários grandes lucros e nenhuma grande perda indicam sobreajuste”. | Expectativa realista. | 943 |
| C19 | **Teste de sensibilidade**: deslocar parâmetros, individual e conjuntamente, em pequenas quantidades; desempenho deve ser moderadamente sensível. Se todos os vizinhos são piores, a escolha é **solução de pico (sobreajustada)**. **Espaço n-dimensional**: agrupar testes por distância ao centro em camadas concêntricas e observar a queda do desempenho médio por camada. | Estabilidade local. | 943–944 |
| C20 | **Disciplina de evidência**: não aceitar “prova” por exemplos escolhidos; a “significância do significativo” depende do total de tentativas em **todas** as estratégias, não só na atual. 70% de testes lucrativos é regra prática de robustez apenas antes de estreitar a faixa. **Checagem entre mercados**: sistema lucrativo no S&P, mas não no NASDAQ, provavelmente está sobreajustado; mercados relacionados são dados fora da amostra. Sistemas anunciados em um só mercado são “bons demais para ser verdade”. | Testes múltiplos e replicação. | 944–945 |
| C21 | **Exemplo comparativo** (NASDAQ 100, 1997–2003, US$ 125 por operação): média móvel versus inclinação da regressão, períodos 10–250 em passos de 10. A maioria dos testes é lucrativa (confirma a premissa); número de operações cai ordenadamente e estabiliza perto de 8; fator de lucro de operações encerradas salta de modo enganoso; usar índice de informação de retornos diários. Sistema mais robusto tem maior **média** do índice numa faixa razoável (2,62 versus 2,30). | Aplicar critérios para comparar sistemas. | 946–949 |
| C22 | **Custos**: média móvel NASDAQ 1991–2011, custo zero, US$ 50, 100 e 150 por ida e volta: faixa lucrativa se estreita de períodos acima de 15 dias para aproximadamente 45–75 conforme o custo sobe; “custos excessivos tornam tudo perdedor; custos realistas são necessários”. | Sensibilidade a custos. | 949 |
| C23 | **Piores resultados também informam**: lucro de choque em um parâmetro não é razão para escolhê-lo. Uma região persistentemente perdedora (períodos 1–11 no NASDAQ, devido a ruído) pode virar **contratendência rápida dentro de uma tendência lenta lucrativa**: comprar quando média lenta sobe e rápida vira para baixo; vender quando lenta cai e rápida vira para cima; sair quando lenta virar. Lucro líquido 64.385 → 53.380; fator de lucro 1,51 → 2,26; operações 212 → 72; acertos 35 → 47% (um só mercado). | Usar a região perdedora. | 950–951 |
| C24 | **Reteste**: após desenvolvimento, um teste final com todos os dados; parâmetros deveriam mudar pouco; retestar após **5–10% de dados novos**. Grande mudança indica volatilidade incomum ou dados originais curtos; **após choque, não criar regras para corrigi-lo**. **O modelo está quebrado?** Comparar tamanho/duração dos drawdowns ao vivo com perfil testado; perdas persistentes até o antigo drawdown máximo sinalizam problema. Probabilidade de drawdown ≥ P sob retornos normais: `Prob = (1 − P)^(2μ/σ²)` (exemplo: retorno anual de 30%, μ/σ = 0,09 diário; expoente 23,51; confiança de 95% → drawdown de 12% esperado em ~5% dos meses); pressupõe normalidade, portanto caudas pesadas tornam a estimativa otimista. | Deriva de parâmetros e monitoramento ao vivo. | 951–953 |
| C25 | **Teste em muitos mercados**: mesmas regras em vários mercados são base da robustez; “calças folgadas servem em todos” (Tropin) — esperar resultados subótimos, mas consistentes. | Consistência entre ativos. | 954 |
| C26 | **Choques de preço**: evento não antecipado; como costuma contrariar posições lotadas, “a menos que você seja contrarian, choque tende mais a causar perda do que lucro”. Testes históricos sempre incluem choques que o otimizador pode ter aproveitado; com 10 choques em 20 anos, lucrar em 8 implica que ao menos ~3 deveriam ter sido perdas; risco artificialmente baixo “permite alavancagem excessiva”. Teste: remover P/L de movimentos de 1 dia com amplitude acima de **5× ATR dos 10 dias anteriores** — desempenho de tendência cai de forma consistente (S&P 1991–2009, fig. 21.21); calcular média dos testes vizinhos, mas **usar o maior drawdown**. Listar choques (amplitude ≥ 3,5× média recente, confirmar nos gráficos), contar ganhos e perdas (mais de 50% de ganhos significa que lucro e risco estão errados); **inverter** o lucro médio de 1 dia para perda equivalente nesses dias; ganhos/perdas devem ter tamanhos comparáveis entre magnitudes de choque. | Backtests ajustados por choques. | 970–972 |
| C27 | **Anatomia de uma otimização** (petróleo, 1990–91): melhor média móvel usando dados anteriores a cada choque mantinha posição errada no dia (vendida antes da invasão; comprada antes do ataque dos EUA); melhor parâmetro com ambos os choques fica entre duas perdas (instável) e a maior parte do lucro veio dos choques (sem choques: US$ 3.225 e 2.495, contra US$ 16.565–28.335 incluindo-os); escolha razoável seria perto de 60 dias, com lucro muito menor. | Exemplo real de parâmetros ajustados a choques. | 972–975 |
| C28 | **Síntese da robustez**: após sucesso dentro e fora da amostra, retestar com todos os dados e começar pequeno; robustez = bom resultado em muitos parâmetros, mercados e anos; julgar por **médias** (lucro líquido, operações, drawdown, lucro/operação) e desvio-padrão, não pelo melhor. Primeiro item da lista: validar ideia existente com premissa sólida (padrão de comportamento humano ou processo econômico/fundamental). | Definição final. | 976 |

As observações sobre cripto abaixo são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Expectativas/tese predefinidas | ❌ | Bots/backtests sem metadados de hipótese (planejado no livro 3). |
| Faixas de parâmetros predefinidas | ⚠️ | Varredura exige listas/faixas explícitas na solicitação; nada as fixa antes de ver resultados; `MAX_SWEEP_RUNS` só limita o tamanho. |
| Grades uniformes versus geométricas | ❌ | Grades são fornecidas pelo usuário; sem helper logarítmico/geométrico (livro 4, cap. 7 O1 e cap. 17 O3). |
| Parâmetros categóricos/codificados versus numéricos | ❌ | `strategy_type` é separado, mas varreduras de espaços mistos não são diferenciadas. |
| Dentro/fora da amostra | ⚠️ | Uma divisão cronológica (`segments.py`); reavalia-se repetidamente nos mesmos dados; não há terceiro segmento bloqueado. |
| Blocos aleatórios alternados | ❌ | Nenhum. |
| Step-forward (walk-forward) | ❌ | B-WALK-FORWARD já proposto. |
| Detecção de viés de curto prazo (ótimo salta entre janelas) | ❌ | N/A até existir walk-forward. |
| Visualização de mapa de parâmetros | ⚠️ | Varreduras retornam lista; app mostra tabela/classificação (verificar); sem mapa de calor 2D ou média de vizinhos. |
| Sensibilidade da vizinhança | ❌ | Não calculada. |
| Agregados da varredura (média, desvio-padrão) | ❌ | Classificação por métrica apenas; sem “média de todos os testes − 1σ”. |
| Número de operações e taxa de acerto | ✅ | Em `Metrics`. |
| Tempo de recuperação, tempo no mercado, inclinação dos retornos | ❌ | Não em `Metrics` (cap. 2, O1/O2). |
| Média dos drawdowns máximos | ❌ | Não calculada. |
| Curva de sensibilidade a custos | ⚠️ | Uma `fee_rate` e `slippage_bps` por execução; varrer custos só se parâmetro de varredura (verificar); sem relatório-padrão de escada de custos. |
| Choques de preço no backtest | ❌ | Sem lista de choques ou métricas ajustadas. |
| Consistência entre mercados | ❌ | Um ativo por execução; bot negocia um ativo; relatório não agrega vários ativos. |
| Revisão de outliers/maiores operações | ❌ | Lista operações, mas não lucro sem as N maiores. |
| Contagem de testes múltiplos | ❌ | Sem total de execuções por família de estratégia. |
| Reteste em dados novos/deriva do ótimo | ❌ | Sem histórico dos melhores parâmetros. |
| Monitor de modelo quebrado (drawdown ao vivo vs perfil testado) | ❌ | Sem comparação de tamanho/duração do drawdown ao vivo com distribuição do backtest. |
| Reprodutibilidade | ✅ | Semente e hash SHA-256 dos candles são armazenados. |
| Ferramentas de busca (genética/amostragem Monte Carlo) | ❌ | Somente grade. |

## 3. Oportunidades

As oportunidades estão agrupadas; o primeiro grupo tem baixo custo e alto valor.

### O1 — Relatório de robustez da varredura: agregados, vizinhança e platô *(livro: C10, C11, C18, C19, C28, pp. 922–932, 943–944, 976)*

* **Proposta:** além da classificação, calcular por varredura: média, mediana, desvio-padrão, porcentagem de execuções lucrativas (retorno líquido e retorno após custos), **retorno ajustado = média − 1σ**, **média da vizinhança** de cada execução (média de 9 células em 2D, versões de borda; média dos dois vizinhos em 1D), **sensibilidade** da execução escolhida (queda da média dos vizinhos), drawdown máximo médio e o **maior** drawdown máximo entre vizinhos, além do alerta **“solução de pico”** se todos os vizinhos forem piores. Mostrar curva 1D ou mapa de calor 2D e alertar para mapas erráticos (o livro: errático significa não confiável ou teste com erro).
* **Benefício:** trocar “escolher o máximo” por “escolher o platô estável”, mensagem central do livro e alinhada ao melhor de N do livro 3 e sensibilidade de parâmetros de Chan. **Complexidade:** baixa–média (analytics + endpoint + tela). **Riscos:** exige grade regular; varreduras aleatórias/irregulares precisam de outra definição de vizinhança (raio no espaço n-dimensional, C19); não apresentar retorno ajustado como probabilidade se retornos não forem normais. **Validação:** mapas sintéticos com platô e pico conhecidos; pico sinalizado; médias de vizinhos iguais ao cálculo manual em bordas e cantos.

### O2 — Faixas predefinidas, grades geométricas e registro de varreduras *(livro: C3, C4, C16, C20, pp. 908–909, 941, 945)*

Criar helper de grades **geométricas/percentuais** (×1,5 ou espaçamento logarítmico), padrão para parâmetros de período; guardar **especificação da varredura** (estratégia, faixas, espaçamento, datas, ativo e custos) definida *antes* da execução e imutável após haver resultados; **registro de execuções totais por família de estratégias e ativo/faixa temporal**, para conhecer o número de tentativas (o livro: considerar o total acumulado de testes entre estratégias). Mostrar “N testes até agora” junto a qualquer melhor resultado e alimentar métodos melhor de N/deflação (livros 3 e 5). **Complexidade:** baixa–média. **Riscos:** registro pode ser contornado criando nomes novos; documentar como apoio à honestidade. **Validação:** faixas imutáveis após primeiro resultado; contadores aumentam pelo número de execuções.

### O3 — Segmento final bloqueado e regras de blocos cronológicos *(livro: C7, C8, pp. 916–919)*

Ampliar divisão para **treino / validação / bloqueado** (o livro também usa 70/20/10 em aprendizado de máquina); avaliar segmento bloqueado no máximo uma vez por família de configuração e registrar consumo pela API (“sem segunda chance”, feedback). Quando blocos não forem contíguos, avaliar **retornos diários (por candle)**, não lucro total. Blocos aleatórios alternados, fixados no início do desenvolvimento e por sistema (sistemas diferentes não compartilham holdout), são variante avançada, prioridade baixa. Igual ao cap. 6, O5 do livro 3. **Complexidade:** média. **Validação:** segunda consulta ao segmento é registrada e exibida; fluxos existentes mantêm métricas.

### O4 — Análise step-forward (walk-forward) com diagnóstico de viés de curto prazo *(livro: C8, pp. 918–919)*

Deslocar janelas (por exemplo, 2 anos dentro da amostra, 6 meses fora) para escolher parâmetros dentro da amostra e acumular somente operações fora; relatar **deriva de parâmetros** entre janelas (sinal de janelas curtas: ótimo salta 10, 50, 15) e curva de patrimônio encadeada fora da amostra. Observação nossa sobre cripto: históricos são curtos (spot Binance desde 2017 para BTC; posteriores para outros), então janela de 2 anos gera poucas janelas; usar 4h/1d com cuidado e esperar ampla incerteza. **Complexidade:** alta (cada janela executa varredura; reutilizar motor e manter `MAX_SWEEP_RUNS` por janela). **Validação:** segmentos fora da amostra concatenados nunca se sobrepõem às janelas de treino; determinístico com mesma semente.

### O5 — Relatório de backtest ajustado por choques *(livro: C26, C27, pp. 970–975)*

* **Proposta:** (a) detectar “candles de choque” por `range ≥ k × ATR(10)` (livro usa 5× para remover e 3,5× para listar); (b) informar resultado líquido **sem** P/L dos candles de choque e também **invertendo o sinal do P/L médio dos dias de choque** em que a estratégia lucrou; (c) contar ganhos e perdas em dias de choque e seus tamanhos; (d) sinalizar execuções com mais de 50% de choques lucrativos (“lucro e risco estão ambos errados”); (e) em varreduras, colunas “lucro sem choques” e “número de dias de choque em posição”; usar o **maior drawdown da vizinhança**, não o da melhor execução, para risco (C26).
* **Motivo:** cripto tem choques frequentes (cascatas de liquidação, eventos em corretoras). Bot spot comprado lucra em choque de alta e sofre na queda; otimizador pode escolher parâmetro que estava sem posição ou vendido antes de um crash.
* **Complexidade:** média (atribuição de P/L por candle no motor; exige patrimônio por candle). **Riscos:** atribuição com posição mantida por vários dias; heurística de inversão do livro presume simetria, falsa para spot comprado (choques têm ambos os sinais, exposição só de um lado); declarar pressuposto. **Validação:** série sintética com choque inserido; atribuições somam ao P/L total.

### O6 — Escada de custos e custo de equilíbrio *(livro: C17, C22, pp. 942, 949)*

Executar configuração escolhida em diversos níveis de custo (por exemplo, 0; 0,5×; 1×; 2×; 3× da taxa + slippage presumidos) e mostrar resultado líquido para cada um e o **múltiplo de custo de equilíbrio**; em varreduras, mostrar a região lucrativa encolhendo com custos (fig. 21.14). Informar também **P/L líquido médio por operação como múltiplo do custo ida-e-volta** (cap. 16, O4). Resultados suspeitosamente altos *sem custos* sugerem estratégias rápidas e choques breves. **Complexidade:** baixa–média. **Validação:** execução 1× coincide com execução normal; resultados monotônicos em custo.

### O7 — Critérios de desempenho adicionais *(livro: C17, pp. 941–942)*

Adicionar a `Metrics` ou relatório analítico: **tempo de recuperação** (e maior duração de drawdown), **tempo no mercado**, **inclinação de retornos periódicos (mensais/trimestrais)** (detector de deterioração), **média de drawdowns máximos entre testes**, **lucro excluindo as N melhores operações/melhor mês** (análise de outliers, C18) e **capital sugerido = k × drawdown máximo** (livro: três vezes), somente informativo. Mesmo conjunto de O1/O2 do cap. 2; aqui o livro acrescenta inclinação de deterioração e revisão de outliers. **Complexidade:** baixa. **Validação:** fixtures.

### O8 — Seleção de parâmetros considerando vizinhos (“selecionar o platô”) *(livro: C9, C10, C15, pp. 919–929, 939–940)*

Na interface e nos “parâmetros recomendados” da API, classificar pela **pontuação suavizada pela vizinhança**, em vez da pontuação bruta; mostrar centros dos k melhores platôs. Combina com O1. O livro também recomenda limitar parâmetros (quatro ou menos) e prefere o **lado lento** de um mapa com dois platôs por motivos de custo. **Complexidade:** baixa quando O1 existir.

### O9 — Acompanhar deriva de parâmetros e monitor “modelo quebrou?” *(livro: C24, pp. 951–953)*

(a) Guardar os melhores parâmetros escolhidos em cada reteste da mesma estratégia ao longo do tempo e mostrar mudanças (livro retesta após 5–10% de dados novos; grande mudança é alerta); (b) para bot ao vivo/paper, comparar **tamanho e duração do drawdown atual com a distribuição do backtest** (perdas persistentes até o antigo drawdown máximo indicam problema; modelos não deveriam deteriorar desde o primeiro dia) e emitir **alerta** (depende do Notifier de propostas anteriores). Fórmula de probabilidade de drawdown `(1 − P)^(2μ/σ²)` serve apenas como referência aproximada (retornos normais). **Complexidade:** média. **Riscos:** falsos alarmes em drawdowns normais; caudas pesadas. **Validação:** fixtures com μ e σ conhecidos; um alerta por violação.

### O10 — Visão de consistência entre ativos *(livro: C20, C25, pp. 945, 954)*

Executar “mesmas regras, vários ativos” (BTC, ETH, SOL, BNB…) e mostrar percentual de ativos lucrativos e dispersão. Estratégia lucrativa em BTC e perdedora em ETH altamente correlacionado é suspeita (exemplo S&P/NASDAQ do livro). Ressalva: cripto tem alta correlação entre ativos (um fator), então concordância exagera independência; plataforma usa um bot por ativo, portanto relatório de pesquisa, não recurso operacional. **Complexidade:** média (percorrer serviço de backtest existente; requer dados importados por ativo). **Validação:** agregados recalculados a partir de resultados armazenados.

### O11 — Variante de contramovimento à tendência rápida como hipótese estrutural *(livro: C23, pp. 950–951)*

Dentro de tendência lenta de alta, entrar na reversão de média rápida (entrada no recuo) e sair somente quando a tendência lenta virar. No livro, lucro por operação subiu (277 → 741) e operações caíram (212 → 72) em um mercado. Para cripto, entrada no recuo já consta em O1 do cap. 9 e cap. 19; manter uma única hipótese (**H-PULLBACK-IN-TREND**), sem duplicar. **Complexidade:** baixa–média como estratégia parametrizada adicional.

### O12 — Métodos de busca: amostragem aleatória em vez de grade completa; genética somente com disciplina *(livro: C9, C12, pp. 919–922, 932–936)*

Se grades excederem `MAX_SWEEP_RUNS`: (1) preferir **amostragem aleatória (Monte Carlo)** do espaço de parâmetros, com semente registrada, contadores para conferir cobertura uniforme e execuções repetidas — preserva a *distribuição* dos resultados (necessária a O1), enquanto algoritmo genético retorna máximos; (2) se busca genética for adicionada, seguir receita do livro: reinícios múltiplos, salvar strings top 20 e conferir agrupamento; (3) nunca usar otimização sequencial como único método com parâmetros interativos (exemplo 2D do livro perde o pico). **Complexidade:** média. Não recomendado agora.

### O13 — Conciliar expectativas ao vivo com backtest *(livro: C2, C24, pp. 907, 952–953)*

Ao criar bot, registrar perfil **esperado** (taxa de acerto, operações por mês, drawdown máximo, permanência média) do backtest escolhido e compará-lo periodicamente ao paper/real; isso operacionaliza “definir expectativas antes do teste” e “o modelo está quebrado?”. Relaciona-se à proposta de paridade paper/backtest (livros 1/3). **Complexidade:** média.

### Não aplicável

Séries de dados específicas de futuros (ajustados retroativamente, indexados, prazo constante), datas de rolagem, dados à vista, procedimentos Excel/TradeStation, Futures Truth, dados sintéticos por regressão kernel (não agora; ideia de proporção de sinais iguais somente se houver necessidade), otimização por descida mais íngreme em superfícies contínuas, índices de referência de hedge funds.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Relatório de robustez de varredura O1 | muito alta | – | – | baixa–média | varreduras |
| 2 | Faixas predefinidas, grades geométricas e registro O2 | muito alta | – | – | baixa–média | – |
| 3 | Critérios adicionais O7 | alta | média | – | baixa | cap. 2 O1/O2 |
| 4 | Escada de custos O6 | alta | – | – | baixa–média | motor |
| 5 | Seleção de platô O8 | alta | – | – | baixa | O1 |
| 6 | Segmento bloqueado O3 | muito alta | – | – | média | segmentos |
| 7 | Relatório ajustado a choques O5 | alta | alta | – | média | patrimônio por candle |
| 8 | Deriva + monitor de modelo quebrado O9 | média | alta | alta | média | Notifier |
| 9 | Conciliação de expectativas O13 | média | alta | alta | média | O9 |
| 10 | Walk-forward O4 | alta | – | – | alta | O1, O2 |
| 11 | Visão entre ativos O10 | média | – | – | média | importação de dados |
| 12 | Hipótese de recuo dentro da tendência O11 | baixa | – | – | baixa–média | cap. 9 |
| 13 | Amostragem aleatória/GA O12 | baixa | – | – | média | O1 |

## 5. Arquivos afetados

`backtesting/domain/segments.py`, `backtesting/domain/engine.py` (atribuição por candle), `backtesting/application/service.py` e código de varredura (registro, agregados, segmento bloqueado, amostragem aleatória), `analytics/domain/metrics.py` e novos módulos analytics (robustez, choques, deriva), `docs/openapi.json`, telas de varredura do app (mapa de calor, platô, contagem no registro, aviso de segmento bloqueado), testes.

## 6. Plano incremental

1. Analytics somente de leitura sobre resultados de varreduras existentes: O1, O7 e O8 (sem alteração de esquema).
2. Grades geométricas e registro O2 (pequena mudança de esquema); escada de custos O6.
3. Segmento bloqueado O3 e relatório de choques O5.
4. O9/O13 quando existir Notifier.
5. Walk-forward O4 e visão entre ativos O10 como ferramentas de pesquisa.

## 7. Critérios de aceitação e testes

* Agregados e médias de vizinhos iguais a cálculos manuais em mapas sintéticos, incluindo bordas e cantos; picos sinalizados como soluções de pico, platôs não.
* Helper de grade geométrica produz inteiros estritamente crescentes e sem duplicatas para parâmetros de período.
* Segmento bloqueado avaliado uma vez; pedidos posteriores recusados/sinalizados; endpoints existentes inalterados por padrão.
* Atribuição de choques soma ao P/L total; execução sem choques recalcula de forma consistente.
* Escada de custos monotônica e ponto 1× igual à referência.
* ruff, mypy e testes existentes aprovados.

## Ressalvas

A maioria dos exemplos numéricos vem de futuros ou índices dos EUA, com custos em dólares e slippage (S&P, renda fixa, energia) que não se aplicam a cripto spot. “Retorno ajustado = média − 1σ → 84%” e fórmula de probabilidade de drawdown pressupõem retornos normais. “70% dos testes lucrativos” e “quatro ou menos variáveis” são regras práticas da experiência do autor/Futures Truth, não limites provados. Várias recomendações repetem Aronson (livro 3) e Chan (livros 1–2) e devem ser consolidadas no backlog geral. As pp. 954–969 e 977–982 não foram lidas em detalhe.
