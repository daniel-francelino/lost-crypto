# Livro 5 · Capítulo 5 — Atributos diferenciados fracionariamente

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 75–86 (motivação, dilema estacionariedade versus memória, literatura, método de diferenciação fracionária, pesos e convergência, implementações de janela expansiva e largura fixa, d mínimo para estacionariedade, início da Tabela 5.1) foram lidas. Pp. 87–90 (restante da tabela, conclusões e exercícios) não foram lidas.

**Compatibilidade com a plataforma:** hoje não há atributos de ML. Este capítulo só será relevante se um modelo for treinado com informação do nível de preço (meta-rotulagem, cap. 3 O3) ou como diagnóstico da memória dos preços brutos. É capítulo futuro, de baixa prioridade.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | **Dilema entre estacionariedade e memória**: modelos supervisionados geralmente exigem atributos estacionários, mas diferenciação inteira usual (retornos) elimina **toda a memória**, enquanto níveis de preço preservam memória, mas não são estacionários. Memória é base do poder preditivo (por exemplo, modelos de equilíbrio precisam saber o quanto o preço se afastou da média). Estacionariedade é “necessária, mas não suficiente”. Pergunta: qual a **menor diferenciação que torna a série estacionária e preserva o máximo de memória**? Retornos são “um tipo de transformação (e, na maioria dos casos, subótima)”. | Diferenciação excessiva. | 75–76 |
| C2 | **Diferenciação fracionária**: generalizar `(1 − B)^d` para d real pela série binomial; `X̃_t = Σ_k ω_k X_{t−k}`, `ω_k = −ω_{k−1}(d − k + 1)/k`, `ω_0 = 1`; `d = 0` retorna série original, `d = 1` primeira diferença `{1, −1, 0, …}`; para `0 < d < 1`, pesos são negativos, decaem e convergem a zero (memória preservada com peso decrescente). | A transformação. | 76–80 |
| C3 | **Janela expansiva** aplica todos os pesos disponíveis e sofre memória desigual entre pontos e **deriva negativa** (fig. 5.3), a menos que a perda de peso seja controlada. **Janela de largura fixa (FFD)** descarta pesos com `|ω_k| < τ` (ex.: 1e-5), usa o mesmo vetor de pesos para cada ponto e gera **combinação sem deriva de nível + ruído**; saída é estacionária, mas não gaussiana (assimetria/curtose pela memória). | Implementação prática. | 80–84 |
| C4 | **d mínimo**: para log-preços diários do E-mini S&P 500, desde início e rolados pelo truque ETF, estatística ADF cruza valor crítico de 95% (−2,8623) perto de **d ≈ 0,35**, quando correlação com série original ainda é **0,995**; retornos (d = 1) têm ADF −46,9 e correlação original 0,03. Tabela 5.1 mostra **87 futuros líquidos** alcançando estacionariedade em **d < 0,6**; alguns (suco de laranja, gado vivo), sem diferenciação. “A maioria dos estudos diferenciou em excesso.” | Evidência de que d = 1 é excessivo. | 84–86 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Engenharia de atributos/modelos | ❌ | Não existe; estratégias usam preço/indicadores diretamente (EMA, Donchian). |
| Testes de estacionariedade (ADF), diferenciação fracionária | ❌ | Nenhum. |
| Memória do nível de preço usada por estratégias | ✅ (implícita) | EMA crossover e Donchian dependem do histórico de níveis; não são modelos estatísticos e não exigem estacionariedade. |

## 3. Oportunidades

### O1 — Diferenciação fracionária (FFD) como função pura e diagnóstico de d mínimo *(livro: C2–C4, pp. 76–86)*

* **Proposta:** implementar `ffd(series, d, threshold)` (janela fixa) e `min_d(series)` (menor d numa grade para que teste Dickey–Fuller aumentado na série FFD rejeite raiz unitária a 5%, informando correlação com original nesse d) no domínio analytics; expor nos diagnósticos das séries de log-preços de cada par/timeframe importado. Usar decimais ou floats conforme convenção do módulo analytics (float somente dentro do módulo; valores monetários continuam `Decimal` nas fronteiras).
* **Motivo:** se houver modelo com atributos de preço, o diagnóstico estima diferenciação necessária, oferecendo atributos estacionários com memória; também descreve persistência/tendência do ativo. Evidência do livro é sobre futuros (87 séries), não cripto: medição da plataforma verificaria BTC/ETH etc.
* **Custos/riscos:** exige ADF (statsmodels não está no projeto; implementar corretamente não é trivial; valores críticos e seleção de defasagens importam) → dependência nova ou versão restrita e testada. Saída FFD não é gaussiana; d diferente por ativo reduz comparabilidade; τ e largura são parâmetros. **Complexidade:** média. **Validação:** `d = 0` retorna série; `d = 1` equivale a primeiras diferenças; pesos seguem recorrência; estatística ADF coincide com referências em fixtures (passeio aleatório não rejeita, ruído branco rejeita); `min_d` de AR(1) sintético próximo à raiz unitária entre 0 e 1.

### O2 — Documentar quais indicadores preservam memória e quais são estacionários antes de ML *(livro: C1, pp. 75–76 · adaptação)*

Nota breve nas diretrizes de pesquisa: retornos brutos (estacionários, sem memória), nível do preço (memória, não estacionário), razões EMA, distância ao canal e z-scores (aproximadamente estacionários, com memória parcial) e diferenças fracionárias como escolha de atributos de modelo. Ao considerar ML, definir atributos com essa terminologia e testá-los com diagnóstico. **Complexidade:** documentação.

### O3 — Não acrescentar diferenciação fracionária às estratégias baseadas em regras *(livro: C1)*

Regras EMA/Donchian usam níveis intencionalmente; substituir preços por série FFD muda seu significado e adiciona parâmetros sem evidência de benefício. Registrar para evitar expansão de escopo. **Complexidade:** nenhuma.

### Não aplicável

Truque ETF/rolagens de futuros para série contínua (somente spot); tabela de 87 futuros como evidência para cripto; restauração da gaussianidade; cointegração (livros 1/2 tratam pares).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Nota de vocabulário O2 | baixa | – | – | doc. | – |
| 2 | Diagnóstico FFD + d mínimo O1 | baixa–média | – | – | média | decisão sobre dependência ADF |
| 3 | O3 (não agir) | – | – | – | – | – |

## 5. Arquivos afetados

`analytics/domain/` (novo módulo `frac_diff`) e dependências (ADF), testes com valores de referência; documentação.

## 6. Plano incremental

Não implementar antes de aprovar linha de ML (cap. 3 O3). Se aprovado: função FFD e testes → ADF → diagnóstico por par → decidir se algum modelo precisa dela.

## 7. Critérios de aceitação e testes

* Recorrência dos pesos e casos especiais (`d = 0`, `d = 1`) verificados; comprimento e aquecimento FFD conforme especificação; saídas ADF coincidem com tabelas publicadas para séries conhecidas; diagnóstico somente de leitura.

## Ressalvas

Evidências usam futuros (baseadas em ADF) e dados diários do E-mini S&P; estacionariedade pelo ADF é teste estatístico com baixo poder e sensível à especificação. Correlação preservada (0,995 em d = 0,35) indica apenas proximidade da série original, não maior poder preditivo. O livro reconhece que estacionariedade não garante capacidade preditiva. Estas páginas não demonstram que diferenciação fracionária melhora resultados de negociação.
