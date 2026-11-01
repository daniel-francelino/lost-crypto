# Livro 2 · Capítulo 6 — Estratégias de momentum entre pregões

*Algorithmic Trading*, Chan (2013). Páginas do livro (PDF = livro + 18). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise. Todo o conteúdo das pp. 133–154 foi lido.

Este é o capítulo mais próximo do que Lost Crypto executa atualmente (tendência/rompimento, somente comprado). Os exemplos usam futuros, ações e carteiras de sentimento de notícias; os resultados não incluem custos (ressalva do livro 2, cap. 3) e usam dados anteriores a 2013.

## 1. Resumo do capítulo (pp. 133–154)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Quatro causas do momentum: persistência do sinal do retorno de rolagem de futuros; disseminação/aceitação lenta da informação; vendas/compras forçadas por fundos; manipulação por operadores de alta frequência. Momentum de *série temporal* (retorno passado do próprio ativo correlacionado ao futuro) versus *transversal* (persistência do desempenho relativo). | Entender por que existem tendências. | 133–134 |
| C2 | **Testar momentum de série temporal**: correlação (e valor-p) entre o retorno de uma janela retrospectiva e o retorno de uma janela futura de manutenção, para uma grade de pares (janela, manutenção), **usando pares não sobrepostos** (deslocar pelo maior dos dois intervalos); também correlacionar os *sinais*; expoente de Hurst e razão de variâncias como testes globais. Futuros TU: melhores compromissos entre correlação e valor-p em (60,10), (60,25), (250,10), (250,25), (250,60), (250,120). H = 0,44 e o teste da razão de variâncias não rejeitou passeio aleatório, pois momentum e reversão coexistem em horizontes diferentes. Preferir a menor duração de manutenção (melhor Sharpe). | Escolher janela e duração com evidência. | 134–137 |
| C3 | **Estratégia de série temporal** (Moskowitz et al.): posição comprada se o retorno de 12 meses for positivo, vendida se negativo; manter por um mês. Distribuir o capital diariamente em 1/25, formando tranches escalonadas. TU: Sharpe ≈ 1, retorno anual de 1,7% sobre o nocional, drawdown máximo 2,5%. BR, HG e TU também funcionam (Tabela 6.2). Explicação em futuros: o sinal do retorno de rolagem persiste. Um sinal de **retorno de rolagem defasado** (limite 3%) teve resultado melhor (Sharpe 2,1). Há poucas operações, portanto o **risco de seleção de dados é real**; o teste verdadeiro é fora da amostra. | Regra de referência para momentum. | 137–141 |
| C4 | Outros sinais de entrada: nova máxima de N dias; preço acima de média móvel (exponencial); banda superior de Bollinger; mais dias de alta que de baixa numa janela; filtro de Alexander (entrada após alta de x%, saída após recuo de x% desde a máxima). **Combinar reversão e momentum** pode funcionar melhor (CL: comprar se o preço estiver abaixo do nível de 30 dias antes, mas acima do nível de 40 dias antes; retorno anual 12%, Sharpe 1,1). O indicador S&P Diversified Trends (comprado acima da EMA, vendido abaixo): Sharpe 1,3, drawdown máximo −16,6% (1988–2010), mas desempenho fraco desde 2008. | Opções e combinações de regras de entrada. | 140–141 |
| C5 | Extração de retorno de rolagem por arbitragem futuro/ETF; VX versus ES (retorno anual 6,9%, Sharpe 1); momentum transversal em futuros (ordenar retornos de 12 meses: 18% e Sharpe 1,37 em 2005–2007, depois retorno anual −33% em 2008–2009). Momentum transversal em ações (decil superior contra inferior dos retornos de 12 meses, manter 25 dias): Sharpe 4,1 em 2007, depois retorno anual −30% em 2008–2009; resultado de longo prazo de Daniel e Moskowitz: retorno 16,7%, Sharpe 0,83 (1947–2007). Visão por fatores: retorno da ação = retorno do mercado + retornos dos fatores. | Alternativas transversais. | 141–148 |
| C6 | **Sentimento de notícias** como fator (Hafez e Xie: retorno anual de 52–156%, Sharpe 3,9–5,3 antes dos custos); estudos sobre humor no Twitter são questionados. **Vendas/compras forçadas de fundos mútuos** (Coval e Stafford): fator PRESSURE a partir de posições e fluxos; retornos aproximados de 17% + 17% + 7% antes dos custos. Dados custam cerca de US$ 10 mil por ano e atrasos causam slippage. | Momentum acionado por eventos e fluxos. | 148–151 |
| C7 | **Desvantagens do momentum**: é mais difícil torná-lo rentável; em geral tem Sharpe menor, pois janelas e períodos de manutenção longos geram **poucos sinais independentes**; há **crashes de momentum** após crises financeiras (segundo Daniel e Moskowitz, após 1929 uma estratégia precisou de mais de 30 anos para recuperar sua máxima); o horizonte do momentum causado por notícias **encurta quando chegam mais operadores**, sem calendário para ajustar a duração. | Expectativas realistas. | 151–153 |
| C8 | **Vantagens**: stops são coerentes com momentum (um sinal oposto funciona como stop); a saída é temporal ou por stop, portanto **a perda por posição é limitada e o potencial de alta é ilimitado**; caudas pesadas (curtose alta) favorecem momentum (no exemplo 1.1, uma série aleatória com curtose de TU e sem autocorrelação igualou o retorno de momentum de TU em 12% das simulações); diversificação entre classes de ativos; combinar momentum com estratégias de reversão à média aumenta Sharpe e reduz drawdown. | Por que ainda usar a estratégia. | 153–154 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Estratégias de momentum temporal | ✅ | `ema_crossover` (preço acima da EMA) e `donchian_breakout` (nova máxima de N dias) já cobrem duas famílias de entrada de C4. |
| Sinal oposto como stop | ✅ | Ambas saem com sinal oposto; há `stop_loss_pct` e `take_profit_pct` opcionais; stop atravessado por lacuna é executado na abertura. |
| Saída por tempo | ❌ | Não há `max_holding_candles` (também citado no livro 1, cap. 7 O2). |
| Escolha de janela/manutenção baseada em evidência | ❌ | Parâmetros vêm do operador e das varreduras; não há grade de correlação ou teste de momentum. |
| Tranches escalonadas (1/N do capital ao dia) | ❌ | Um bot mantém uma posição; não há tranches nem medição do efeito da data inicial. |
| Combinação de momentum e reversão | ❌ | Não existe no catálogo. |
| Momentum transversal | ❌ | Um ativo por bot. |
| Sentimento de notícias/fatores de fluxo | ❌ | Não há dados externos. |
| Aviso sobre poucos sinais independentes | ⚠️ | `round_trips` é apresentado, mas não há aviso para contagem baixa (livro 1, cap. 3 O6; livro 2, cap. 1 O3). |
| Crashes de momentum/regimes | ❌ | Não há tratamento (livro 2, cap. 5 O1 propõe quebras nomeadas). |
| Custos | ✅ | Sempre incluídos nos backtests. |

