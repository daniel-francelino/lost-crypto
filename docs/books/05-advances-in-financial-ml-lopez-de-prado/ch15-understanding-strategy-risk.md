# Livro 5 · Capítulo 15 — Compreender o risco da estratégia

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 211–217 foram lidas (pagamentos simétricos/assimétricos, precisão e frequência implícitas, probabilidade de falha da estratégia e início do algoritmo bootstrap). Restante do algoritmo, exemplos numéricos e exercícios (pp. 218–220) **não foram lidos**.

**Relevância:** forma compacta e fechada de relacionar **taxa de acerto (precisão), tamanho dos ganhos/perdas (take-profit/stop) e frequência de apostas** ao Sharpe, e perguntar quão frágil é estratégia a pequenas mudanças de acerto. Mapeia diretamente a estatísticas de tendência/rompimento já exibidas (taxa de acerto, ganho/perda médios, quantidade de operações).

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Maioria das estratégias tem condições explícitas ou implícitas de saída (take-profit/stop-loss; sem stop, existe limite implícito, como chamada de margem ou tolerância à dor). Modelar resultados como **processo binomial** revela combinações antieconômicas de frequência de aposta, odds e pagamentos, e quando a estratégia é vulnerável a pequenas variações. | 211 |
| C2 | **Pagamentos simétricos** (lucro `π` com probabilidade p, perda `−π` com `1−p`; n apostas IID/ano): `E[X] = π(2p−1)`, `V[X] = 4π²p(1−p)`, Sharpe anualizado `θ[p,n] = (2p−1)/(2·sqrt(p(1−p)))·√n` — “um valor t de p reescalado sob `H₀: p = 1/2`”; π se cancela. Pequena vantagem gera Sharpe alto com n grande (base econômica de alta frequência): para `p=0,55`, Sharpe anualizado 2 exige **396 apostas/ano**; apostas semanais (`n=52`) exigem `p ≈ 0,6336` para Sharpe 2. Sharpe depende de **precisão**, não acurácia (não operar não é premiado nem punido). Precisão implícita: `p = (1/2)(1 + sqrt(1 − n/(θ² + n)))`. | 211–213 |
| C3 | **Pagamentos assimétricos** (`π₊ > 0` com p, `π₋ < π₊` com `1−p`): `E[X] = (π₊−π₋)p + π₋`, `V[X] = (π₊−π₋)²p(1−p)`, `θ[p,n,π₋,π₊] = ((π₊−π₋)p + π₋)/((π₊−π₋)·sqrt(p(1−p)))·√n`; reduz ao simétrico se `π₋ = −π₊`. Resolver quadrática dá **precisão implícita p** para Sharpe-alvo (trecho 15.3) e **frequência implícita n** (15.4). Exemplo: `n=260`, `π₋=−0,01`, `π₊=0,005`, Sharpe-alvo 2 exige `p=0,72`; mudança pequena de p (0,70→0,72) move Sharpe de 1,173 para 2 — **estratégia é vulnerável a pequenas mudanças na precisão**. Quanto mais negativo `π₋` para mesmo n, maior p necessária; menos apostas (n menor) exigem maior p. | 213–216 |
| C4 | **Probabilidade de falha da estratégia**: `p_θ*` é precisão abaixo da qual estratégia fica aquém do Sharpe-alvo `θ*`; como p é desconhecido, modelá-lo como variável aleatória. **Risco da estratégia ≠ risco da carteira**: “risco da estratégia é risco de a estratégia de investimento deixar de funcionar ao longo do tempo” (pergunta do CIO), não volatilidade da carteira subjacente (métrica do CRO). Exemplo: queda de p de 0,70 para 0,67 elimina lucros. Probabilidade de falha `P[p < p_θ*]`. | 216–217 |
| C5 | **Início do algoritmo**: a partir de resultados `{π_t}`, estimar `π₋ = E[π_t | π_t ≤ 0]`, `π₊ = E[π_t | π_t > 0]` (ou ajustar mistura de duas gaussianas pelo algoritmo EF3M), frequência anual `n = T/y`; então **reamostrar distribuição de precisão**: sortear com reposição `n·k` resultados (k anos que investidor usa para avaliar estratégia, ex.: 2), obter precisão `p_i` em cada I iterações, ajustar densidade `f[p]` (KDE) e calcular `P[p < p_θ*]` (restante — forma fechada aproximada com E[p] — não lida). | 217 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Taxa de acerto, ganho/perda médios, fator de lucro, quantidade de operações | ✅ | Em `Metrics`. |
| Série de resultados por aposta (retorno por operação) | ✅ | Operações armazenadas; P/L líquido por operação disponível. |
| Apostas anualizadas | ⚠️ | Derivável por operações/período; não informado. |
| Precisão/Sharpe implícitos de `{p,n,π₊,π₋}` | ❌ | — |
| Bootstrap da taxa de acerto/probabilidade de falha | ❌ | — |
| Risco da estratégia versus risco da carteira | ❌ | Métricas de drawdown cobrem risco da carteira; sem métrica “a estratégia continuará funcionando?”. |

## 3. Oportunidades

### O1 — Calculadora de “taxa de acerto necessária” e indicador de fragilidade em cada backtest *(livro: C2, C3, pp. 211–216)*

