# Livro 1 · Capítulo 2 — À procura de ideias

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

## 1. Resumo do capítulo (pp. 9–29)

O capítulo é um conjunto de **triagens rápidas** a aplicar a uma estratégia candidata antes de fazer o backtest.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Ideias são abundantes (artigos, blogs, fóruns); a maioria das prontas não sobrevive a um backtest cuidadoso (pararam de funcionar, só funcionam em small caps, ignoram custos). Uma ideia básica muitas vezes pode ser modificada até ficar lucrativa; a parte proprietária é a variação. | Onde achar estratégias e quanto desconfiar. | 9–11 |
| C2 | Ajustar a estratégia a *você*: horário de trabalho, habilidade de programação, capital, objetivo (renda vs. ganho de longo prazo). O período de posse determina a regularidade da renda. | Estratégia que o próprio dono não consegue operar. | 12–17 |
| C3 | O crescimento máximo no longo prazo vem do **índice de Sharpe** máximo (com alavancagem suficiente), não do buy-and-hold; um Sharpe maior permite mais alavancagem (detalhes adiados para o Cap. 6). | Julgar estratégias pelo retorno bruto. | 17, 19 |
| C4 | Comparar com um **benchmark**: para long-only, o índice de mercado; para dollar-neutral, uma taxa livre de risco. `Information Ratio = média(retornos em excesso) / desvio-padrão(retornos em excesso)`, `Excesso = carteira − benchmark`. O Sharpe é o caso especial com a taxa livre de risco; usa-se Sharpe pela comparabilidade. | Retorno sem contexto e sem consistência. | 18–19 |
| C5 | Regras práticas: poucas operações por ano → Sharpe baixo; drawdown maior que ~10% ou mais longo que ~4 meses → improvável um Sharpe alto; **Sharpe < 1 não serve isoladamente**; lucrativa quase todo mês → Sharpe anualizado tipicamente > 2; quase todo dia → > 3. | Triagem rápida com informação limitada. | 20–21 |
| C6 | **Drawdown** = patrimônio atual − máximo acumulado (a *high watermark*); drawdown máximo = maior queda de pico a vale, em % da watermark; **duração máxima do drawdown** = maior tempo para se recuperar; os dois normalmente não coincidem. Comparar com a própria tolerância. | Estratégia que você não consegue segurar psicologicamente. | 21–22 |
| C7 | **Custos de transação** = comissões + spread compra-venda (custo de liquidez) + impacto de mercado + slippage (atraso entre o gatilho e a execução). Ordens limitadas evitam o spread, mas custam operações perdidas. Estimativa de custo ≈ metade do spread médio (+ comissão) se o tamanho da ordem for pequeno. Exemplo: uma reversão à média com Bollinger de 5 minutos no ES vai de Sharpe ≈ 3 para ≈ −3 após 1 bp de custo. | Vantagens de alta frequência que somem após os custos. | 22–23 |
| C8 | **Viés de sobrevivência**: dados sem os papéis deslistados/falidos inflam os resultados, especialmente para ideias de "comprar barato"; pedir dados point-in-time. | Backtests inflados. | 24 |
| C9 | **Desempenho ao longo do tempo**: períodos antigos parecem melhores (menos concorrência, spreads maiores, mais distorção de sobrevivência); julgar pelos anos mais recentes. **Mudanças de regime** quebram a estacionariedade, então mais dados não são automaticamente mais robustos. | Confiar em uma amostra longa e heterogênea. | 24–25 |
| C10 | **Viés de data-snooping**: muitos parâmetros/regras → ajuste a acidentes; difícil de evitar mesmo com um ou dois parâmetros. Modelos simples duram. O quadro lateral de IA lista as condições dele para confiar em modelos: lógica sólida, poucos parâmetros, linear, simples, toda a otimização numa **janela móvel de lookback** com demonstração fora da amostra contínua. Dados financeiros independentes são mais escassos do que parecem (dados tick têm correlação serial). | Overfitting. | 25–27 |
| C11 | **Capacidade/nicho**: preferir estratégias pequenas demais para instituições. | Concorrência de grandes players. | 27 |

