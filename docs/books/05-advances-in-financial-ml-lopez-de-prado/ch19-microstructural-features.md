# Livro 5 · Capítulo 19 — Atributos de microestrutura

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 281–286 foram lidas (motivação, revisão da literatura, regra do tick, modelo Roll, volatilidade máxima-mínima, Corwin–Schultz). Segunda geração (lambda de Kyle, Amihud, Hasbrouck, pp. 286–290), terceira geração (PIN/VPIN, pp. 290–293) e atributos adicionais (293–296) foram vistos somente pelos títulos/primeiras frases e **não são resumidos em detalhe**.

**Compatibilidade com a plataforma:** plataforma tem candles OHLCV, sem negócios nem livro de ordens. Só são práticos atributos calculáveis de OHLCV: **spread Corwin–Schultz**, **volatilidade máxima-mínima Parkinson/Beckers** e (pelos títulos) **iliquidez tipo Amihud**. Atributos de fluxo (regra do tick, VPIN, lambda Kyle/Hasbrouck, cancelamentos) exigem dados de negócios/livro.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Dados de microestrutura (mensagens FIX: cancelamentos, filas, execuções parciais, lado agressor) estão entre os ingredientes mais importantes para atributos preditivos de ML. Três gerações: (1) modelos de sequência de preços (regra do tick, Roll 1984), (2) modelos de volume/negociação estratégica (Kyle 1985, Amihud 2002), (3) modelos de sequência de negócios (PIN, Easley et al. 1996; VPIN com amostragem por volume), nos quais spread bid-ask é prêmio cobrado pelo formador de mercado por seleção adversa. | 281–282 |
| C2 | **Regra do tick**: lado agressor `b_t = sign(Δp_t)`, ou `b_{t−1}` se preço não muda; alta precisão apesar da simplicidade; transformações de `{b_t}` geram atributos (expectativa filtrada por Kalman, quebras estruturais, entropia, t-values de somas acumuladas, diferenciação fracionária). | 282 |
| C3 | **Modelo Roll**: preço observado = preço médio ± metade do spread `c` com lado agressor aleatório; implica `c = sqrt(max{0, −cov[Δp_t, Δp_{t−1}]})` e `σ²_u = σ²[Δp] + 2 cov[Δp_t, Δp_{t−1}]`; útil para instrumentos com poucas cotações. Pressupostos (sem deriva, homocedástico, sinais serialmente independentes) são contraditos empiricamente, mas plausíveis com amostragem adequada (cap. 2). | 282–283 |
| C4 | **Volatilidade máxima-mínima** (Parkinson 1980; Beckers 1983): `E[(1/T) Σ log²(H_t/L_t)] = k₁σ²_{HL}`, `k₁ = 4 log 2`; `E[(1/T) Σ log(H_t/L_t)] = k₂σ_{HL}`, `k₂ = sqrt(8/π)`; mais precisa que volatilidade entre fechamentos. | 283–284 |
| C5 | **Estimador de spread bid-ask de Corwin–Schultz (2012) via máxima e mínima**: máximas cruzam sobretudo oferta e mínimas demanda; componente de volatilidade da razão max/min cresce com tempo, componente spread não. Com `β_t = E[Σ_{j=0..1} log²(H_{t−j}/L_{t−j})]` (amplitudes de barras individuais em 2 barras), `γ_t = log²(H_{t−1,t}/L_{t−1,t})` (amplitude de 2 barras), `α_t = (√(2β_t) − √β_t)/(3 − 2√2) − √(γ_t/(3 − 2√2))`, spread `S_t = 2(e^{α_t} − 1)/(1 + e^{α_t})`; zerar α negativo (recomendação dos autores); estimativa móvel sobre comprimento `sl` pode ser suavizada por filtro Kalman; volatilidade estimada é subproduto. | 284–286 |
| C6 | Segunda geração foca **iliquidez** (risco precificado) por regressões sobre volume com sinal (lambda Kyle, Amihud, Hasbrouck); terceira, probabilidade de negociação informada (PIN, VPIN) — somente títulos. | 286–293 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Candles OHLCV com volume | ✅ | `Candle` (volume não usado pelas estratégias). |
| Negócios/lado agressor/livro de ordens | ❌ | Não importados (Binance oferece `aggTrades` com `isBuyerMaker` e snapshots/streams de profundidade). |
| Estimativa de spread por candles | ❌ | `slippage_bps` fixo. |
| Medidas de iliquidez | ❌ | Nenhuma. |

