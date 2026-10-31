# Livro 1 · Capítulo 3 — Backtesting

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

Nota de leitura: as pp. 32–36 (Excel, MATLAB, TradeStation e plataformas comerciais) foram apenas folheadas; descrevem ferramentas, não métodos. O restante (pp. 36–67) foi lido. No texto extraído o sinal de raiz quadrada se perde na prosa (a p. 44 imprime "12 times"), mas o código das pp. 45–46 mostra `SQRT(252)`, o que confirma a fórmula abaixo.

## 1. Resumo do capítulo (pp. 31–67)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Replicar cada estratégia você mesmo: prova que você a entendeu, expõe erros da pesquisa original e permite testar variações. | Confiar em resultados publicados não verificados. | 31 |
| C2 | **Dados ajustados** (splits, dividendos): multiplicar os preços anteriores por um fator para que os retornos não mudem; dados sem ajuste criam sinais falsos nas datas ex. | Saltos de preço falsos. | 36–40 |
| C3 | **Viés de sobrevivência**: o exemplo de brinquedo "comprar as ações de menor preço" deu −42% com papéis deslistados incluídos e +388% sem eles. Mitigação: registrar dados point-in-time você mesmo daqui em diante, ou testar em dados recentes. | Resultados inflados. | 40–42 |
| C4 | **Dados de máxima/mínima são mais ruidosos** que abertura/fechamento; uma ordem limitada "abaixo da máxima" pode não ter sido executada. Uma checagem de sanidade: calcular os retornos, inspecionar os que passam de ~4 desvios-padrão e exigir um evento de notícia ou um movimento de todo o mercado que os explique. | Backtests que lucram com ticks ruins. | 42–43 |
| C5 | **Sharpe e drawdown** são as duas medidas principais (o retorno anual bruto exige qualificações demais: denominador, alavancagem). **Não** subtrair a taxa livre de risco em estratégias dollar-neutral ou só intradiárias (sem custo de financiamento); subtrair quando a estratégia tem financiamento. **Sharpe anualizado = √N_T × Sharpe no período T**, onde N_T é o número de períodos em um ano (N_T = 252 × 6,5 = 1.638 para retornos horários da sessão dos EUA; calcular 252 × 24 é citado como erro comum). Exemplo 3.4: `SQRT(252)*AVERAGE(excess)/STDEV(excess)`. | Comparar estratégias de forma justa. | 43–47 |
| C6 | **Cálculo do drawdown** (Exemplo 3.5): retorno composto acumulado; high watermark corrente; drawdown = (1+HWM)/(1+cum) − 1; contador de duração volta a 0 quando o drawdown é 0, senão +1; máximos de ambos. Resultado do exemplo: 10,53% e 497 dias. | Números de drawdown reprodutíveis. | 48–50 |
| C7 | **Viés de look-ahead**: usar informação ainda não disponível (por exemplo a mínima do dia, ou coeficientes de regressão ajustados em toda a amostra). Corrige-se atrasando (lag) as entradas do sinal. **Teste de truncamento**: rodar em todos os dados e salvar as posições A; rodar nos dados truncados pelos últimos N períodos (10–100) e salvar B; cortar A ao mesmo tamanho; devem ser idênticas. | Vazamento silencioso do futuro. | 51–52, 59 |
| C8 | **Viés de data-snooping**: regra prática ≤ **5 parâmetros**; escolhas qualitativas (entrar na abertura vs. fechamento, carregar overnight…) também contam; tamanho de amostra ≈ **252 × número de parâmetros livres** (declarado como baseado em experiência, não em literatura), contado em observações *independentes* (7 meses de dados por minuto para um modelo diário são só ~147 pontos). | Overfitting. | 52–53 |
| C9 | **Fora da amostra**: treinar primeiro, testar na parte posterior (metades aproximadamente iguais; teste ≥ ⅓ do treino, no mínimo). Se o teste for ruim, simplificar o modelo. A **otimização móvel (rolling)** é a versão mais rigorosa; modelo "sem parâmetros" = parâmetros reotimizados numa janela móvel de lookback; é melhor tirar a média entre conjuntos de parâmetros do que escolher um só "melhor". O **paper trading** é o teste final fora da amostra, e o período desde a publicação conta como fora da amostra se você não ajustou sobre ele. | Estimativa honesta de generalização. | 53–55 |
| C10 | **Análise de sensibilidade**: variar parâmetros e fazer pequenas mudanças qualitativas; um modelo que só funciona no ótimo exato está sobreajustado. Remover condições uma a uma e continuar removendo enquanto o resultado do **teste** não piorar. Nunca adicionar ou ajustar para melhorar o conjunto de teste (ele vira treino). Depois, dividir o capital entre valores de parâmetros. | Ótimos frágeis. | 60 |
| C11 | **Custos** (Exemplo 3.7): uma estratégia com Sharpe 4,47 antes dos custos em small caps teve 0,25 no S&P 500 e −3,19 após 5 bp por operação. Tratar resultados sem dados livres de sobrevivência como limites superiores. | Custos e universo decidem a viabilidade. | 60–65 |
| C12 | **Refinamento**: pequenas variações (por exemplo agir na abertura em vez do fechamento elevou o Sharpe de −3,19 para 0,78 após custos, Exemplo 3.8); preferir refinamentos com lógica econômica, e qualquer mudança deve melhorar treino e teste. | Melhorar sem sobreajustar. | 65–66 |
| C13 | Honestidade do resumo: pular algumas precauções é aceitável para uma primeira olhada; problemas ainda podem aparecer só no paper/live. | Perfeccionismo vs. progresso. | 67 |

