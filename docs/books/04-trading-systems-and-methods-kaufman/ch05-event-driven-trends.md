# Livro 4 · Capítulo 5 — Tendências acionadas por eventos

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** lidas integralmente pp. 181–184 (definição de swing trading e início da construção de gráficos de oscilação) e 222–233 (**rompimento de N dias, regras Donchian e Turtles**). Restante da construção de filtros de oscilação (pp. 184–194) e **gráficos ponto-e-figura (pp. 195–221)** não foram lidos nem são resumidos. O relatório trata sobretudo de rompimento de N dias, seção mais próxima de `donchian_breakout`.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Métodos tendenciais **acionados por eventos ignoram o tempo decorrido** e reagem ao preço que atinge novo extremo: nova máxima/mínima “significa que algo importante mudou”. O autor recomenda perguntar se métodos novos e complexos superaram os simples. **Swing trading**: oscilação sustentada maior que limite (*filtro de swing*, unidades absolutas ou percentual); gráfico sem eixo de tempo; construção clássica em sete etapas com convenção de dia externo aplicada consistentemente. | Definição tendencial objetiva mais simples. | 181–184 |
| C2 | **Rompimento de N dias**: comprar quando máxima de hoje supera máxima dos N dias anteriores; vender quando mínima cai abaixo das mínimas anteriores (sempre posicionado, invertendo). Forma conservadora usa **fechamentos** para confirmação, entrando mais tarde. N menor que ~5 dias deixa de ser acionado por evento e passa a continuação de tendência. **Risco** da posição é distância da entrada ao extremo oposto de N dias: **N maior → risco por operação muito maior**. Comparar com médias temporais no cap. 8. | Sistema tendencial básico e perfil de risco. | 222–223 |
| C3 | **Regra de quatro semanas de Donchian** (entrada acima das máximas das quatro semanas anteriores, com regra vendida simétrica): rompimento lento e duradouro. Sucesso e dificuldade de controle de risco vêm do canal escalar com volatilidade de cada mercado, fazendo **mercados voláteis dominarem os calmos**. Prática moderna dimensiona posições para manter **risco constante**, corrigindo o maior problema das estratégias acionadas por eventos. | Dimensionar posição em rompimentos. | 223–224 |
| C4 | **Escolher N**: testar faixa é abordagem óbvia; alternativa: **`N_t = N_I × V_n / V_c`** (volatilidade normal/atual; N diminui com aumento de volatilidade, técnica adaptativa). | N fixo ou adaptativo. | 224–225 |
| C5 | **Teste da regra de N dias** (petróleo bruto, N de 10 a 100, passos de 5, 1991–2010, sem custos, futuros ajustados retroativamente): apenas **um teste perdeu**. Padrão difere entre 1991–2000 e 2001–2010; **melhor N por lucro líquido: 75, 15 e 100** para primeira década, segunda e período total. Tabela 5.7 (2001–2010, futuros e ações): melhor N varia de **10 a 95** entre mercados; proporção de N rentáveis (“robustez”) vai de ~21% a 100%; operações vencedoras: 31%–48%. | N instável entre mercados e períodos. | 225–227 |
| C6 | **Rompimento semanal**: agir apenas no fecho de sexta; estudo de futuros de 1982 encontrou risco maior que sistemas de cruzamento em ~75%. Implementar em barras semanais, não derivar de diárias (semanas encerradas quinta quebram lógica do dia da semana). | Canal de frequência menor. | 225–228 |
| C7 | **Sistema de rompimento dinâmico** (Stridsman): antecipar níveis de entrada/saída do dia seguinte a partir de múltiplo do desvio-padrão e colocar stops antecipadamente; analisar distribuição do tempo até stop (falhas rápidas versus posições longas) para posicionar melhor as ordens. | Colocação de ordens de rompimento. | 228 |
| C8 | **Futuros versus ações**: futuros são alavancados e comissão é ínfima perante nocional (~0,7 pb por operação de E-mini); ações custam ~3 pb por ida e volta fixa de US$ 9. Julgar **retorno por unidade (centavos/ação, dólares/contrato)** para verificar cobertura de comissão/slippage. | Realismo de custos. | 228–229 |
| C9 | **Donchian 40/20** (registro antigo de rompimento de N dias: canal longo para entrada, curto para saída) e **sistema Turtles**: S1 entra no rompimento de 20 dias e sai no extremo oposto de 10, com **filtro** que pula entrada se operação S1 anterior foi lucrativa; S2 usa 55/20 sem filtro. **Risco**: stop a 2L da entrada, sendo L ATR de 20 dias em dólares; tamanho da unidade iguala `L × valor por ponto` entre mercados (**1 unidade = 1% do patrimônio / (L × BPV)**); limites por grupos correlacionados (4/6/10/12 unidades), piramidagem de uma unidade a cada movimento favorável de L até cinco, elevando stops a 2L. **Risco de carteira**: reduzir posição 20% por cada 10% de drawdown desde o pico e recompor 10% por etapa de recuperação. S1 mais rápido em cobre lucrou apenas no início dos anos 1980; S2 lento lucrou com consistência por 30 anos; rompimento simples em cobre 1980–2010 foi lucrativo para todos N menos um, e “55 e 20 não foram os melhores”. | Conjunto completo de regras, dimensionamento e risco. | 229–233 |

