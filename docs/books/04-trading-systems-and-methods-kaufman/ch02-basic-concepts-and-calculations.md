# Livro 4 · Capítulo 2 — Conceitos e cálculos básicos

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20; alguns símbolos se perderam no texto). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 25–55 e 58–61 foram lidas. Detalhes da construção de índices (pp. 55–58), restante da seção de probabilidade (pp. 62–66: sequências, esperança etc.) e “Oferta e procura” (pp. 66–78) **não** foram lidos em detalhe nem são resumidos.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Lei das médias** corretamente entendida: sequências anormais não precisam ser “compensadas”; eventos normais acabam prevalecendo. | Falácia do jogador. | 26 |
| C2 | **Dentro/fora da amostra**: todo teste sofre sobreajuste; reservar dados não vistos; **há uma única oportunidade**: se a avaliação fora da amostra falhar, encerra-se a tentativa. Alterar regras depois de consultar os dados contamina a amostra. Blocos alternados de dois anos podem ajudar em mercados mutáveis; reservar metade dos dados também reduz à metade os padrões disponíveis. | Validação honesta. | 27–28 |
| C3 | **Erro amostral ≈ 1/√N**: 1 observação → 100%; 4 → 50%; **400 operações → 5%**. Sistema lento com 2–3 operações anuais precisa aplicar o mesmo método em muitos mercados para alcançar N útil. | Quantas operações bastam. | 28–29 |
| C4 | **Dados representativos**: incluir pelo menos alta, baixa e lateralização (dez anos de alta fazem qualquer estratégia comprada parecer boa); mudanças estruturais (empresa/moeda) podem tornar o histórico antigo não representativo; amostras maiores ajudam a verificar adaptação; muitas operações diárias não cobrem condições variadas. | Cobertura dos dados. | 29 |
| C5 | **Médias**: aritmética, ponderada pelo tempo, geométrica (razões e variações percentuais), quadrática/RMS, harmônica, mediana e moda; cada uma se adequa a dados diferentes. | Escolher a média apropriada. | 30–37 |
| C6 | **Momentos**: média, variância/desvio-padrão, **assimetria** (preços tendem à assimetria positiva; lucros de sistemas de tendência com stops fixos têm assimetria à direita), **curtose** (excesso = K − 3). **Curtose de retornos diários acima de 7–8 pode indicar sobreajuste**: “quantidade excessiva de operações lucrativas de tamanho semelhante, algo improvável em negociação real”. Desvio-padrão pode enganar em dados assimétricos; distribuições de frequência/percentis são melhores. Retornos de negociação não são normalmente distribuídos. | Forma dos resultados. | 37–43 |
| C7 | **Autocorrelação** (persistência), por correlação defasada ou estatística Durbin–Watson d (2 = nenhuma). **Teste t de duas amostras** para consistência: comparar médias dos retornos líquidos de operações de dois períodos **não sobrepostos**, usando graus de liberdade de Satterthwaite. | Detectar persistência e estabilidade. | 43–48 |
| C8 | **Padronizar risco e retorno**: anualizar e comparar com **volatilidade-alvo** comum (livro usa 12%; escalar exposição pela razão volatilidade-alvo/realizada). Retorno simples `p₁/p₀ − 1` versus retorno `ln` (pequenas diferenças se acumulam); NAV começa em 100; retorno anual simples `AROR = (E_n/E₀−1)·252/n`, composto `(E_n/E₀)^(252/n)−1`; usar 252 dias de negociação. Anualizar desvio-padrão multiplicando pela **raiz quadrada** do número de observações por ano (em um trecho o texto diz “multiplicar por 252”, em contradição com a regra e parágrafo seguinte). | Comparar números. | 48–53 |
| C9 | **Dados mensais sempre parecem menos voláteis** que diários (S&P 1990–2010: 18,6% diária contra 15,3% mensal), ocultando drawdowns dentro do mês; diligência exige retornos diários. | Risco subestimado. | 53 |
| C10 | **Risco de queda**: semivariância/momentos parciais inferiores; risco por drawdown (perda líquida nos dias abaixo do pico patrimonial). | Risco relevante. | 53–54 |
| C11 | **Índices de desempenho**: índice de informação (retorno/risco), Sharpe (excesso sobre taxa livre de risco), Treynor (beta), **drawdown máximo** (queda percentual do pico de NAV até o menor NAV posterior; destaca grandes perdas), **Calmar** (retorno/drawdown máximo), **Sortino** (desvio de queda). Medidas simples costumam bastar e classificar candidatos de modo semelhante. Beta/alfa vêm de regressão contra índice; índice é benchmark (carteira 60/40 ações/títulos). | Ordenar sistemas. | 52, 58–59 |
| C12 | Noções de **probabilidade**: regras de adição e multiplicação, probabilidade conjunta, marginal e condicional (sequências de alta/baixa em dois dias). | Raciocínio condicional. | 59–61 |