Os dois exemplos trabalhados de Chan, de pairs trading e reversão à média, são específicos de ações (pares de ETFs, S&P 500) e não são transferíveis como tal; só a metodologia é. Nenhum conselho sobre cripto aparece no capítulo.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C2 dados ajustados | n/a | O spot cripto não tem splits/dividendos. Eventos do lado da exchange (redenominação de símbolo, deslistagem) não são tratados. |
| C3 sobrevivência | ❌ | Sem tratamento de deslistagem; universo escolhido à mão. Poderíamos começar a registrar listagens point-in-time agora. |
| C4 sanidade dos dados | ⚠️ | `Candle` **não tem checagem de consistência OHLC** (`high ≥ max(open, close)`, `low ≤ min(open, close)`, preços positivos, volume não negativo) em `market_data/domain/models.py`. Apenas o módulo de risco rejeita *entradas* em candles cuja amplitude excede `max_candle_range_pct`. O backtester não tem esse filtro nem relatório de outliers. |
| C4 cobertura | ❌ | `find_gaps` existe e aparece no endpoint de cobertura, mas `BacktestService._check_candles` exige apenas **pelo menos um** candle no intervalo, então um backtest roda silenciosamente sobre buracos. |
| C5 Sharpe | ❌ | Não calculado (ver capítulo 2). Convenção de anualização indefinida. |
| C6 drawdown | ⚠️ | Profundidade calculada corretamente (`max_drawdown_pct`); duração e série da watermark ausentes. |
| C7 look-ahead | ✅ por construção, ❌ sem teste de regressão | O motor executa na abertura do candle seguinte e a estratégia só vê candles fechados (`engine.py`). Sem teste automatizado de truncamento (grep por `truncat`/`lookahead` em `api/tests` acha apenas um comentário). |
| C8 snooping / tamanho da amostra | ⚠️ | As estratégias têm ≤ 4 parâmetros. Sem checagem de tamanho de amostra, sem contagem de tentativas nos sweeps (`create_sweep` limita a grade com `MAX_SWEEP_RUNS`, mas não registra aviso de testes múltiplos). |
| C9 fora da amostra | ⚠️ | Uma divisão fixa com a estratégia rodando uma vez sobre todos os dados (`segments.py`). Sem walk-forward, sem regra de tamanho mínimo. O paper trading existe e é obrigatório antes do live. |
| C10 sensibilidade | ⚠️ | Os sweeps dão a matéria-prima, mas não há visão de robustez (por exemplo estabilidade da vizinhança da melhor célula). |
| C11 custos | ⚠️ | Taxa e slippage fixos (capítulo 2). |
| C12 refinamento | ✅ possível | Experimentos são baratos; sem governança em torno disso. |

## 3. Oportunidades