Exemplos são futuros e ações, comprados e vendidos, com alavancagem. Referências a cripto são **adaptação nossa**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Rompimento de N dias com canal de saída separado (40/20, 20/10, 55/20) | ✅ | `donchian_breakout`: padrão `entry_period` 20, `exit_period` 10 (Turtle S1), apenas comprado, com **fechos versus canais anteriores** (variante mais conservadora). |
| Risco cresce com N; dimensionamento de risco constante | ⚠️ | `RiskLimits.max_risk_per_trade_pct` dimensiona pelo stop, mas stop Donchian é opcional e percentual, **não ligado ao canal nem ATR**. Sem stop, risco entre entrada e mínima do canal de saída não é limitado pelo dimensionamento. |
| Stop/dimensionamento por ATR (`L`) | ❌ | Não há auxiliar ATR nem stop baseado em ATR (também livro 4, cap. 4 O3). |
| N adaptativo à volatilidade | ❌ | Não existe (ver cap. 17). |
| Robustez pela proporção de N rentáveis | ❌ | Varreduras mostram grade, mas não proporção de células rentáveis nem estabilidade da vizinhança (livro 1, cap. 3 O7; livro 3, cap. 6 O4). |
| Instabilidade do melhor N entre períodos | ❌ | Não comparada por subperíodo. |
| Filtro Turtle após operação vencedora | ❌ | Não existe. |
| Piramidagem | ❌ | Uma entrada por posição (motor rejeita COMPRA com posição aberta). |
| Redução gradual de exposição em drawdown | ❌ | Bots pausam em `max_drawdown_pct`; não há redução gradual (livro 1, cap. 6 O3; livro 2, cap. 8 O2). |
| Limites por grupo de correlação | ⚠️ | Há `max_open_positions` e `max_total_exposure` globais; não há grupos correlacionados. |
| Custos por unidade | ✅ | Taxa percentual e slippage em bps sobre nocional, aplicados por execução. |

## 3. Oportunidades

### O1 — Resumo de robustez de varredura de um parâmetro: proporção rentável e estabilidade do melhor N *(livro: C5, pp. 225–227)*

* **Problema:** varredura de `entry_period` costuma ser lida como “escolher o melhor N”, embora o livro mostre instabilidade (75, 15 e 100 no mesmo mercado; 10 a 95 entre mercados).
* **Proposta:** para varredura de um parâmetro, apresentar (a) proporção de valores com retorno líquido positivo após custos; (b) melhor valor em cada subperíodo (metade inicial/final) e **correlação de postos** entre curvas de lucro; (c) suavidade (diferença de cada célula para vizinhas). Sinalizar “platô estável” versus “pico isolado”. Amplia robustez de vizinhança (livro 3, cap. 6; livro 1, cap. 3 C10). **Complexidade:** baixa a média. **Riscos:** amostras pequenas, mais segmentação/testes múltiplos e nenhuma garantia. **Validação:** curvas sintéticas em platô e pico.

### O2 — Dimensionamento de risco atento ao canal para Donchian *(livro: C2, C3, C9, pp. 222–224, 230–231)*