Exemplos referem-se a futuros e índices de ações. Aplicações em cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Uma única avaliação fora da amostra | ❌ | Segmento de teste pode ser consultado repetidamente (livro 3, caps. 6 e 9 O2). |
| Tamanho da amostra/erro conforme operações | ⚠️ | Exibe `round_trips`, mas não alerta em relação a 1/√N ou meta (livro 1, cap. 3 O6; livro 3, cap. 4 O5). |
| Cobertura representativa de regimes | ❌ | Não verifica se janela inclui alta, baixa e lateralização; estratégia comprada testada em alta não recebe aviso. |
| Assimetria/curtose/percentis de resultados | ❌ | `Metrics` não tem essas métricas nem distribuição dos retornos por operação/barra. |
| Alerta por curtose | ❌ | Não existe. |
| Autocorrelação/Durbin–Watson | ❌ | Não existem (também livro 2, cap. 6 O1). |
| Teste t entre períodos (treino/teste) | ❌ | Métricas aparecem lado a lado sem teste de diferença. |
| Normalização por volatilidade-alvo | ❌ | Retornos absolutos; comparação entre par volátil e calmo não normalizada. |
| Convenções de retorno | ⚠️ | Retorno baseado no patrimônio em `Decimal`; não documenta simples versus logarítmico (livro 3, cap. 1 O4). |
| Volatilidade diária versus mensal | n/a | Métricas ainda não usam volatilidade. |
| Risco de queda/Sortino/Calmar/estatísticas de drawdown | ❌ | Só `max_drawdown_pct` (livro 1, cap. 2). |
| Definição de drawdown máximo | ✅ | `max_drawdown_pct` é a queda percentual desde o pico acumulado, como definido. |

## 3. Oportunidades

### O1 — Ampliar conjunto de métricas conforme o capítulo *(livro: C6, C8, C10, C11, pp. 38–59)*

Acrescentar ao módulo: Sortino (desvio de queda), **Calmar** (retorno anualizado/drawdown máximo), assimetria e curtose excedente dos retornos por barra e por operação, percentis dos retornos de operação e desvio-padrão calculado **com retornos na frequência da barra da estratégia**, anualizado por `√(barras por ano)` (convenção do livro 1, cap. 3 O1, ajustada a mercados 24/7). Informar tamanho da amostra em cada métrica.

**Benefício:** completar visão de desempenho com risco ajustado e de queda. **Complexidade:** baixa a média (funções puras em `Decimal`, fronteira float documentada para `sqrt`). **Riscos:** cada índice adicional estimula seleção conveniente; mostrar conjunto pequeno e fixo. Momentos amostrais de assimetria/curtose são instáveis com poucas operações. **Validação:** casos calculados à mão (inclusive dados no estilo da Tabela 2.3) e testes de propriedades.

### O2 — Heurística de sobreajuste: curtose e lucros de tamanho semelhante *(livro: C6, p. 43)*

Sinalizar distribuição de retornos por barra/operação com curtose excedente acima de limite configurável (autor cita 7–8 como suspeito) e/ou fração excepcional de operações lucrativas quase idênticas, integrando o bloco de alertas (livro 2, cap. 1 O3). É heurística baseada em experiência, não teste estatístico. **Complexidade:** baixa. **Validação:** série sintética semelhante a sobreajuste.