### O1 — Sharpe/Sortino anualizados com convenção explícita para cripto *(livro: C5 · a convenção é adaptação nossa)*
* **Livro:** Sharpe = √N_T × média/desvio-padrão dos retornos em excesso no período T; N_T deve contar períodos reais de negociação; uma divergência (252 × 24 para uma sessão de 6,5 horas) é um erro.
* **Adaptação:** cripto negocia 24/7, então N_T = 365 × (24 h / horas do candle), por exemplo 8.760 para 1h, 365 para 1d. Taxa livre de risco = 0 por padrão porque a estratégia é spot long-only sem financiamento, em linha com a regra do livro (subtrair só quando há financiamento); manter configurável.
* **Problema:** métrica ausente. **Benefício:** a principal medida de comparação do livro; ranqueia sweeps. **Complexidade:** baixa. **Risco:** curvas de patrimônio paradas em caixa reduzem a volatilidade e favorecem o índice; reportar o **tempo no mercado** junto; poucos retornos dão razões pouco confiáveis (mostrar o tamanho da amostra). **Validação:** reproduzir os números do Exemplo 3.4 do livro (Sharpe 0,7893 para buy-and-hold de IGE) com as mesmas entradas num teste unitário; testes com séries conhecidas.

### O2 — Duração do drawdown e série da watermark *(livro: C6, pp. 48–50)*
Implementar exatamente a recorrência do livro (o contador de duração volta a zero quando o drawdown é zero) e expor as duas séries. **Complexidade:** baixa. **Validação:** reproduzir as definições do Exemplo 3.5 numa curva sintética; drawdown em andamento reportado como em andamento.

### O3 — Validação de integridade dos candles *(livro: C4, pp. 42–43)*
* **Proposta:** validar consistência OHLC e valores positivos na construção/importação; rejeitar ou pôr em quarentena linhas ruins com um contador; adicionar um relatório de outliers (retornos além de k desvios-padrão; o livro sugere ~4) que o operador possa revisar; fazer o backtester opcionalmente excluir/sinalizar execuções que cruzem candles sinalizados.
* **Nota:** o passo do livro de "conferir com notícia ou movimento de todo o mercado" é manual; aqui poderíamos comparar o movimento com outros pares (adaptação).
* **Benefício:** protege todo backtest de dados ruins. **Complexidade:** baixa–média. **Risco:** filtragem excessiva pode apagar crashes reais; sinalizar, não descartar em silêncio. **Validação:** testes unitários com candles malformados; teste de integração dos contadores do job de importação.

### O4 — Recusar (ou avisar de forma explícita sobre) backtests com lacunas nos dados *(adaptação, motivada por C4/C11)*
Usar o `find_gaps` existente dentro de `_check_candles`; devolver a contagem/tamanho das lacunas no resultado da execução e falhar ou avisar acima de um limite. **Complexidade:** baixa. **Risco:** janelas de manutenção da exchange são lacunas legítimas; fazer um aviso com tolerância. **Validação:** teste de integração com um buraco.

### O5 — Teste de regressão de look-ahead (teste de truncamento) *(livro: C7, pp. 52, 59)*
Automatizar o procedimento do livro: rodar o motor com os candles completos e com os últimos N removidos, comparar os **sinais/posições** no prefixo comum, para toda estratégia registrada. **Complexidade:** baixa (funções puras, rápido). **Benefício:** protege contra o bug silencioso mais perigoso sempre que uma estratégia for adicionada. **Validação:** o próprio teste, mais uma estratégia falsa deliberadamente com vazamento que deve reprová-lo.

### O6 — Guarda de tamanho de amostra e contagem de parâmetros *(livro: C8, pp. 52–53 · limiares são regras práticas do autor)*
Calcular o número de parâmetros livres a partir dos `PARAMETERS` da estratégia, comparar o número de observações **independentes** (operações ou barras, não ticks) com 252 × parâmetros e emitir um aviso (não um bloqueio). Calibrar para cripto depois. **Complexidade:** baixa. **Risco:** a regra do 252 é explicitamente baseada em experiência; tratar como heurística e tornar configurável. **Validação:** teste unitário do aviso.

### O7 — Contagem de tentativas e visão de sensibilidade para sweeps *(livro: C8, C10, pp. 52–60)*
Armazenar o número de combinações em cada resultado de sweep; adicionar uma visão de **robustez da vizinhança** (o desempenho cai suavemente ao redor da melhor célula ou colapsa?) e exigir que o vencedor também seja aceitável no segmento de teste; nunca ranquear pelo segmento de teste. **Complexidade:** média. **Risco:** ainda sem correção formal de testes múltiplos (livros posteriores tratam disso). **Validação:** um sweep sintético com um único pico deve ser sinalizado como frágil.