## 3. Oportunidades

### O1 — Diagnósticos de correlação defasada para momentum *(livro: C2, pp. 134–137)*

* **Problema:** as janelas de observação e manutenção das estratégias de tendência são escolhidas por varredura, aumentando a seleção de dados; o livro oferece um método estatístico para localizar onde existe momentum.
* **Proposta:** ampliar o módulo de diagnósticos de séries (livro 2, cap. 2 O1) com grade de pares não sobrepostos de retornos `(look-back, holding)` → correlação de Pearson e valor-p (e versão baseada nos sinais); exibir tabela/mapa de calor e contagens na página de dados de mercado. Mostrar Hurst/razão de variâncias ao lado e explicar possíveis divergências.
* **Benefício:** faixas iniciais fundamentadas para `fast/slow_period`, `entry/exit_period` e limite de manutenção, com mais poder do que contar operações do backtest.
* **Complexidade:** baixa a média (funções puras; calcular valor-p da correlação exige função de sobrevivência da distribuição t, implementada ou aproximada de forma explícita).
* **Riscos:** a grade também envolve testes múltiplos (49 pares no exemplo do livro); retornos cripto têm caudas pesadas e agrupamento de volatilidade; amostras não sobrepostas são pequenas em horizontes longos (os valores-p do livro ficam no limite: 0,017–0,09); correlação não equivale a lucro negociável.
* **Validação:** séries AR(1) sintéticas com autocorrelação positiva/negativa conhecida; passeio aleatório deve gerar correlações não significativas; contagens devem obedecer à regra de não sobreposição.

### O2 — Opção de saída temporal *(livro: C3, C8, pp. 137–138, 153)*

Já proposta no livro 1, cap. 7 O2. Este capítulo acrescenta a escolha fundamentada pelo diagnóstico O1 e observa que saída temporal e stops limitam a **perda por posição**. Adicionar como parâmetro opcional às duas estratégias e excluí-lo das varreduras padrão. **Complexidade:** baixa.

### O3 — Sensibilidade à data inicial como alternativa simples às tranches *(livro: C3, p. 138 · adaptação)*

* **Problema:** uma execução começa numa só data; os resultados podem depender dela, sobretudo quando há poucas operações. O livro reduz esse efeito investindo 1/25 do capital por dia, em 25 tranches sobrepostas.
* **Proposta:** executar a mesma configuração a partir de várias datas iniciais deslocadas (por exemplo, de 0 a N candles/dias) e apresentar a dispersão dos retornos/drawdowns. Não exige alterar o modelo de uma posição por bot.
* **Benefício:** mede diretamente a fragilidade temporal do resultado e serve a qualquer estratégia. **Complexidade:** baixa a média (custo computacional; já existe execução em lote por varreduras). **Riscos:** deslocar a data altera o aquecimento e a primeira operação; interpretar como dispersão, não valor esperado. **Validação:** estratégia com artefato temporal deliberado deve mostrar dispersão ampla.
* A carteira real de tranches fica registrada como **B-TRANCHES** (exige várias subposições simultâneas por bot).