Não está neste capítulo: como calcular na prática o Sharpe anualizado ou o drawdown (Cap. 3, Exemplos 3.4–3.7). Chan não dá orientação sobre cripto; os pontos de cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| C4 benchmark | ✅ parcial | `buy_and_hold_return_pct` existe (`analytics/domain/metrics.py`). É só uma comparação de retorno; sem série de retornos em excesso, sem information ratio. |
| C3/C4/C5 Sharpe | ❌ | Sem Sharpe/Sortino/volatilidade/retorno anualizado em `Metrics`. |
| C6 drawdown | ⚠️ | `max_drawdown_pct` existe (pico a vale, % da watermark, bate com a definição do livro). **A duração não é calculada**, nem a série da high watermark. |
| C7 custos | ⚠️ | `fee_rate` fixo + `slippage_bps` fixo, mesmo código no backtest e no paper (`execution/domain/fills.py`). Sem sensibilidade ao nível de custo, sem custo de equilíbrio (break-even), sem impacto dependente do tamanho; custo de oportunidade de ordens limitadas não modelado. Só ordens a mercado no backtester. |
| C8 sobrevivência | ⚠️ | Pares cripto também podem ser deslistados; os candles são guardados por símbolo e a lista de símbolos é escolhida à mão, então um universo de "sobreviventes" escolhido à mão é provável. Sem tratamento de deslistagem. Não se aplica a backtest de um único par, mas é relevante ao comparar pares. |
| C9 ao longo do tempo | ⚠️ | Uma divisão cronológica treino/teste (`backtesting/domain/segments.py`). Sem detalhamento por ano/subperíodo, sem janelas móveis, sem rotulagem de regime. |
| C10 snooping | ⚠️ | As estratégias têm 2–4 parâmetros (bom). Os sweeps ranqueiam por uma única métrica **sem contagem de tentativas** e sem correção; a divisão treino/teste existe, mas é um único hold-out. |
| C2 ajuste ao operador | ✅ | Bots baseados em timeframe, automação, worker; documentado nos documentos de arquitetura. |
| C11 nicho | n/a | O capital é pequeno por desenho; nenhum modelo de capacidade é necessário agora. |

## 3. Oportunidades

### O1 — Adicionar Sharpe, Sortino, volatilidade e retorno anualizado em `Metrics` *(livro: C3–C5, pp. 17–21 · a anualização para cripto é adaptação nossa)*
* **Problema:** não dá para aplicar as próprias regras de triagem do livro (Sharpe < 1, razão vs. benchmark) nem comparar estratégias em termos ajustados ao risco.
* **Proposta:** calcular a partir dos retornos periódicos da curva de patrimônio. Fator de anualização derivado do timeframe dos candles e de **365 dias** (cripto negocia todo dia, ao contrário dos exemplos de ações do livro; a convenção exata é tema do Capítulo 3, então decidir lá). Taxa livre de risco configurável, padrão 0. Marcar as métricas como `None` quando houver poucos retornos.
* **Benefício:** o número útil mais ausente; permite comparar resultados de sweeps e ranquear por algo melhor que o PnL líquido.
* **Complexidade:** baixa–média (funções puras, tudo em `Decimal`; cuidado com raízes quadradas e com curvas de patrimônio que ficam planas enquanto fora do mercado).
* **Riscos:** Sharpe sobre poucos retornos, autocorrelacionados ou majoritariamente planos engana; um Sharpe alto numa amostra curta não é evidência. Deve exibir o tamanho da amostra ao lado.
* **Validação:** testes unitários com séries calculadas à mão; propriedade: escalar os retornos escala o Sharpe corretamente; retornos com variância zero dão `None`, não infinito.

### O2 — Duração do drawdown e série da high watermark *(livro: C6, p. 21)*
* **Problema:** só a profundidade é reportada; o livro trata a duração como igualmente importante para saber se o operador aguenta.
* **Proposta:** adicionar a duração máxima do drawdown (em barras e em tempo real) e expor a curva "underwater" para o gráfico do app.
* **Benefício:** responde "por quanto tempo isto pode ficar no vermelho?". **Complexidade:** baixa.
* **Risco:** um drawdown aberto no fim da série deve ser reportado como em andamento, não como recuperado.
* **Validação:** testes unitários incluindo uma série que nunca se recupera.

### O3 — Checagem de tolerância do operador *(livro: C6 p. 22 · adaptação para funcionalidade de produto)*
* **Proposta:** permitir que o operador informe o drawdown máximo aceitável (profundidade, duração) ao criar um backtest/bot; sinalizar execuções que o excedem. `max_drawdown_pct` já existe como limite de risco em *tempo de execução*; isto ligaria a pesquisa a ele.
* **Complexidade:** baixa. **Risco:** falso conforto se o drawdown do backtest for subestimado. **Validação:** teste de API para o sinalizador.