### O3 — Comparação de duas amostras de retornos de operação entre treino e teste *(livro: C7, p. 48)*

Teste t de duas amostras Welch/Satterthwaite (e alternativa bootstrap) sobre retornos líquidos de operações dos segmentos de treino e teste, exibindo tamanhos das amostras. Responde se período de teste difere estatisticamente do treino; evita comparação visual. **Complexidade:** baixa. **Riscos:** poucas operações e caudas pesadas; teste detecta *diferença*, não habilidade; combinar com permutação do livro 3, cap. 5. **Validação:** amostras sintéticas com diferença média conhecida.

### O4 — Normalizar comparação por volatilidade-alvo *(livro: C8, pp. 52–53)*

Apresentar cada execução também com **volatilidade anualizada-alvo** (12% no livro): `scale = alvo / volatilidade realizada`, aplicado à série de retornos (escala de exposição limitada a 1 por ser à vista e apenas comprada; portanto só reduz exposição quando volatilidade supera o alvo). Útil para comparar BTC com moeda menor. **Complexidade:** baixa. **Risco:** limite 1 impede ampliar resultado de baixa volatilidade; rotular claramente.

### O5 — Verificar cobertura de regimes da janela de dados *(livro: C4, p. 29)*

Classificar trajetória de comprar e manter em alta/baixa/lateralização (por exemplo, retorno móvel em relação a uma faixa) e avisar se algum grupo estiver sub-representado; para estratégias compradas, alertar janelas dominadas por alta. A classificação heurística é **adaptação nossa**; o livro fornece o princípio. **Complexidade:** baixa a média. Relaciona-se a quebras de regime nomeadas (livro 2, cap. 5 O1).

### O6 — Explicitar regra de uso único *(livro: C2, p. 27)*

Já coberto pela proposta de validação bloqueada (livro 3, cap. 9 O2). Acrescentar ao runbook: validação que falha encerra a ideia; ajustar novamente depois de vê-la contamina os dados. **Complexidade:** documentação.

### O7 — Documentar convenções de retorno e anualização *(livro: C8, pp. 49–53)*

Registrar em `docs/` retornos usados (simples/log), base de dias (365 dias corridos para cripto) e anualização da volatilidade, resolvendo contradição do livro (“multiplicar por 252” versus raiz quadrada). **Complexidade:** muito baixa.

### Não aplicável

Construção de índices de preços, médias para preços de commodities e exercícios de probabilidade conjunta.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O7 nota sobre convenções | média | – | – | muito baixa | – |
| 2 | O1 conjunto ampliado de métricas | alta | alta | – | baixa–média | livro 1, cap. 2 O1 |
| 3 | O2 alerta de curtose | média | – | – | baixa | O1 |
| 4 | O3 teste t treino versus teste | média | – | – | baixa | O1 |
| 5 | O5 cobertura de regimes | média | – | – | baixa–média | – |
| 6 | O4 visão por volatilidade-alvo | baixa | média | – | baixa | O1 |
| 7 | O6 regra no runbook | – | – | – | nenhuma | – |

## 5. Arquivos afetados

`analytics/domain/metrics.py`, `analytics/domain/inference.py`, `backtesting/domain/segments.py`, `analytics/presentation/schemas.py`, `docs/openapi.json`, nota de convenções em `docs/`, cartões de métricas e testes (`api/tests/unit`).

## 6. Plano incremental

1. Nota de convenções.
2. Funções puras: Sortino, Calmar, assimetria, curtose e percentis.
3. Comparação treino/teste e alerta de curtose.
4. Aviso de cobertura de regimes e visão de volatilidade-alvo.

## 7. Critérios de aceitação e testes

* Casos calculados manualmente para cada métrica nova; `None` com motivo para série degenerada/curta.
* Adições opcionais à API; execuções armazenadas não mudam; Ruff, mypy e testes atuais passam.

## Ressalvas

Limites do livro (400 operações para erro de 5%, curtose acima de 7–8 e volatilidade-alvo de 12%) são convenções do autor para futuros. Regra 1/√N é aproximação que supõe operações independentes.
