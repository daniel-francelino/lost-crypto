# Livro 5 · Capítulo 13 — Backtesting com dados sintéticos

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 169–176 (motivação, regras de negociação, definição de sobreajuste, estrutura O-U, algoritmo de cinco etapas e código) e pp. 188–192 (conclusão/exercícios) foram lidas. Figuras de mapas de calor e descrições por combinação de parâmetros (176–188) foram vistas superficialmente: texto descreve movimento da região ótima com meia-vida/equilíbrio, sem tabela de números.

**Escopo:** apesar do título, capítulo trata de **calibrar regras de saída (take-profit e stop-loss) a partir de processo estocástico ajustado, usando Monte Carlo em vez de backtest histórico**. Não fornece gerador geral de mercados sintéticos para validar sinais de entrada.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Usar história para **estimar processo estocástico** e gerar muitos conjuntos sintéticos com mesmas características estatísticas, evitando ajustar estratégia a um caminho só. Foco: **regras de negociação** (táticas de entrada/saída): entrar quando sinal alcança valor; sair por limites de lucro e stop. Parâmetros calibrados por simulação histórica sobreajustam caminho dentro da amostra (“estratégia fica tão presa ao passado que se torna inadequada ao futuro”). | Sobreajuste das regras de saída. | 169–170 |
| C2 | **Formalização**: oportunidade i com posição `m_i`, PnL marcado a mercado `π_{i,t} = m_i(P_{i,t} − P_{i,0})`; regra `R = {π̲, π̄}` sai no primeiro entre take-profit `π̄` e stop `π̲` (mais permanência máxima = barreira vertical do cap. 3). Calibração força bruta maximiza `SR_R = E[π_{i,T_i}|R] / σ[π_{i,T_i}|R]` em regras candidatas `Ω`. Com duas variáveis livres numa amostra I, sobreajustar é trivial (par seleciona poucos outliers). **Regra sobreajustada**: regra ótima dentro da amostra deve ter desempenho abaixo da mediana das alternativas fora dela (mesma definição do PBO, cap. 11). | Definição do problema. | 170–172 |
| C3 | **Estrutura**: presumir preço da posição segundo processo discreto **Ornstein–Uhlenbeck (O-U)** `P_t = (1−φ)·E₀[P_T] + φ·P_{t−1} + σ·ε_t`, `ε ~ N(0,1)`; estacionário se `φ ∈ (−1, 1)`; `φ = 2^(−1/τ)`, τ meia-vida. Pergunta: é possível derivar par ótimo `(π̲, π̄)` de `{φ, σ}` e condições iniciais **sem simulação histórica**? | Modelo para posições de reversão à média. | 172 |
| C4 | **Algoritmo de cinco etapas**: (1) estimar `φ` e `σ` por OLS na equação linearizada (13.5); (2) montar grade de pares `(π̲, π̄)` (ex.: 20×20, múltiplos de σ de 0,5 a 10); (3) simular muitos caminhos (ex.: 100.000) por oportunidade com permanência máxima (ex.: 100); (4) aplicar cada regra a cada caminho e calcular Sharpe por ponto; (5) escolher par ótimo, stop ótimo dado alvo de lucro (5b) ou take-profit ótimo dado stop máximo (5c). Código (trechos 13.1–13.2) com `forecast ∈ {10, 5, 0, −5, −10}`, `half-life ∈ {5, 10, 25, 50, 100}`, `σ = 1`, `maxHP = 100`, `nIter = 1e5`. | Algoritmo. | 173–176 |
| C5 | **Resultados experimentais** (mapas de calor de Sharpe na grade lucro/stop): equilíbrio de longo prazo zero (semelhante a formador de mercado), positivo (tomador de posição; take-profit ótimo maior) e negativo (imagem espelhada). Com meia-vida maior, processo se aproxima do passeio aleatório, região de melhor desempenho se amplia e Sharpe cai (ex.: Sharpe ≈ 12 em previsão 5, meia-vida 5, numa figura); regra ótima depende de `{E₀[P_T], τ, σ}`. | Comportamento das regras ótimas. | 176–188 |
| C6 | **Conclusão/conjectura**: para preços O-U há **combinação única ótima** de take-profit e stop que maximiza Sharpe. Autor argumenta que probabilidade de conjectura ser falsa é insignificante frente à chance de sobreajuste por ignorá-la; “presuma que esteja correta e determine OTR com dados sintéticos; no pior caso será subótima, mas superará regra sobreajustada”. (Sem prova; argumento se apoia nos experimentos apresentados.) | Conclusão. | 192 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Stops/take-profit calibrados por varreduras históricas | ✅ | Stops/alvos são parâmetros de estratégia/risco; varreduras podem incluí-los (ressalva livro 4: valor do stop importa menos que regra de entrada). |
| Permanência máxima | ❌ | Não existe (cap. 3 O2). |
| Estimativa de parâmetros de reversão à média (meia-vida) | ❌ | Não existe (livro 2, cap. 2 aborda meia-vida; não implementada). |
| Gerador de caminhos sintéticos | ❌ | Há sementes para backtest determinístico, mas não gerador de preços sintéticos. |
| Avaliação de saída independente do caminho histórico | ❌ | — |

## 3. Oportunidades

### O1 — Ambiente de teste com caminhos sintéticos e modelos nulos para pipeline de evidências *(livro: C1, C4 · generalização, adaptação nossa)*

