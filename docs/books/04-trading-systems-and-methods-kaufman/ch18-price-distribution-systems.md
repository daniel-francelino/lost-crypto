# Livro 4 · Capítulo 18 — Sistemas de distribuição de preços

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foram lidas somente as pp. 801–802 (introdução e medição da volatilidade). As seções “Uso de distribuições e padrões de preços para antecipar movimentos” (805–810), “Distribuição de preços” (811–821), “Market Profile de Steidlmayer” (822–829) e “Uso de distribuições diárias para identificar suporte e resistência” (830–832) **não foram lidas**; apenas os títulos e uma tabela com letras do perfil foram vistos. Por isso, este relatório é breve e as oportunidades são provisórias.

## 1. Resumo do capítulo (conteúdo lido)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Os preços podem ser vistos como uma **distribuição**, em vez de uma série temporal (precificação de opções compara volatilidade histórica e implícita; gestores de risco usam desvio-padrão anualizado). O desvio-padrão é a medida básica: ±1σ ≈ 68% do movimento, ±2σ ≈ 95%, ±3σ ≈ 99,7%; teoricamente, tudo fica dentro de ±3,5σ. | 801 |
| C2 | **Medir uma distribuição exige dados suficientes**, e a volatilidade é comparada em **janelas de 20 dias** para observar mudanças. A volatilidade anualizada do petróleo bruto foi 39% entre 1983–2010, mas chegou a 140% no fim de 2008 (uma queda nunca pode exceder 100%, enquanto o desvio-padrão dos retornos também inclui oscilações de alta, de US$ 30 a US$ 150 e de volta); a volatilidade pode disparar por períodos curtos em situações extremas de estresse. | 801–802 |
| C3 | (Não lido) O Market Profile (Steidlmayer) constrói uma distribuição do tempo ou volume em cada nível de preço durante a sessão para encontrar áreas de valor e suporte/resistência. | 822–832 (somente títulos) |

## 2. Diagnóstico

| Conceito | Status | Evidência |
|---|---|---|
| Volatilidade realizada móvel | ❌ | Não é calculada em lugar algum (não há métrica de volatilidade em `analytics`). |
| Distribuição por nível de preço (volume ou tempo no preço) | ❌ | Não existe. |
| Volatilidade anualizada dos retornos de um bot | ❌ | Não consta em `Metrics` (cap. 2, O1 do livro 4). |

## 3. Oportunidades

### O1 — Volatilidade realizada móvel como recurso compartilhado e visualização *(livro: C1, C2, pp. 801–802)*

A volatilidade realizada anualizada de 20 barras (configurável), usando a convenção do cap. 3, O1 do livro 1 (365 dias para cripto), é pré-requisito para stops e dimensionamento baseados em ATR/σ (caps. 20 e 23), metas de volatilidade (cap. 2, O4) e razões de choque (cap. 14, O1). Uma implementação; exibir junto ao gráfico de candles. **Complexidade:** baixa. **Ressalva do livro:** volatilidade realizada calculada a partir dos retornos reflete as duas direções; grandes altas a elevam tanto quanto quedas. Para risco, usar também medidas de queda ou baseadas em drawdown (cap. 2, O1).

### O2 — Perfil de volume por preço (área de valor, ponto de controle) somente como diagnóstico de pesquisa *(livro: C3 · apenas a ideia, capítulo não lido)*

OHLCV dos candles permite uma aproximação de perfil de volume (distribuir o volume de cada candle ao longo de sua faixa), da qual se calcula um ponto de controle e uma área de valor. Saber se esses níveis funcionam como suporte/resistência em cripto é uma questão empírica; qualquer estudo deve seguir o processo de diagnóstico e pipeline do livro 3 (definição do objetivo, fora da amostra e contagem de testes múltiplos). **Complexidade:** média. Registrar como **H-VOLUME-PROFILE**; **não recomendado antes da leitura do capítulo**.

### Não aplicável

Volatilidade implícita de opções, gráficos de letras do Market Profile.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Recurso de volatilidade realizada O1 | média | média | – | baixa | – |
| 2 | Perfil de volume O2 | baixa | – | – | média | leitura do capítulo |

## 5–7. Arquivos, plano e aceitação

`analytics/domain/` (volatilidade móvel), compartilhado com helpers de estratégias; visualização no gráfico do app. Aceitação: corresponder à volatilidade calculada manualmente em fixtures; invariância de escala; ruff, mypy e testes aprovados.

## Ressalvas

O conteúdo principal do capítulo (sistemas baseados em distribuições e Market Profile) não foi lido. A única afirmação quantitativa consultada foi o exemplo de pico de volatilidade do petróleo bruto.
