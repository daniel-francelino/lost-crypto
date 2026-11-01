# Livro 5 · Capítulo 18 — Atributos de entropia

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 263–267 (entropia de Shannon, estimador plug-in, início dos estimadores Lempel–Ziv/Kontoyiannis) e 275–276 (aplicações financeiras: eficiência de mercado, geração de máxima entropia e início de concentração da carteira) foram lidas. Pp. 268–274 (esquemas de codificação, detalhes dos estimadores, média generalizada/diversidade) e 277–280 (exercícios e referências) **não foram lidas**.

**Compatibilidade com a plataforma:** família de atributos de *pesquisa*. Alegação do livro de que conteúdo de informação (compressibilidade) de sequência de preços indica se apostas de tendência/reversão à média darão certo é hipótese, não resultado demonstrado nestas páginas.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Séries de preço refletem oferta/demanda com informação parcial; estimar **conteúdo informativo** pode gerar atributos: tendência talvez renda mais quando preço tem *pouca* informação e reversão à média, quando tem *muita* (expectativa do autor). | 263 |
| C2 | **Entropia de Shannon** `H[X] = −Σ p[x] log₂ p[x]` (0 ≤ H ≤ log₂|A|), **redundância** `R = 1 − H/log₂|A|`, **informação mútua** `MI[X,Y] = H[X] + H[Y] − H[X,Y]` (normal bivariada: `MI = −½ log(1 − ρ²)`) e variação normalizada de informação como métrica. | 263–264 |
| C3 | **Estimador plug-in (máxima verossimilhança)** da taxa de entropia em palavras de comprimento `w` de sequência discretizada (ex.: sinais de retornos ou retornos em quantis): `Ĥ_{n,w} = −(1/w) Σ p̂_w[y] log₂ p̂_w[y]`; exige `n ≫ w` para distribuição empírica aproximar a real. | 264–265 |
| C4 | Complexidade baseada em compressão **Lempel–Ziv**: mais substrings não redundantes por comprimento da mensagem implicam entropia maior; estimador **Kontoyiannis** usa comprimento de maior correspondência `L_i^n` numa janela passada: `lim L_i^n / log₂ n = 1/H`, estima `Ĥ = [ (1/k) Σ L_i^n / log₂ n ]⁻¹`; mensagens de entropia alta têm correspondências menores. | 265–267 |
| C5 | **Aplicações**: **eficiência de mercado** — mercado “descomprimido” (alta entropia, não redundante) é eficiente; mercado “comprimido” (baixa entropia) é ineficiente e bolhas se formam em mercados comprimidos. **Geração de máxima entropia** (Fiedor) — resultado que maximiza entropia é difícil para modelos frequentistas preverem e pode disparar stops/sequências. **Concentração de carteira** — decompor covariância em autovalores, cargas fatoriais e parcela de risco por componente principal, aplicando medida de concentração baseada em entropia (restante não lido). | 275–276 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Atributos de entropia/compressibilidade | ❌ | Nenhum. |
| Diagnósticos de previsibilidade (autocorrelação, sequências) | ❌ | Planejados no livro 4, cap. 15 O1 (tabelas de sequências) e cap. 1 O1 (ER/ruído). |

## 3. Oportunidades

### O1 — Entropia/compressibilidade de sequências de retornos de candle como **diagnóstico**, comparado a dados embaralhados *(livro: C3, C4, pp. 264–267)*

* **Proposta:** discretizar retornos (sinal ou bins de quantil, ex.: 3 ou 10 símbolos) por ativo/timeframe; calcular taxa de entropia plug-in para palavras `w = 1…~4` e complexidade Lempel–Ziv/Kontoyiannis em janelas móveis; comparar cada uma com distribuição de cópias da janela **embaralhadas** (embaralhamento destrói sequência, preserva marginal), gerando valor tipo p de “redundância excedente”. Mostrar redundância móvel junto da razão de eficiência e diagnósticos de sequência (livro 4 caps. 1 O1 e 15 O1).
* **Motivo:** mesma pergunta das tabelas de sequência, por outra lente (teoria da informação); referência embaralhada corrige fraqueza de valores brutos, dependentes de alfabeto/janela.
* **Complexidade:** baixa–média. **Riscos:** viés de estimação em janelas curtas (`n` muito maior que `|A|^w`); limites arbitrários; agrupamento de volatilidade reduz entropia de codificação de retornos absolutos sem indicar direção explorável. **Validação:** símbolos aleatórios IID dão entropia próxima a `log₂|A|` e redundância excedente zero; sequência periódica/Markov é sinalizada; determinístico com semente.

### O2 — Testar hipótese do livro (baixa entropia ↔ estratégias de tendência funcionam) com estratégias atuais *(livro: C1, C5, pp. 263, 275)*

Usar O1 como variável de regime e perguntar se resultados das operações `ema_crossover`/`donchian_breakout` (tabela de sinais, cap. 3 O1; N efetivo, cap. 4 O1) diferem entre janelas de entropia baixa/alta, em vários ativos, com contagem de testes múltiplos do pipeline. **H-ENTROPY-REGIME.** **Complexidade:** média. **Riscos:** mais uma variável de regime entre ER, volatilidade e SADF; alta chance de achados espúrios; tratar como exploratória, com hipótese pré-declarada e verificação bloqueada.

### O3 — Concentração de carteira via parcelas de risco dos componentes principais (visão futura) *(livro: C5, pp. 275–276)*

Calcular autovalores da matriz de correlação/covariância dos ativos mantidos e parcela de risco por componente principal; informar “número efetivo de apostas independentes” `exp(H)` dessa distribuição. Substituto interpretável para contagem ingênua de ativos na visão de carteira (livro 4, cap. 24 O1). **Complexidade:** baixa–média. **Validação:** covariância identidade dá N; ativos perfeitamente correlacionados dão 1.

### Não aplicável

Esquemas de codificação para barras de quantis/sigma além de nota (não lidos), regras de negociação de máxima entropia (especulativas), entropia de microestrutura de sinais de fluxo (exige dados de negócios).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Número efetivo de apostas O3 | – | média | – | baixa–média | visão de carteira |
| 2 | Diagnóstico de entropia com referência embaralhada O1 | baixa | – | – | baixa–média | módulo de diagnósticos |
| 3 | Teste da hipótese de regime O2 | média | – | – | média | O1, itens caps. 3/4 |

## 5. Arquivos afetados

`analytics/domain/` (estimadores de entropia, referências embaralhadas, parcelas dos componentes principais), página de diagnósticos, testes.

## 6. Plano incremental

O3 junto da visão de carteira; O1 somente se abrir linha de pesquisa de regimes; O2 por último.

## 7. Critérios de aceitação e testes

Estimadores coincidem com formas fechadas em distribuições conhecidas (moeda justa → 1 bit; determinística → 0); referências embaralhadas reproduzem nulo; determinístico; ruff, mypy e testes existentes aprovados.

## Ressalvas

As páginas lidas não contêm resultado empírico que conecte entropia à lucratividade; “mercado comprimido → bolha” e “entropia máxima → cisne negro” são conjecturas de trabalhos citados. Pp. 268–274 e 277–280 não foram lidas.
