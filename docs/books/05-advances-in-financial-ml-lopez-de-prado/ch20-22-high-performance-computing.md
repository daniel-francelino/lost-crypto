# Livro 5 · Capítulos 20–22 — Receitas de computação de alto desempenho

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foi lido somente o divisor da Parte 5 e início do cap. 20 (pp. 301–303), além dos títulos: cap. 20 *Multiprocessing and Vectorization* (p. 303), cap. 21 *Brute Force and Quantum Computers* (p. 319), cap. 22 *High-Performance Computational Intelligence and Forecasting Technologies* (p. 329, de Kesheng Wu e Horst Simon). Conteúdo **não analisado**; arquivo registra escopo e poucas implicações visíveis na introdução.

## Sobre o conteúdo dos capítulos (páginas lidas)

* **Cap. 20:** explica `mpPandasObj`, usado ao longo do livro — motor de multiprocessamento que particiona trabalho (“moléculas”) entre CPUs/servidores; e vetorização (“programação de arrays”) como paralelização simples, por exemplo construir produto cartesiano de dimensões definidas em execução. Estrutura independente de hardware (núcleos de servidor ou cluster/nuvem).
* **Cap. 21:** otimização discreta por força bruta e computadores quânticos (somente título).
* **Cap. 22:** HPC e tecnologias de previsão (somente título).

## Diagnóstico (fatos relevantes à plataforma)

| Tópico | Status | Evidência |
|---|---|---|
| Execução paralela de varreduras/backtests | ⚠️ | Varreduras ocorrem no serviço de backtest; `MAX_SWEEP_RUNS` limita volume. Verificar se execuções são concorrentes ou sequenciais antes de projetar paralelismo. |
| Execução em segundo plano | ✅ | Processos worker (heartbeat, reconciliador) existem para negociação; trabalhos longos de pesquisa precisariam de worker semelhante. |

## Oportunidades

* **O1 — Execução paralela/em segundo plano para trabalhos pesados de pesquisa** (PBO com S=16 → 12.870 combinações de séries pré-calculadas é barato; CPCV com varredura por divisão, distribuições nulas em dados sintéticos (cap. 13 O1) e SADF são caros). Projetar quando esses itens forem aprovados: tabela de jobs, pool de workers limitado pela CPU, sementes determinísticas por job e resultados persistidos; avaliação vetorizada estilo NumPy quando lógica permitir. **Complexidade:** média–alta. **Não implementar antes** dos primeiros itens (registro, PBO, DSR), pois têm baixo custo.
* **O2 — Implementações vetorizadas em analytics** (estatísticas móveis, bootstrap, laços combinatórios CSCV) em vez de laços Python, para manter latência da API baixa. Avaliar se desempenho virar problema; projeto usa `Decimal` para dinheiro, então manter explícita fronteira entre float/vetorização (estatísticas de pesquisa podem usar float; quantias de negociação permanecem `Decimal`).

## Não aplicável

Computação quântica, GPU/clusters distribuídos, previsão em escala de supercomputador. Plataforma de usuário único não precisa disso.

## Ressalvas

Pp. 304–360 não foram lidas; não extrapolar recomendações além dos dois pontos genéricos acima.
