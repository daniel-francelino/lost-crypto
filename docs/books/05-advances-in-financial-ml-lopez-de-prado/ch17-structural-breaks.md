# Livro 5 · Capítulo 17 — Quebras estruturais

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 249–254 foram lidas (motivação, taxonomia de testes, testes CUSUM, Dickey–Fuller tipo Chow, SADF, preços log versus brutos, custo computacional). Pp. 255–262 (testes sub/supermartingale, variantes SADF como QADF/CADF e exercícios) **não foram lidas**.

**Compatibilidade com a plataforma:** detecção de regimes/quebras como *diagnóstico* e atributo de filtro. Computacionalmente caro (SADF exige O(n²) regressões) e estatisticamente delicado; útil sobretudo em dados diários.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | **Quebras estruturais** (ex.: padrão de reversão à média dá lugar a momentum) surpreendem a maioria dos participantes; perdas (stops após manter posição esperando) são origem de algumas melhores relações risco/recompensa. Portanto, medir *probabilidade* de quebra e criar atributos sobre ela. | 249 |
| C2 | Duas famílias de teste: **CUSUM** (erros recursivos de previsão desviam de ruído branco?) e **explosividade** (processo mostra crescimento/colapso exponencial, incompatível com passeio aleatório/estacionariedade e insustentável?): testes de raiz unitária pela cauda direita e testes sub/supermartingale. | 249–250 |
| C3 | **CUSUM Brown–Durbin–Evans** em resíduos de mínimos quadrados recursivos (exige atributos `x_t`; início arbitrário produz resultados inconsistentes). **CUSUM de Chu–Stinchcombe–White sobre níveis** (Homm–Breitung): `S_{n,t} = (y_t − y_n)/(σ̂_t √(t − n))`, `σ̂²_t = (t−1)⁻¹ Σ (Δy_i)²`, sob `H₀: β_t = 0` ~ N(0,1); valor crítico unilateral dependente do tempo com `b_{0.05}=4.6` (via Monte Carlo). Nível de referência `y_n` arbitrário, então usar supremo sobre janelas retrospectivas `S_t = sup_{n∈[1,t]} S_{n,t}`. | 250–251 |
| C4 | **Explosividade**: testes de múltiplas bolhas são mais robustos, pois ciclo bolha–estouro–bolha parece estacionário em teste de bolha única (bolhas incluem vendas em pânico). **Dickey–Fuller tipo Chow** (passeio aleatório muda para explosivo numa data desconhecida; testar datas dentro de intervalo aparado — Andrews; pressupõe uma quebra e bolha até fim da amostra). **ADF de supremo (SADF, Phillips–Wu–Yu)**: para cada extremo `t`, regressões ADF em todos os inícios `t₀ ∈ [1,t−τ]` e usar supremo das estatísticas; não pressupõe número de regimes; série SADF tem picos em comportamento de bolha e volta a níveis baixos após estouro (fig. 17.1, E-mini S&P 500). | 251–253 |
| C5 | Usar **preços logarítmicos** em SADF/ADF: em preços brutos, rejeitar raiz unitária implica variância finita dos preços e, assim, volatilidade de retorno decrescente quando preços sobem (heterocedasticidade estrutural). Em log-preços, escala `x=k·y` desloca nível por constante, relevante entre décadas/bolhas. | 253–254 |
| C6 | **Custo computacional**: laço aninhado é Θ(n²); para 356.631 barras de dólar do E-mini S&P com 3 regressores, uma atualização SADF exige ~2,035 TFLOPs e série completa ~242 PFLOPs; nessa escala precisa paralelização HPC (cap. 20). | 254 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Detecção de regime/quebra | ❌ | Nenhuma; estratégias operam continuamente. |
| Filtro CUSUM (evento) | ❌ | Proposto no cap. 2 O3. |
| ADF/raiz unitária | ❌ | Proposto no cap. 5 O1. |
| Detecção de deterioração de desempenho | ❌ | Livro 4 cap. 21 O9 e cap. 23 O8 propõem monitores. |

