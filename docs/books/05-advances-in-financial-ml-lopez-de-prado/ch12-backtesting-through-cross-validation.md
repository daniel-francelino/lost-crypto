# Livro 5 · Capítulo 12 — Backtesting por validação cruzada

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 161–168 (walk-forward e armadilhas, backtest por CV, CV purgada combinatória, como CPCV trata sobreajuste e exercícios) foram lidas. Fórmula de máximo esperado na p. 166 saiu parcialmente corrompida na extração e só é mencionada qualitativamente.

**Relevância:** oferece a resposta do livro ao problema “um único caminho histórico é fácil de sobreajustar”: gerar **vários caminhos fora da amostra** da mesma história. Para plataforma baseada em regras, importa sobretudo quando há parâmetros aprendidos/otimizados (toda busca e seleção é um processo de aprendizado); CPCV aplica-se ao procedimento “otimizar em blocos de treino, testar em blocos retidos”.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Duas formas de usar dados passados: (1) simular desempenho histórico (**walk-forward, WF**); (2) simular **cenários que não ocorreram**. “Backtest” tornou-se sinônimo de WF. Não há receita genérica; cada teste deve ser adaptado à estratégia. | Dois paradigmas de backtest. | 161 |
| C2 | **Vantagens do WF**: interpretação histórica clara (comparável ao paper); histórico é filtragem temporal e dados anteriores garantem OOS (com purge; erro comum é vazamento quando `t1.index` fica no treino e `t1.values` no teste). Não precisa embargo. **Armadilhas do WF**: (1) testa **um caminho só**, fácil de sobreajustar; (2) resultado depende da **sequência** (treinar em baixa e testar em alta versus inverso); “é tão fácil sobreajustar walk-forward quanto walk-backward”; resultado inconsistente quando se inverte sequência é evidência de sobreajuste; (3) decisões iniciais usam poucos dados — com aquecimento `t₀` de T, metade das decisões tem em média apenas cerca de `3t₀/(4T) + 1/4` da amostra. | Limites do walk-forward. | 161–162 |
| C3 | **Backtests por CV** (treinar em todos os períodos exceto o teste, por exemplo testar 2008 com modelo treinado em 2009–2016): não são historicamente precisos, mas são **cenário de estresse** para estratégia “ignorante” do período. Vantagens: não dependem da ordem histórica; cada decisão usa treino de mesmo tamanho; toda observação é testada uma vez (maior OOS). Desvantagens: continua sendo um único caminho; sem interpretação histórica; pode haver vazamento porque treino não precede teste (precisa purge/embargo, cap. 7). | Teste como cenário. | 162–163 |
| C4 | **Validação cruzada purgada combinatória (CPCV)**: dividir T observações em N grupos ordenados; cada combinação de k grupos forma teste (`C(N,k)` divisões); cada grupo aparece em `φ[N,k] = k·C(N,k)/N` testes, recombinados em **`φ` caminhos distintos de backtest** (ex.: N=6, k=2: 15 divisões, 5 caminhos, treino = `1 − k/N`); aplicar purge/embargo (cap. 7); resulta em **distribuição de Sharpe** (um por caminho), não valor único. `k=1` vira CV; `k=2` gera N−1 caminhos e treino `1−2/N`; escolher `N=φ+1`; limitar `k≤N/2`. | Muitos caminhos a partir de um histórico. | 163–166 |
| C5 | **Como CPCV trata sobreajuste**: máximo esperado de I estimativas Sharpe normais IID cresce com I (aprox. `(1−γ)Z⁻¹[1−1/I] + γZ⁻¹[1−1/(Ie)]`, γ = constante Euler–Mascheroni 0,5772), ou seja, viés de seleção aumenta com testes. WF/CV estimam Sharpe em um caminho (variância alta); CPCV calcula média de φ caminhos: `σ²[média] = φ⁻¹σ²(1 + (φ−1)ρ̄)`, menor que um caminho quando correlação média `ρ̄ < 1`; reduz falsas descobertas (não elimina viés, reduz variância). Revisor pode exigir CPCV com N,k escolhidos posteriormente, evitando sobreajuste a caminho específico. | Variância da estimativa de desempenho. | 166–167 |
| C6 | Exercícios: testes com sequência invertida, viés de seleção do aquecimento, divulgação seletiva WF versus CV, valores N,k para 1.000 caminhos em 100 mil previsões e ética de retirar artigo após CPCV falhar (Sharpe médio −1, desvio 0,5). | Prática. | 167–168 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Backtest histórico de caminho único | ✅ | Backtest executa uma vez no período selecionado. |
| Teste de sanidade da sequência invertida | ❌ | Não disponível (nem útil para todas as estratégias; diagnostica sobreajuste em processos que aprendem parâmetros). |
| WF/reotimização móvel | ❌ | B-WALK-FORWARD proposto (livro 4, cap. 21 O4). |
| CV/CPCV | ❌ | Nenhuma. |
| Distribuição de desempenho em vários caminhos | ❌ | Um valor por backtest e lista por varredura. |
| Aquecimento | ✅/⚠️ | Indicadores precisam histórico; resultados cobrem período após aquecimento. Tamanho efetivo por decisão não é questão em regras sem aprendizado. |

## 3. Oportunidades

### O1 — CPCV para qualquer processo que **escolha parâmetros a partir dos dados** (pipeline varrer-e-selecionar) *(livro: C4, C5, pp. 163–167)*

