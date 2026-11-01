# Livro 5 · Capítulo 14 — Estatísticas de backtest

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 195–207 e início da atribuição (p. 207) foram lidas. Pp. 208–210 (restante de atribuição, exercícios, referências) não foram lidas. Algumas fórmulas ficaram corrompidas na extração (notadamente PSR/DSR); são reapresentadas a partir de fragmentos visíveis e definições publicadas padrão (Bailey & López de Prado, 2012, 2014). A forma abaixo foi **conferida com a estrutura visível das fórmulas das pp. 203–204**, mas deve ser revisada no livro antes de implementação.

**Relevância:** capítulo central para métricas e pipeline de evidências: Sharpe probabilístico, Sharpe deflacionado, apostas versus operações, concentração de retornos, drawdown/tempo submerso, métricas de shortfall de execução e “Terceira Lei do Backtesting”.

## 1. Resumo do capítulo

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Sete famílias de estatísticas de backtest: características gerais, desempenho, sequências/drawdowns, shortfall de execução, eficiência retorno/risco, pontuação de classificação e atribuição. Relatar métricas usadas por investidores para comparar; métricas devem revelar risco assimétrico ou capacidade baixa. | 195 |
| C2 | **Características gerais**: intervalo temporal (teste precisa abranger regimes suficientes), AUM médio, capacidade (AUM mínimo para dimensionar/diversificar; desempenho cai conforme AUM aumenta), alavancagem (com custos), **tamanho máximo em dólares da posição** (preferir estratégia cujo máximo se aproxima do AUM médio, sem depender de eventos extremos), razão de posições compradas (long-short ideal ≈ 0,5), **frequência de apostas**: **aposta** = sequência de posições no mesmo lado (termina ao zerar ou inverter), então apostas ≤ operações; “contar operações superestima oportunidades independentes”; **permanência média** ponderada, **giro anualizado** (valor negociado por ano ÷ AUM médio; pode ser alto mesmo com poucas apostas se posição é ajustada constantemente), **correlação com universo subjacente** (correlação significativa pode indicar apenas manter/vender o universo). | 196–197 |
| C3 | **Desempenho**: PnL, PnL comprado, taxa de retorno anualizada, taxa de acerto, retorno médio de ganhos/perdas; **retorno ponderado pelo tempo (TWRR)** segundo GIPS, encadeado geometricamente e ajustado a fluxos externos de caixa. | 198–199 |
| C4 | **Sequências**: retornos raramente são IID; sequências contínuas de mesmo sinal elevam risco de queda. **Concentração de retornos** por índice tipo Herfindahl-Hirschman: `h⁺ = (Σ (w_t⁺)² − 1/n)/(1 − 1/n)` sobre pesos de apostas positivas (0 = uniforme, 1 = um retorno representa tudo); também `h⁻` para retornos negativos e concentração de apostas por mês. **Drawdown (DD)** = perda entre máximas sucessivas do patrimônio; **tempo submerso (TuW)** = tempo da máxima até PnL superá-la novamente. Estatísticas: HHI de retornos positivos, negativos e apostas mensais; percentis 95 de drawdown e TuW. | 199–202 |
| C5 | **Shortfall de execução**: taxas de corretagem por giro, **slippage por giro**, desempenho monetário por giro, retorno sobre custos de execução (desempenho ÷ custos totais — “deve ser múltiplo grande” para sobreviver execução pior que esperada; também múltiplo de custo no qual estratégia empata). | 202–203 |
| C6 | **Sharpe** `SR = μ/σ` (retornos excedentes gaussianos IID); erro de estimação substancial. **Sharpe probabilístico**: `PSR[SR*] = Z[ (SR̂ − SR*)·sqrt(T−1) / sqrt(1 − γ̂₃·SR̂ + ((γ̂₄ − 1)/4)·SR̂²) ]`, com `T` número de retornos, `γ̂₃` assimetria, `γ̂₄` curtose (3 para gaussiana), `SR̂` Sharpe observado não anualizado. PSR aumenta com SR̂, histórico mais longo e assimetria positiva; diminui com caudas pesadas. **Sharpe deflacionado**: `DSR = PSR[SR*]`, onde referência `SR*` é Sharpe máximo esperado entre N tentativas independentes sob nulo: `SR* = sqrt(V[{SR̂_n}])·((1−γ)·Z⁻¹[1 − 1/N] + γ·Z⁻¹[1 − 1/(N e)])`, γ ≈ 0,5772 (Euler–Mascheroni), V = variância dos Sharpes estimados entre tentativas. Máximo esperado é positivo mesmo se SR real = 0, cresce rápido com N e variância entre tentativas. **Terceira Lei do Backtesting de Marcos**: “todo resultado de backtest deve ser relatado junto com todas as tentativas envolvidas em sua produção. Sem isso, é impossível avaliar a probabilidade de falsa descoberta”. | 203–205 |
| C7 | **Estatísticas de eficiência**: Sharpe anualizado `SR·sqrt(a)` (a = observações/ano; pressupõe IID), índice de informação (retorno excedente ao benchmark ÷ erro de aderência), PSR e DSR (deve superar 0,95 para significância de 5%). | 205–206 |
| C8 | **Pontuação de classificação** para camada de meta-rotulagem: acurácia, precisão, recall, F1 (média harmônica), log-loss negativo. Tabela 14.1 lista quatro casos degenerados (observado sempre 1/0, previsto sempre 1/0) em que precisão/recall/F1 são indefinidos ou equivalem; scikit-learn define F1 = 0 com aviso. | 206–207 |
| C9 | **Atribuição**: decompor PnL por classe de risco (duração, crédito, liquidez, setor, moeda…); riscos não são ortogonais (restante não lido). | 207 |