* **Proposta:** da lista de operações, calcular `π₊` (retorno médio das vencedoras), `π₋` (retorno médio das perdedoras, negativo), precisão observada `p̂` (taxa de acerto) e apostas/ano `n`. Informar: (a) Sharpe anualizado analítico implícito em `{p̂,n,π₊,π₋}` (verificação do Sharpe empírico da curva); (b) **precisão de equilíbrio** `p₀` (Sharpe=0 ⇒ `p₀=−π₋/(π₊−π₋)`) e precisão para Sharpe 1 e 2; (c) **margem de segurança** `p̂−p₀` e `p̂−p_{θ=1}`, em erros-padrão da proporção binomial, para mostrar quantos pontos percentuais de queda da taxa de acerto a estratégia tolera. 
* **Motivo:** estratégias de tendência da plataforma têm acerto em torno de 30–40% e ganho/perda >1 (livro 4 cap. 22 C15); explicita quão estreita é a margem e sua dependência da frequência anual. Se p precisa ficar a 2 pontos da estimativa, estratégia é frágil, sobretudo com poucas operações (erro-padrão de p̂ com 40 operações ≈ 7,7 pontos).
* **Complexidade:** baixa. **Riscos:** modelo presume dois pagamentos e apostas IID; retornos reais são dispersos, então médias π₊/π₋ ocultam distribuição (Sharpe usa médias; conferir desvio-padrão empírico); resultados de tendência têm dependência serial. **Validação:** exemplos do livro (p=0,55 → n≈396 para Sharpe 2; n=52 → p≈0,6336; n=260, π₋=−0,01, π₊=0,005, Sharpe 2 → p=0,72) reproduzidos à precisão impressa; p₀ dá Sharpe zero; invariância ao escalar pagamentos.

### O2 — Probabilidade de falha da estratégia por bootstrap *(livro: C4, C5, pp. 216–217)*

Implementar início do algoritmo: reamostrar resultados de operações para formar distribuição de precisão num horizonte de k anos (`n·k` sorteios), calcular `P[p < p_θ*]` para Sharpe-alvo 0 e 1 e exibir “probabilidade de Sharpe da estratégia cair abaixo de 0/1 nos próximos k anos”. Usar bootstrap em blocos se resultados tiverem dependência serial (adaptação nossa). Combinar com PSR/DSR (cap. 14) e PBO (cap. 11) no painel: PBO = **seleção**, PSR/DSR = **significância estatística**, falha = **fragilidade futura**. **Complexidade:** baixa–média. **Riscos:** bootstrap de conjunto pequeno é ruidoso; viés de seleção não é corrigido (preferir operações fora da amostra/bloqueadas). **Validação:** determinismo com semente; cobertura em pagamentos Bernoulli sintéticos (intervalo nominal versus observado).

### O3 — Usar precisão exigida × frequência como regra ao escolher timeframes *(livro: C2, C3, pp. 212–216)*

Timeframes menores aumentam n e reduzem vantagem necessária para Sharpe dado, mas custos por operação reduzem `π₊` e pioram `π₋` (taxas/slippage entram em ambos; livros 4 caps. 16/22). Calculadora interativa: usuário fornece `{taxa de acerto, ganho médio, perda média após custos, operações/ano}`; interface exibe Sharpe, precisão de equilíbrio e precisão para Sharpe-alvo. **Complexidade:** baixa. **Validação:** igual a O1.

### O4 — Mostrar “risco da estratégia” junto ao risco da carteira *(livro: C4, p. 217)*

Adicionar vocabulário à documentação/interface: drawdown/volatilidade = risco da carteira; margem de segurança em taxa de acerto, ganho/perda e frequência = risco da estratégia. Métricas O1/O2 podem acionar pausa/redução segundo regras do ciclo de vida (cap. 1 O1; livro 4 cap. 22 O2 e cap. 21 O9), por exemplo quando taxa de acerto nos últimos `m` negócios cai abaixo de `p₀` + margem com significância (teste binomial sequencial — livro 4 cap. 23 O8). **Complexidade:** baixa–média.

### Não aplicável

Ajuste de mistura EF3M (não lido), detalhes práticos de alta frequência, pressuposto IID além de nota de sensibilidade.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Taxa exigida/fragilidade O1 | alta | alta | – | baixa | lista de operações |
| 2 | Calculadora interativa O3 | média | média | – | baixa | O1 |
| 3 | Vocabulário + ligação a monitor ao vivo O4 | – | alta | alta | baixa–média | alertas |
| 4 | Probabilidade de falha por bootstrap O2 | alta | alta | – | baixa–média | O1 |

## 5. Arquivos afetados

`analytics/domain/` (módulo de risco da estratégia), `docs/openapi.json`, resultados de backtest e pequena página de calculadora, testes.

## 6. Plano incremental

1. Funções fechadas com exemplos do livro como testes.
2. Painel de fragilidade no nível do backtest.
3. Probabilidade de falha por bootstrap.
4. Hooks de monitoramento ao vivo/paper após existir sistema de alertas.

## 7. Critérios de aceitação e testes

* Reproduzir exemplos impressos; monotonicidade em p e n; precisão de equilíbrio implica Sharpe zero; bootstrap determinístico com semente; ruff, mypy e testes existentes aprovados.

## Ressalvas

Estrutura presume apostas Bernoulli IID e dois níveis de pagamento: modelo estilizado; vencedoras de tendência têm caudas pesadas (livro 4 cap. 22), então aproximação de dois pontos pode enganar; dependência serial é ignorada. Sharpe aqui é por aposta e anualizado por √n, diferente do Sharpe temporal da curva de patrimônio. Pp. 218–220 (restante do algoritmo, exemplos e exercícios) não foram lidas.