* **Proposta:** tratar “varrer blocos de treino → escolher melhor → testar em blocos retidos” como aprendiz; implementar CPCV nos candles cronológicos: `N` grupos ordenados (ex.: 8–12), `k=2` retidos; para cada uma de `C(N,2)` divisões, executar varredura nos blocos de treino com purge/embargo (reutilizar motor, `MAX_SWEEP_RUNS` por divisão), aplicar parâmetros escolhidos nos blocos retidos e **recombinar** segmentos retidos em N−1 caminhos OOS completos. Relatar distribuição (média, mediana, desvio, fração negativa) de Sharpe/retorno/drawdown entre caminhos e estabilidade dos parâmetros selecionados entre divisões.
* **Motivo:** valor OOS único é ruidoso e depende do caminho; distribuição responde “como esse processo de seleção poderia ter se saído”, incluindo taxa de falha. Integra com PBO (cap. 11 O2) e Sharpe deflacionado (cap. 14).
* **Custos/riscos:** custo cresce como `C(N,2) ×` custo da varredura (N=10 → 45 varreduras); posições abertas/estado de indicadores nas fronteiras exigem purge/embargo (cap. 7 O1); cada caminho concatena segmentos de modelos distintos (curva pode ter saltos; fechar posições na fronteira ou avaliar de modo consistente); histórico cripto curto (N grupos de poucos meses, cada qual regime distinto e resultados ruidosos); caminhos correlacionados por reutilização de grupos (`ρ̄` do livro). **Complexidade:** alta. **Validação:** passeio aleatório sem vantagem gera distribuição centrada perto de zero (menos custos), sem proporção de caminhos positivos sistematicamente alta; vantagem inserida produz positividade entre caminhos; nenhum treino dentro de intervalo retido ± embargo; quantidade de caminhos igual a `φ[N,k]`.

### O2 — Verificação de consistência com sequência invertida, diagnóstico barato de sobreajuste em varreduras *(livro: C2, p. 162)*

Executar mesmo processo de varrer/selecionar na série **temporalmente invertida** (para estratégias simétricas, como tendência comprada/vendida; para somente comprado, inversão transforma altas em baixas, então diferença é economicamente legítima — declarar ressalva) e comparar. Argumento do livro: se WF fosse informativo para o futuro, sequências normais deveriam superar sistematicamente as invertidas; inconsistência indica sobreajuste do processo. Oferecer como **diagnóstico de pesquisa**, com ressalva long-only. **Complexidade:** baixa–média. **Riscos:** interpretação errada para spot somente comprado; não usar como aprovação/reprovação.

### O3 — Cenários de estresse com período retido pela lógica CV (treino sem período de estresse) *(livro: C3, pp. 162–163)*

Definir períodos cripto nomeados (ex.: baixa de 2018, crash de março/2020, topo de 2021, estresse Luna/FTX de maio/2022, baixa de 2022); avaliar configuração escolhida em dados **sem** o período de estresse nesse período, mostrando desempenho de estratégia “ignorante” da crise. Concretiza análise de choques (livro 4, cap. 21 O5) e representatividade do período. **Complexidade:** baixa–média (lista de períodos, segmentação, purge). **Validação:** parâmetros não dependem do período retido (teste de propriedade); resultados reproduzíveis.

### O4 — Informar a amostra usada por decisão em procedimentos móveis/WF *(livro: C2, p. 162)*

Quando B-WALK-FORWARD existir, relatar quantidade média e mínima de dados disponíveis em cada decisão (efeito de aquecimento: decisões iniciais usam poucas observações). Expressão do livro mostra que somente fração da amostra total informa metade das decisões. **Complexidade:** baixa.

### Não aplicável

Discussão dos exercícios sobre ética de periódicos; fórmula assintótica exata do máximo esperado (derivada novamente no cap. 14).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Períodos de estresse retidos O3 | alta | média | – | baixa–média | segmentação + purge (cap. 7 O1) |
| 2 | Relatório de amostra por decisão O4 | baixa | – | – | baixa | walk-forward |
| 3 | Diagnóstico de sequência invertida O2 | baixa | – | – | baixa–média | – |
| 4 | CPCV para varrer/selecionar O1 | alta | – | – | alta | cap. 7 O1, cap. 11 O1–O2 |

## 5. Arquivos afetados

`backtesting/application` (orquestração CPCV sobre varreduras; execução longa em job de background como workers atuais), `backtesting/domain/segments.py` (divisão de grupos, purge/embargo, recombinação de caminhos), `analytics/domain` (estatísticas de caminhos), `docs/openapi.json`, app (visão da distribuição de caminhos), testes.

## 6. Plano incremental

1. Avaliação de períodos de estresse retidos (O3) sobre purge/embargo.
2. Walk-forward (livro 4, cap. 21 O4), depois orquestração CPCV em tarefa de background.
3. Combinar com PBO e Sharpe deflacionado em painel de “credibilidade da seleção”.

## 7. Critérios de aceitação e testes

* `φ[N,k]` e quantidade de divisões seguem fórmulas (N=6, k=2 → 15 divisões, 5 caminhos); cada grupo testado exatamente φ vezes; cada caminho cobre cada grupo uma vez; treinos expurgados não cruzam intervalos retidos/embargo; determinístico com semente; ruff, mypy e testes existentes aprovados.

## Ressalvas

O livro apresenta CPCV como invenção própria e não dá estudo empírico de falsas descobertas nestas páginas (remete a artigos e capítulos posteriores); redução de variância depende da correlação média entre caminhos, alta quando compartilham grupos. Respostas dos exercícios não são fornecidas. Argumento WF versus série invertida é exemplo, não teorema. Para estratégia long-only baseada em regras com 2–3 parâmetros, análise de platô/PBO oferece boa parte do benefício a custo bem menor.