## 3. Oportunidades

### O1 — Estatística de quebra CUSUM em níveis como diagnóstico barato *(livro: C3, p. 251)*

Implementar estatística Chu–Stinchcombe–White `S_t = sup_n S_{n,t}` sobre log-preços (limitar janelas a lookback máximo para ficar O(n·L)), mais limite baseado em `b=4.6` (confirmar fórmula exata do limite temporal no livro/artigo antes de uso — extração ilegível); mostrar no gráfico como faixa de “probabilidade de quebra”. Somente pesquisa: sinal de quebra precede mudança de taxa de acerto de estratégia de tendência? **Complexidade:** baixa–média. **Riscos:** muitos falsos alarmes em cripto volátil; janela arbitrária. **Validação:** passeio aleatório raramente ultrapassa limite; mudança de tendência inserida aciona; determinístico.

### O2 — Indicador explosivo tipo SADF em log-preços diários (atributo de pesquisa) *(livro: C4, C5, pp. 252–254)*

Calcular SADF em log-preços diários de ativos importados, com subconjunto espaçado de pontos iniciais e janela máxima para limitar custo, exigindo ADF (cap. 5 O1). Usar como **atributo de regime**: valores altos = alta semelhante a bolha (estratégias de tendência prosperam e sofrem no colapso); testar em backtest se condicionar entradas/tamanho melhora retorno ajustado (**H-SADF-REGIME**). **Custo:** com dados diários (milhares de pontos), versão espaçada é barata; intradiário, não (C6). **Complexidade:** média–alta. **Riscos:** baixo poder, sensibilidade ao lookback, look-ahead se supremo não for causal (calcular apenas com dados até `t`); regressões com janelas sobrepostas são dependentes. **Validação:** detectar segmento AR(1) explosivo em série sintética; passeio aleatório apresenta valores baixos; teste de truncamento.

### O3 — Gatilho de quebra para revalidar/treinar novamente *(livro: C1, p. 249 · conexão com livro 4 caps. 21 O9, 23 O8)*

Tratar quebra detectada na dinâmica do ativo (ex.: mudança de regime de volatilidade realizada, CUSUM excedido) como gatilho para rever ficha de expectativas da estratégia e, no ciclo de vida (cap. 1 O1), sinalizar “validade da evidência anterior em dúvida”. **Complexidade:** baixa–média após O1. Apenas notificar; nunca parar automaticamente.

### Não aplicável

Teste Brown–Durbin–Evans (exige modelo de atributos), teste tipo Chow com quebra única presumida, testes sub/supermartingale (não lidos), HPC para SADF completo em barras de dólar.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Diagnóstico CUSUM em níveis O1 | baixa–média | baixa | – | baixa–média | — |
| 2 | Gatilho de revalidação O3 | – | média | média | baixa–média | alertas, O1 |
| 3 | Atributo de regime SADF O2 | média | – | – | média–alta | ADF (cap. 5 O1) |

## 5. Arquivos afetados

`analytics/domain/` (estatísticas de quebra, ADF), endpoint/página de diagnósticos, testes.

## 6. Plano incremental

O1 primeiro; O2 somente se O1 demonstrar valor informativo; integrar a monitores do ciclo de vida depois.

## 7. Critérios de aceitação e testes

Estatísticas reproduzem comportamento conhecido em passeios aleatórios, mudanças de nível e segmentos explosivos simulados; causalidade estrita (teste de truncamento); tempo de execução limitado por janela/passos configurados; ruff, mypy e testes existentes aprovados.

## Ressalvas

Testes de quebra têm baixo poder e muitos falsos alarmes; limites vêm de simulações com incrementos gaussianos IID ideais. Páginas lidas não demonstram que condicionar estratégias nessas estatísticas melhora resultados (“algumas melhores relações risco/recompensa” é afirmado). SADF tem custo proibitivo em barras de alta frequência. Pp. 255–262 não foram lidas.