### O4 — Aviso para poucos sinais independentes e horizontes longos *(livro: C7, p. 151)*

Adicionar ao bloco de alertas (livro 2, cap. 1 O3): número de operações completas abaixo de limite relativo ao número de parâmetros livres; duração de manutenção grande perante o tamanho da amostra. Limites configuráveis. **Complexidade:** baixa.

### O5 — Pesquisar uma combinação de momentum e reversão *(livro: C4, p. 140 · hipótese apenas)*

O livro relata que, para um contrato futuro, combinar a regra “preço abaixo do de 30 dias atrás, mas acima do de 40 dias atrás” superou cada regra isolada. Não há evidência para cripto. Tratar como **experimento**: variante com condição de tendência de longo prazo e recuo de curto prazo, avaliada só depois dos controles de integridade, truncamento e sensibilidade a custos. ID da hipótese **H-MOM-REV**. **Complexidade:** média; risco alto de seleção de dados (mais regras/parâmetros).

### O6 — Atenção a crashes de momentum *(livro: C7, pp. 151–153; relacionado ao livro 2, cap. 5 O1)*

Usar quebras de regime nomeadas e métricas por regime para verificar se o desempenho caiu após crashes gerais do mercado e destacar o resultado. Para operação real, as pausas atuais por drawdown e perda diária já protegem; não se propõe mecanismo novo. **Complexidade:** depende do livro 2, cap. 5 O1.

### O7 — Momentum transversal numa cesta de criptoativos *(livro: C5, pp. 144–148)*

Relatório somente de pesquisa (ordenar os pares armazenados por retorno passado e testar se o grupo superior continua na frente), apenas comprado. Aplicam-se as limitações e o ID do backlog do livro 2, cap. 4 O4 (**B-MULTI-ASSET**). Viés de sobrevivência é grave para moedas removidas de listagem.

### Não aplicável

Sinais de retorno de rolagem e arbitragem de futuros/ETFs, VX–ES, feeds de sentimento de notícias e fatores de pressão de fundos mútuos.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O4 aviso de poucos sinais | média | – | – | baixa | livro 2, cap. 1 O3 |
| 2 | O1 diagnósticos de momentum | alta | – | – | baixa–média | livro 2, cap. 2 O1 |
| 3 | O3 sensibilidade à data inicial | alta | – | – | baixa–média | infraestrutura de varredura existente |
| 4 | O2 saída temporal | baixa | média | – | baixa | O1 para escolher valores |
| 5 | O6 atenção a crashes | média | média | – | baixa | livro 2, cap. 5 O1 |
| 6 | O5 experimento de momentum + reversão | média | – | – | média | integridade, truncamento e sensibilidade a custos |
| 7 | O7 relatório transversal de moedas | baixa | – | – | média | dados de vários pares |

## 5. Arquivos afetados

`analytics/domain/` (grade de correlação e valores-p), `market_data/presentation/router.py` (endpoint de diagnósticos), `strategies/domain/ema_crossover.py`, `donchian_breakout.py` (parâmetro opcional de saída) e `base.py`, `backtesting/application/service.py` (lotes com deslocamento da data inicial), `docs/openapi.json`, painel de diagnóstico de dados de mercado e formulário de backtest no app, `lib/shared/strategies/params.ts` e testes.

## 6. Plano incremental

1. Avisos de baixa contagem de sinais (baixo custo).
2. Módulo de diagnósticos: grade de correlação e valores-p com testes sintéticos.
3. Executor de sensibilidade à data inicial usando varreduras.
4. Saída temporal opcional com testes; escolher padrões apenas pelos diagnósticos.
5. Quebras de regime (livro 2, cap. 5) e, depois, experimentos O5/O7.

## 7. Critérios de aceitação e testes

* A grade usa somente pares não sobrepostos; apresenta contagens por célula; dados AR(1) sintéticos recuperam o sinal esperado.
* Sensibilidade à data inicial apresenta mínimo/mediana/máximo de retorno e drawdown entre deslocamentos e é determinística.
* Novos parâmetros são opcionais e, por padrão, não alteram o comportamento atual.
* Ruff, mypy e testes existentes passam.

## Ressalvas

Todos os retornos citados (Sharpe até 5,3, retorno anual até 156%) são anteriores a custos e, em geral, usam dados de ações ou futuros anteriores a 2013; vários (momentum transversal de ações e sentimento de notícias) entraram em colapso ou dependem de dados de fornecedores. Os “crashes de momentum” e a recuperação de 30 anos após 1929 lembram que uma estratégia de tendência pode ficar em drawdown durante anos; isso não implica que tendências de cripto persistirão.