## 2. Diagnóstico (verificado no código)

| Métrica | Status | Evidência/observações |
|---|---|---|
| PnL líquido, retorno, buy-and-hold, drawdown máximo, taxas, taxa de acerto, fator de lucro, operação média | ✅ | `analytics/domain/metrics.py`. |
| Sharpe/Sortino/Calmar, anualização | ❌ | Não existem (planejados no livro 4, cap. 23 O1). |
| PSR/DSR | ❌ | — |
| Assimetria/curtose de retornos | ❌ | — |
| Número de apostas versus operações | ≈ | Uma posição por vez e comprado: operações ≈ apostas (cada ida-e-volta é uma aposta). |
| Permanência média/giro | ⚠️ | Duração pode ser derivada das operações (verificar se informada); giro não informado. |
| Tempo submerso/percentis de drawdown | ❌ | Só drawdown máximo. |
| Concentração HHI de retornos | ❌ | — |
| Correlação com subjacente | ❌ | Informa retorno buy-and-hold, não correlação. |
| Métricas de shortfall de execução | ⚠️ | Taxas/slippage totais contabilizados; razões (desempenho ÷ custos, múltiplo de equilíbrio) não. |
| Pontuação de classificação | ❌ | Sem classificadores. |
| Atribuição | ❌ | — |
| Contagem de tentativas para deflação | ❌ | Ver cap. 11 O1. |

## 3. Oportunidades

### O1 — Adicionar PSR e DSR aos resultados de backtest/varredura *(livro: C6, C7, pp. 203–206)*

* **Proposta:** calcular retornos por período (ex.: diários) da curva de patrimônio e então Sharpe observado não anualizado `SR̂`, assimetria, curtose, `T`, **PSR contra Sharpe de referência (padrão 0)** e, para varreduras/backtest com N tentativas no registro (cap. 11 O1), **DSR** usando N = tentativas independentes e V = variância empírica dos Sharpes. Mostrar: “Probabilidade de Sharpe real > 0: PSR 0,82; após deflação por 200 tentativas: DSR 0,31”, com explicação, limiar (≥ 0,95) e alertas (T pequeno, caudas pesadas, não IID).
* **Motivo:** converte “melhor de N” em probabilidade, contrapondo viés de seleção da varredura; precisa apenas retornos e contagem. Com PBO (cap. 11), forma painel mínimo de credibilidade.
* **Nuances:** (a) frequência de retorno consistente (retornos diários em estratégia de barras 1h fornecem menos observações; fórmula usa Sharpe não anualizado na frequência amostral); (b) tentativas “independentes”: parâmetros vizinhos são correlacionados, então N efetivo menor que execuções (livro não fornece estimador; opções: agrupar por correlação de retorno, famílias × platôs distintos ou mostrar sensibilidade a vários N); (c) autocorrelação viola IID: mostrar sensibilidade Newey–West/blocos; (d) curva de patrimônio parada por longos períodos tem muitos retornos zero, reduz σ medida e infla SR (livro 4, cap. 24); informar também SR sobre **retornos por aposta** e períodos ativos.
* **Complexidade:** baixa–média (fórmulas, CDF normal inversa, registro). **Validação:** referências em fixtures (ruído branco → PSR ≈ 0,5 com SR*=0; DSR cai com N; N→1 implica DSR→PSR); propriedades de simetria.

### O2 — Pacote ampliado de estatísticas (gerais, sequências e shortfall) *(livro: C2, C4, C5, pp. 196–203)*