### O8 — Otimização walk-forward (móvel) *(livro: C9, pp. 54–55)*
O método rigoroso de fora da amostra do livro. Funcionalidade grande: reajustar parâmetros numa janela de lookback e testar no bloco seguinte, concatenando os resultados fora da amostra. **Complexidade:** alta. **Risco:** custo computacional; vazamento se as janelas se sobrepuserem errado. Manter como backlog **B-WALK-FORWARD** e planejar depois dos capítulos sobre validação cruzada do Livro 5.

### O9 — Sensibilidade a custos e custo de equilíbrio *(livro: C11, pp. 60–65)*
Igual ao capítulo 2 O4; reexecutar sinais em grades de taxa/slippage e reportar onde a lucratividade desaparece. **Complexidade:** média.

### O10 — Registro de listagens point-in-time *(livro: C3, p. 40 · adaptação)*
Começar a guardar diariamente a lista de símbolos e o status da exchange para que um universo livre de sobrevivência exista no futuro. **Complexidade:** baixa; o valor cresce com o tempo, então é barato começar cedo.

### Não aplicável
Ajuste de splits/dividendos (C2), exemplos de universos de ações (exemplos de C11, C12), escolha de plataformas (pp. 32–36).

## 4. Prioridade

| # | Item | Qualidade do backtest | Confiabilidade | Gestão de risco | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O5 teste de truncamento | alta | alta | – | baixa | – |
| 2 | O3 integridade dos candles | alta | alta | média | baixa–média | – |
| 3 | O4 guarda de lacunas | alta | média | – | baixa | `find_gaps` (existe) |
| 4 | O1 Sharpe/Sortino | alta | – | média | baixa | – |
| 5 | O2 duração do DD | média | – | alta | baixa | – |
| 6 | O7 tentativas/robustez do sweep | alta | – | – | média | O1 |
| 7 | O6 guarda de tamanho de amostra | média | – | – | baixa | – |
| 8 | O9 sensibilidade a custos | alta | – | média | média | O1 |
| 9 | O10 registro de listagens | baixa agora | – | – | baixa | – |
| 10 | O8 walk-forward | alta | – | – | alta | O1, O7, Livro 5 |

## 5. Arquivos afetados
`market_data/domain/models.py` (validação de Candle), `market_data/application/service.py` (contadores de importação), `backtesting/application/service.py` (`_check_candles`, sweeps), `backtesting/domain/engine.py` (somente leitura para O5), `analytics/domain/metrics.py`, `backtesting/domain/segments.py`, novos testes em `api/tests/unit` (truncamento, métricas, validação de candles), `docs/openapi.json`, cards de métricas e página de sweep do app.

## 6. Plano incremental
1. O5 teste de truncamento para toda estratégia registrada (sem mudança no código de produção).
2. O3 + O4 integridade dos dados (validação de domínio, guarda de lacunas, contadores de importação).
3. O1 + O2 métricas (funções puras, campos aditivos na API, exibição no app).
4. O7 + O6 honestidade dos sweeps (contagem de tentativas, robustez, aviso de tamanho de amostra).
5. O9 sensibilidade a custos.
6. O10 registro de listagens; O8 como projeto separado depois.

## 7. Critérios de aceite e testes
* O teste de truncamento passa para todas as estratégias e falha para uma deliberadamente com vazamento.
* Candles malformados são rejeitados ou sinalizados com uma contagem; sem descartes silenciosos.
* Um backtest sobre um intervalo com lacunas reporta as lacunas.
* Fixtures de Sharpe/drawdown batem com cálculos à mão, incluindo séries no estilo dos Exemplos 3.4/3.5; retornos com variância zero dão `None`.
* Apenas mudanças aditivas na API; execuções armazenadas não são afetadas.
* Tudo continua `Decimal` no domínio; ruff, mypy e todos os testes existentes continuam verdes.

## Ressalvas
Os números de Chan (≤ 5 parâmetros, 252 × parâmetros, 4 desvios-padrão, teste ≥ ⅓ do treino) são **regras práticas dele**, não resultados estatísticos, e foram derivados para estratégias de ações. Resultados de backtest não garantem retornos futuros; taxas, slippage, overfitting e efeitos específicos de cripto (24/7, liquidez fragmentada, deslistagens) podem piorar os resultados reais.