* **Proposta:** gerador determinístico de séries com propriedades controladas: (a) passeio aleatório gaussiano sem deriva (nulo); (b) passeio aleatório com agrupamento de volatilidade (GARCH/regimes); (c) processo O-U com meia-vida escolhida; (d) processo tendencial com deriva inserida. Parâmetros podem ser estimados de série real (média, volatilidade, autocorrelação, curtose). Usar para (i) testes unitários de estratégias e infraestrutura varredura/PBO (sem vantagem → sem significância; vantagem inserida → detectar) e (ii) **distribuição nula** do melhor resultado da varredura sem vantagem, mas com mesma volatilidade (permutação/bootstrap paramétrico do livro 3).
* **Motivo:** responde “qual seria o melhor entre N sem vantagem?” e valida estatísticas propostas (PBO, Sharpe deflacionado, CPCV). Algoritmo do livro serve de modelo (simular muitos caminhos do processo ajustado e avaliar cada regra).
* **Complexidade:** média (geradores, execução com semente, comparação); custo = caminhos × tamanho da varredura (reduzir com vetorização). **Riscos:** resultados dependem da especificação; nulo gaussiano subestima caudas pesadas/agrupamento, então usar também nulos de bootstrap/regime. **Validação:** geradores reproduzem momentos-alvo; mesma semente gera mesmo caminho; distribuição nula do Sharpe máximo cresce com N conforme fórmula do máximo esperado (cap. 14).

### O2 — Diagnósticos de reversão à média e meia-vida (informam saídas) *(livro: C3, C4 etapa 1, p. 173)*

Estimar `φ` por regressão OLS de `P_t − m` sobre `P_{t−1} − m` (coeficiente AR(1) dos desvios do equilíbrio/média móvel), derivar meia-vida `τ = −ln 2 / ln φ`, volatilidade `σ` e exibir nos diagnósticos da série (com intervalos de confiança e aviso de não estacionariedade quando `|φ| ≥ 1`). Sobrepõe-se a Chan (livro 2, cap. 2: meia-vida via regressão O-U); implementar uma vez. Necessário se houver estratégia de reversão à média. **Complexidade:** baixa. **Validação:** recuperar `φ` conhecido em O-U simulado.

### O3 — Grade de take-profit/stop avaliada em caminhos O-U simulados para reversão à média (somente se estratégia for criada) *(livro: C4, C5, pp. 173–188)*

Reproduzir grade do livro: para estratégia de reversão à média com `{φ, σ}` estimados, calcular mapa de Sharpe de `(stop, alvo)` (múltiplos de σ) em 10⁴–10⁵ caminhos simulados com permanência máxima; comparar mapa histórico e reportar sobreposição. Usar como prior, não verdade: preços spot cripto não são geralmente O-U (tendências, saltos); validar `φ` (ADF/meia-vida estáveis entre subperíodos) antes. Para estratégias **de tendência** atuais, procedimento inadequado, pois O-U contradiz a premissa. **Complexidade:** média, ligada a futura estratégia de reversão. **Riscos:** especificação errada (saltos, caudas pesadas, volatilidade agrupada) torna corredor ótimo apenas num mundo inexistente; apresentar como prior regularizador de saída. **Validação:** casos degenerados (φ=0: ruído IID ao redor do equilíbrio); previsões simétricas espelham-se (livro observa imagens espelhadas para ±forecast).

### O4 — Tratar conjectura do livro com cautela: não depender de um único par “ótimo” de saídas *(livro: C6, p. 192)*

Conjectura de ótimo único é empírica e limitada ao modelo O-U. Abordagem própria de platô/vizinhança (livro 4, cap. 21) e PBO são compatíveis como regularizadores, mas não se deve codificar corredor “ótimo” como certeza. Registrar: escolher saídas em platô dos mapas históricos e simulados; corredor deve sobreviver a custos/gaps. **Complexidade:** nenhuma.

### Não aplicável

Exercícios de trader-executor (cobrir venda com saídas especificadas), código estilo Python 2, exercício de multiprocessamento (cap. 20 do livro).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Ambiente de teste/nulo sintético O1 | muito alta | – | – | média | registro/PBO/DSR |
| 2 | Diagnóstico de meia-vida/reversão O2 | média | – | – | baixa | módulo analytics |
| 3 | Corredor de saídas simuladas O3 (somente reversão) | média | média | – | média | estratégia de reversão |
| 4 | Documentação O4 | baixa | – | – | doc. | – |

## 5. Arquivos afetados

`analytics/domain/` (geradores sintéticos, executor de distribuição nula, estimador de meia-vida), `backtesting/application` (executar estratégia em dados sintéticos com sementes armazenadas), testes, documentação; diagnósticos do app.

## 6. Plano incremental

1. Geradores de passeio aleatório e O-U com testes de momentos.
2. Distribuição nula do melhor de N numa varredura (validação PBO/DSR).
3. Diagnósticos de meia-vida; depois mapa de calor do corredor de saída.

## 7. Critérios de aceitação e testes

* Geradores: momentos amostrais dentro da tolerância; reproduzíveis por semente; meia-vida O-U recuperada por OLS dentro do intervalo de confiança.
* Distribuição nula: sem vantagem, média do melhor Sharpe entre N tentativas cresce com N; fração de resultados acima do limite de significância corresponde à taxa nominal após correção.
* ruff, mypy e testes existentes aprovados.

## Ressalvas

Resultados de “regra de negociação ótima” pressupõem processo O-U *conhecido*; preços reais divergem, portanto corredor depende do modelo. Conjectura não foi provada. Mapas são ilustrativos (combinações específicas), Sharpe depende de `σ` e limite de permanência; capítulo não testa estratégia real em dados reais. O título promete mais do que entrega: backtest geral com dados sintéticos para sinais de entrada não é tratado.