Adicionar às métricas: **apostas versus operações** (definições explícitas), **permanência média**, **giro anualizado**, **tempo no mercado**, **correlação com retornos do subjacente**, **HHI de concentração de retornos positivos/negativos e mensais**, **série de drawdown, tempo submerso, percentis 95 de DD/TuW** e razões de shortfall (**desempenho ÷ custos totais**, **múltiplo de equilíbrio**, **slippage por giro**). Sobrepõe-se ao livro 4, cap. 21 O7 e cap. 23 O1: definir cada métrica uma única vez, com referência. **Complexidade:** baixa–média. **Validação:** fixtures fechadas; HHI entre 0–1 (uniforme=0, único retorno=1); TuW coerente com patrimônio; métricas invariantes à escala constante.

### O3 — Relatar resultados junto com tentativas (Terceira Lei) como regra do produto *(livro: C6, p. 205)*

Toda métrica de desempenho exibida para configuração escolhida em busca deve vir com: tentativas brutas/efetivas, intervalo de dados, famílias de estratégia avaliadas e se segmento de avaliação estava bloqueado. Sem esses dados, interface marca “não verificado: viés de seleção desconhecido”. **Complexidade:** baixa–média (depende do registro). **Validação:** resultado sem registro recebe aviso.

### O4 — Plausibilidade de capacidade e tamanho para conta spot *(livro: C2, p. 196)*

Informar indícios de **capacidade**: notional médio/máximo versus volume médio diário cotado do par (taxa de participação) e alertar quando capital configurado ultrapassar pequena fração (ex.: 1% do volume por candle, livro 4 cap. 20 O5). Para varejo raramente limita, mas documenta. **Complexidade:** baixa.

### O5 — Pontuações de classificação para filtros/modelo meta, tratando casos degenerados *(livro: C8, pp. 206–207)*

Implementar acurácia/precisão/recall/F1/log-loss e casos degenerados explicitamente (retornar None/NaN com explicação, não zero) na avaliação de filtros (cap. 3 O4). **Complexidade:** baixa. **Validação:** casos da Tabela 14.1.

### O6 — Retorno ponderado pelo tempo com depósitos/saques (somente se houver fluxos de capital) *(livro: C3, pp. 198–199)*

Bots usam capital fixo, sem fluxos externos. Se houver saques/aportes, usar TWRR (encadeamento geométrico de retornos subperíodo), não razão simples de PnL. **Complexidade:** nenhuma agora.

### Não aplicável

Relatórios de conformidade GIPS, preço sujo/accrued interest de títulos em TWRR, proporções long-short, atribuição por classe de risco (um ativo spot comprado).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | PSR/DSR O1 | muito alta | – | – | baixa–média | registro (cap. 11 O1) para DSR |
| 2 | Estatísticas ampliadas O2 | alta | alta | – | baixa–média | série patrimonial |
| 3 | Resultados acompanhados de tentativas O3 | muito alta | – | – | baixa–média | registro |
| 4 | Pontuações de classificação O5 | média | – | – | baixa | cap. 3 O1/O4 |
| 5 | Indício de capacidade O4 | baixa | baixa | – | baixa | dados de volume |
| 6 | TWRR O6 | – | – | – | – | desnecessário |

## 5. Arquivos afetados

`analytics/domain/metrics.py` (novas métricas: série de retornos, SR, assimetria, curtose, PSR, DSR, HHI, TuW), helper CDF/CDF inversa normal (usar `statistics.NormalDist` da biblioteca padrão se precisão bastar), esquema de resultado e `docs/openapi.json`, páginas de resultado do app, testes de referência.

## 6. Plano incremental

1. Série de retornos e estatísticas básicas (SR, assimetria, curtose) com testes unitários.
2. PSR; depois DSR com contagem do registro e tabela de sensibilidade.
3. Estatísticas ampliadas (sequências, shortfall, giro).
4. “Painel de credibilidade” na interface: aviso da Terceira Lei + PSR, DSR, PBO.

## 7. Critérios de aceitação e testes

* PSR: `SR̂ = 0`, `SR* = 0` → 0,5; cresce monotonicamente em `SR̂` e T; cai com curtose; DSR ≤ PSR(0) para N>1 e decresce com N; corresponde a exemplos publicados (verificar nos artigos originais antes de publicar).
* Estatísticas determinísticas, invariantes à escala quando apropriado e documentadas com fórmulas/referências.
* ruff, mypy e testes existentes aprovados.

## Ressalvas

PSR/DSR presumem retornos IID com assimetria/curtose estimadas, tentativas independentes e nulo de habilidade zero; retornos cripto são heterocedásticos e por vezes autocorrelacionados, enquanto tentativas são muito dependentes. Assim, DSR com N = execuções é conservador; com N=1, otimista. DSR exige variância dos Sharpes na mesma frequência de retorno. Antes de implementar, validar fórmulas com artigos primários (Bailey & López de Prado, 2012, 2014), pois extração PDF é imperfeita. Pp. 208–210 não foram lidas.