* **Problema:** risco por operação é distância até mínima do canal de saída, muito variável; o livro destaca risco constante como correção principal e Turtles usam `1 unidade = 1% / (ATR × valor)`.
* **Proposta:** permitir que estratégia proponha **stop inicial na mínima do canal de saída** (ou `k × ATR` abaixo da entrada) como proteção no sinal. `assess_signal` então dimensiona para que stop corresponda a fração fixa do patrimônio (mecanismo já existe, mas só opera quando sinal inclui stop). Oferecer stop por ATR. Reutiliza dimensionamento em produção; backtester não o utiliza (livro 1, cap. 5 O2).
* **Benefício:** risco constante por operação e menor domínio dos períodos voláteis. **Complexidade:** baixa a média (auxiliar ATR, alteração do sinal, parâmetro e formulário). **Riscos:** stop na mínima do canal é nível em que a regra já sairia; só importa em lacunas/movimentos intrabar e no dimensionamento. Stop real visível na corretora. Interage com dimensionamento all-in do backtest (livro 1, cap. 5 O2). **Validação:** testes de tamanho `risco% × patrimônio / (entrada − stop)` e backtest com modo de risco.

### O3 — N adaptativo à volatilidade como opção *(livro: C4, pp. 224–225)*

Definir `N_t = N_I × V_n / V_c` com janelas explícitas `V_n` e `V_c`. Retomado nas técnicas adaptativas do cap. 17; não implementar antes de O1 mostrar se N adaptativo é mais estável que N fixo. **Complexidade:** baixa a média; acrescenta parâmetros. Hipótese **H-ADAPTIVE-N**.

### O4 — Filtro “após vencedor” como experimento *(livro: C9, p. 230)*

Filtro Turtle S1 (pular entrada seguinte se a última operação foi lucrativa) é regra documentada com justificativa econômica (não reentrar logo após rompimento bem-sucedido). Testar como parâmetro booleano no fluxo, sem expectativa de sucesso. Hipótese **H-TURTLE-FILTER**. **Complexidade:** baixa (estado na estratégia).

### O5 — Piramidagem e redução gradual por drawdown: backlog *(livro: C9, pp. 230–231)*

Ambas exigem várias unidades simultâneas (B-TRANCHES/B-SCALE-IN, livro 2, caps. 3 e 6) e relacionam-se ao livro 1, cap. 6 O3. Registrar **B-PYRAMID**. Regra de carteira Turtle (reduzir 20% por drawdown de 10%, recompor 10% por etapa de recuperação) é exemplo concreto de redução gradual, a avaliar no livro 1, cap. 6 O3. **Complexidade:** média a alta.

### O6 — Mostrar retorno por unidade e cobertura dos custos *(livro: C8, p. 229)*

Apresentar lucro líquido médio por operação em **pontos-base do nocional** e razão para custo de ida e volta, permitindo avaliar se custos são cobertos com folga. Integra métricas (cap. 2 O1). **Complexidade:** muito baixa.

### Não aplicável

Gráfico ponto-e-figura (não lido), detalhes da construção de swing, regra semanal de sexta (cripto não fecha no fim de semana; intervalo semanal poderia ser testado, mas não consta em `Timeframe`) e rolagem de futuros.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O6 bps por operação versus custo | média | – | – | muito baixa | métricas |
| 2 | O1 resumo de robustez da varredura | **alta** | – | – | baixa–média | varreduras |
| 3 | O2 stop ATR/canal + dimensionamento | – | **alta** | – | baixa–média | auxiliar ATR; livro 1, cap. 5 O2 |
| 4 | O4 experimento filtro Turtle | baixa | – | – | baixa | fluxo de validação |
| 5 | O3 N adaptativo | baixa | – | – | baixa–média | O1 |
| 6 | O5 piramidagem/escala em drawdown | – | média | – | média–alta | modelo de posição |

## 5. Arquivos afetados

`strategies/domain/donchian_breakout.py` (proposta de stop/filtro), novo auxiliar ATR, `risk_management/domain/models.py` (já suporta dimensionamento por risco), `backtesting/application/service.py` (resumo de robustez), `analytics/domain/`, formulários de varredura/estratégia no app e testes (truncamento de cada regra nova).

## 6. Plano incremental

1. Métrica de cobertura de custos.
2. Resumo de robustez da varredura.
3. Auxiliar ATR; stop opcional Donchian; testes de dimensionamento.
4. Experimentos de filtro e N adaptativo pelo fluxo de validação.

## 7. Critérios de aceitação e testes

* Resumo de robustez reproduz casos sintéticos conhecidos de platô/pico.
* Stop respeita validações do módulo (`stop-loss must be below the entry price`) e não altera comportamento padrão.
* Ruff, mypy e testes existentes passam.

## Ressalvas

Todos os números (melhores N, proporções de testes rentáveis, desempenho Turtle) vêm de testes de futuros sem custos e são em grande parte ilustrações, como observa o autor. Curvas acumuladas de um mercado (cobre) não provam padrão geral. Nada indica que rompimentos funcionem em cripto à vista.