## 3. Oportunidades

### O1 — Volatilidade máxima-mínima (Parkinson) e spread Corwin–Schultz como diagnósticos de candle *(livro: C4, C5, pp. 283–286)*

* **Proposta:** implementar ambos estimadores sobre candles; spread móvel (janela 20–100), média em bps por ativo/timeframe e perfil por hora; comparar ao `slippage_bps` assumido (verificação baseada em dados do modelo de custos: spread estimado aproxima metade/total do spread efetivo, não impacto de mercado para tamanho de ordem); volatilidade Parkinson como alternativa a ATR/fechamento (livro 4 cap. 20 O1).
* **Motivo:** ancora custos em dados sem fonte nova e identifica períodos ilíquidos. Para pares spot Binance líquidos, spread estimado será mínimo e provavelmente dominado pelo cotado da corretora (1–2 bps nos principais); uso principal em pares menos líquidos/períodos de estresse. **Complexidade:** baixa. **Riscos:** pressupõe negociação contínua e preço Browniano; candles 1m de pares pouco líquidos geram valores ruidosos/zero (alfa negativa truncada); estima spread, não slippage pelo tamanho. **Validação:** verificações fechadas em preços simulados com spread/volatilidade conhecidos (abordagem de simulação Corwin–Schultz); não negatividade; conferir fórmulas no artigo antes de publicar (extração corrompeu constantes).

### O2 — Razão de iliquidez tipo Amihud `|r| / volume cotado` por candle/dia *(livro: título C6; fórmula não lida — definição do artigo original)*

Média móvel do retorno absoluto dividido pelo volume em dólares, como iliquidez grosseira (impacto de preço por dólar). Usar como filtro ou entrada de risco (pausar quando disparar), após validação dos dados. Ler p. 288 antes de implementar para seguir definição exata do livro. **Complexidade:** baixa. **H-ILLIQ-FILTER** somente pelo pipeline.

### O3 — Dados de negócios (lado agressor, desequilíbrio do fluxo, VPIN): registrar e adiar *(livro: C1, C2, C6; cap. 2 O2)*

Exige dados de negócios/profundidade e armazenamento; muitos atributos (regra do tick, desequilíbrio de volume assinado, autocorrelação do fluxo, VPIN) dependem disso. `aggTrades` Binance expõe flag agressora, então regra do tick é desnecessária. Decidir junto do trabalho com barras de dólar (cap. 2 O2). Livro diz que atributos microestruturais são “ingredientes mais importantes”; evidência nas páginas é teórica e da experiência do autor. **Complexidade:** alta.

### O4 — Usar spread/iliquidez para definir slippage por timeframe e horário *(livro: C5; conexão com livro 4 caps. 16 O2, 20 O5)*

Substituir `slippage_bps` constante por tabela por par e hora, calibrada com O1 e, depois, execuções registradas pela plataforma. **Complexidade:** média.

### Não aplicável

Aplicações BWIC em títulos, mercados de opções, marcas TWAP, cancelamentos (sem dados de ordens), detalhes de estimação PIN/VPIN.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Volatilidade Parkinson + Corwin–Schultz O1 | média | média | – | baixa | candles |
| 2 | Slippage por spread O4 | alta | média | – | média | O1; registros de execução |
| 3 | Razão Amihud O2 | baixa | baixa | – | baixa | leitura p. 288 |
| 4 | Dados no nível de negócio O3 | média–alta | – | – | alta | decisão |

## 5. Arquivos afetados

`analytics/domain/` (estimadores), página de diagnóstico, `execution/domain/fills.py` (tabela de custos, posteriormente), testes.

## 6. Plano incremental

Estimadores e diagnósticos; calibrar modelo de custo; adiar dados no nível de negócio.

## 7. Critérios de aceitação e testes

Estimadores recuperam spreads/volatilidades conhecidos em simulações; respeitam causalidade/truncamento; determinísticos; ruff, mypy e testes existentes aprovados.

## Ressalvas

Constantes/álgebra Corwin–Schultz foram reconstruídas de extração parcialmente corrompida e devem ser verificadas no artigo. Ambos estimadores são aproximações de baixa frequência. O capítulo não demonstra valor preditivo desses atributos para retornos. Pp. 286–296 foram consultadas superficialmente.