### O4 — Análise de sensibilidade a custos *(livro: C7, pp. 22–23)*
* **Problema:** uma premissa fixa de custo pode esconder uma estratégia que morre com custos ligeiramente maiores, exatamente o exemplo do ES do livro.
* **Proposta:** reexecutar (ou recalcular de forma barata) os mesmos sinais sob uma grade de valores de taxa/slippage; reportar o resultado líquido por nível e o **custo de equilíbrio (break-even)**. Uma dimensão de sweep talvez já permita isso, então verificar antes de construir.
* **Benefício:** ganho direto de robustez nos backtests. **Complexidade:** média (custos multiplicam o tempo de execução; cachear sinais).
* **Riscos:** só muda os custos, não o realismo do fill (impacto de mercado, posição na fila de ordens limitadas).
* **Validação:** uma estratégia projetada para ser marginal deve inverter o sinal num custo conhecido.

### O5 — Desempenho por subperíodo *(livro: C9, pp. 24–25)*
* **Proposta:** reportar métricas por ano/trimestre civil e para a janela mais recente, mais um sinalizador "recente vs. geral", além da divisão única treino/teste.
* **Benefício:** detecta decaimento e dependência de regime. **Complexidade:** baixa–média. **Risco:** subamostras pequenas são ruidosas; rotular os tamanhos de amostra. **Validação:** série sintética com uma quebra no meio.

### O6 — Contar as tentativas nos sweeps *(livro: C10, pp. 25–27)*
* **Problema:** ranquear N conjuntos de parâmetros e mostrar o vencedor superestima a qualidade dele; o livro nomeia o viés, mas adia o remédio para o Capítulo 3 (e livros posteriores dão correções formais).
* **Proposta (mínima):** registrar o número de combinações testadas em cada resultado de sweep e mostrá-lo ao lado do melhor resultado; exigir que o vencedor também seja aceitável na parte de teste separada. Sem estatísticas novas por enquanto.
* **Complexidade:** baixa. **Validação:** a resposta da API inclui a contagem de tentativas.

### O7 — Nota sobre sobrevivência/universo *(livro: C8, p. 24 · adaptação)*
Adicionar um aviso explícito ao comparar vários pares escolhidos a posteriori e registrar o histórico de listagem necessário para detectar deslistagens quando mais pares forem importados. Baixa prioridade até existir pesquisa multi-par.

### Não recomendado agora
* **Otimização por janela de lookback (C10, p. 27)** é a disciplina recomendada pelo livro (walk-forward). É uma funcionalidade maior e é melhor planejá-la depois do Capítulo 3 e dos livros posteriores sobre validação cruzada; registrada como backlog **B-WALK-FORWARD**.
* **Alavancagem baseada em Sharpe (C3)**: não existe alavancagem.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O1 Sharpe/Sortino/vol | alta | média | – | baixa–média | convenção de anualização do Cap. 3 |
| 2 | O2 duração do DD | média | alta | – | baixa | – |
| 3 | O6 contagem de tentativas | alta | – | – | baixa | sweeps (existem) |
| 4 | O4 sensibilidade a custos | alta | média | – | média | O1 |
| 5 | O5 subperíodos | média | – | – | baixa–média | O1 |
| 6 | O3 sinalizador de tolerância | baixa | média | – | baixa | O2 |
| 7 | O7 nota de universo | baixa | – | – | baixa | – |

## 5. Arquivos afetados
`api/src/modules/analytics/domain/metrics.py`, `analytics/presentation/schemas.py`, `backtesting/domain/segments.py`, `backtesting/application/service.py`, `backtesting/presentation/router.py`, schema de resultado do sweep, `docs/openapi.json`, app: schemas de `lib/backtests`, cards de métricas, gráfico de patrimônio/underwater (`equity-chart-rows.ts`), `check:consistency`.

## 6. Plano incremental
1. Funções puras de métricas + testes unitários (O1, O2) sem mudança de API.
2. Adicionar campos a `Metrics.to_dict` (aditivos, opcionais) e ao documento OpenAPI; o app os exibe.
3. Contagem de tentativas do sweep (O6).
4. Execução de sensibilidade a custos (O4).
5. Relatório por subperíodo (O5).
6. Sinalizador de tolerância (O3).

## 7. Critérios de aceite e testes
* Métricas existentes e execuções armazenadas inalteradas (apenas campos aditivos); execuções antigas mostram "n/a" nas novas.
* Fixtures calculadas à mão para Sharpe, Sortino, duração de drawdown (incluindo nunca recuperado).
* Todos os números continuam `Decimal`; sem float no domínio.
* A saída do sweep inclui o número de combinações.
* As novas métricas sempre mostram o tamanho da amostra; nenhuma é apresentada como garantia de retornos futuros.

## Ressalvas
Os limiares de Chan (Sharpe > 1, > 2, > 3; drawdown de 10% / 4 meses) são **regras práticas da experiência dele com ações/futuros**, não leis, e não foram calibrados para cripto. Usar apenas como padrões iniciais de triagem, configuráveis.
