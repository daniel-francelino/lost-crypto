# Livro 5 · Capítulo 1 — Aprendizado de máquina financeiro como área distinta

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 3–15 (motivação, razões do fracasso de projetos, estrutura do livro por cadeia de produção/componente/armadilha, público e perguntas frequentes até o início de “econometria”) foram lidas. Pp. 16–20 (restante das perguntas e encerramento do capítulo) não foram lidas. O capítulo é organizacional e metodológico; não contém algoritmos. Seu valor é o mapa de armadilhas (Tabela 1.2) abordadas no restante do livro e um **ciclo de vida de estratégias** que corresponde às etapas paper/ao vivo da plataforma.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | Motivação: aproximar academia e indústria; finanças devem servir a um propósito; muitos investidores usarão ML pronto e perderão dinheiro; **sobreajuste de backtest** é a dificuldade característica do ML financeiro; ML financeiro é uma área distinta do ML padrão. | 3–4 |
| C2 | **Por que projetos fracassam — paradigma de Sísifo**: cada pesquisador sozinho produz um falso positivo de backtest sobreajustado ou investimento padrão em fatores. Solução: **paradigma de metaestratégia** (fábrica de pesquisa com estações especializadas: curadoria de dados, analistas de atributos, estrategistas, backtesters, implantação e supervisão de carteira). Produzir uma estratégia verdadeira custa quase tanto quanto produzir cem. | 4–5 |
| C3 | **Detalhes da cadeia de produção**: descobertas dos analistas de atributos viram bibliotecas utilizáveis em execução, monitoramento e criação de mercado; “erro comum é pensar que analistas de atributos desenvolvem estratégias”. **Estrategistas** formulam teoria que identifique “o mecanismo econômico que faz um agente perder dinheiro para nós” (viés comportamental, informação assimétrica, restrição regulatória) — “atributos podem ser descobertos por caixa-preta, mas a estratégia é desenvolvida em caixa-branca”. **Backtesters** avaliam “a probabilidade de sobreajuste do backtest considerando quantas tentativas foram necessárias para destilar a estratégia” e **não devem devolver resultados à pesquisa** (para evitar feedback); reportam à gestão. A implantação garante que a solução implantada seja logicamente idêntica ao protótipo. | 7–8 |
| C4 | **Ciclo de vida da estratégia** (supervisão de carteira): (1) **quarentena/embargo** — operar em dados posteriores à data final do backtest; (2) **paper trading** com fluxo ao vivo (latências, atrasos de execução); (3) **promoção** a posição real, com atribuição precisa; (4) **realocação** — alocação segue trajetória côncava (pequena na promoção, cresce enquanto desempenho corresponde ao esperado, diminui quando se deteriora); (5) **desativação** quando desempenho fica abaixo por tempo suficiente para concluir que a teoria de sustentação não se confirma; publicar novas variantes em paralelo. | 8–9 |
| C5 | **Estrutura por componente (Tabela 1.1) e por armadilha (Tabela 1.2)**: paradigma de Sísifo → metaestratégia; pesquisa baseada em backtest → análise de importância de atributos; amostragem cronológica → relógio de volume (cap. 2); diferenciação inteira → fracionária (cap. 5); rotulagem de horizonte fixo → barreira tripla (cap. 3); aprender direção e tamanho simultaneamente → meta-rotulagem (cap. 3); ponderação de amostras não IID → ponderação por unicidade e bootstrap sequencial (cap. 4); vazamento em validação cruzada → purge e embargo (caps. 7, 9); backtest walk-forward histórico → validação cruzada purgada combinatória (cap. 12); sobreajuste de backtest → testes com dados sintéticos e Sharpe deflacionado (caps. 11–16). | 9–13 |
| C6 | Matemática experimental: “resolver problemas difíceis por experimentação”; usar métodos experimentais (caps. 11–15) para avaliar estratégia com mais confiabilidade que uma única simulação histórica; “**seja o que for que fizer, pergunte sempre de que maneira pode estar sobreajustando**”; “sobreajuste é antiético… quando consciente, é fraude científica”; a indústria “só remunera retornos fora da amostra”; todo backtest tem algum sobreajuste e sua magnitude precisa ser quantificada. | 11–12 |
| C7 | **Público**: pesquisadores com experiência em ML; código em Python (pandas, numpy, scikit-learn). Perguntas frequentes: ML pode ajudar onde decisões seguem regras (execução, monitoramento de risco) e cada vez mais em decisões de julgamento; máquinas obedecem regras e mantêm registros; **meta-rotulagem permite aplicar uma camada de ML sobre decisão direcional discricionária ou baseada em regras**; econometria é em grande parte regressão linear, que “não aprende”. | 12–15 |

Afirmações quantitativas prometidas pelo livro (por exemplo, Sharpe deflacionado e purge) são avaliadas nos capítulos seguintes; este capítulo não apresenta evidência empírica.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Processo de pesquisa com estações e responsabilidades | ⚠️ | Um único desenvolvedor; módulos separados (market_data, strategies, backtesting, analytics, risk, trading) espelham as estações no código, mas não há separação de processos/artefatos (por exemplo, “registro de pesquisa”). |
| Contagem de tentativas (“tentativas para destilar a estratégia”) | ❌ | Sem contagem de execuções por família; varreduras limitadas por `MAX_SWEEP_RUNS` e sem correção (livro 4, cap. 21, O2). |
| Metadados da hipótese/mecanismo econômico | ❌ | Estratégias têm descrição no catálogo, mas não mecanismo declarado nem perfil esperado (livro 3, livros 4 caps. 21/22). |
| Período de embargo (dados depois do fim do backtest) | ❌ | Divisão treino/teste dentro do mesmo período; sem “holdout futuro” intocado (livro 3, cap. 6 O5 / livro 4, cap. 21 O3). |
| Paper trading antes do ao vivo | ✅ | Há paper trading e gate de permanência mínima antes do modo ao vivo. |
| Ciclo de promoção/realocação/desativação | ⚠️ | Existem estados (rascunho, paper, ao vivo, parado), mas sem reavaliação automática desempenho versus expectativa, redução de alocação por deterioração ou regra de aposentadoria. |
| Separar feedback de backtest da pesquisa | ❌ | Resultados ficam visíveis ao usuário e podem ser iterados livremente; não há avaliação bloqueada. |
| Pipeline de ML (atributos, rótulos, modelos) | ❌ | Nenhum. Plataforma é baseada em regras; capítulos posteriores descrevem requisitos de uma camada ML. |
| Reprodutibilidade | ✅ | Semente e SHA-256 dos candles são armazenados por backtest. |

## 3. Oportunidades

### O1 — Estados de ciclo de vida da estratégia com gates de evidência *(livro: C4, pp. 8–9)*

* **Proposta:** formalizar o caminho de promoção parcialmente existente: **pesquisa (somente backtest) → verificação de embargo → paper → promoção ao vivo (alocação pequena) → realocação → desativação**, exigindo evidência registrada no banco a cada transição: (a) embargo: desempenho em dados **posteriores** ao fim do backtest comparado ao backtest dentro de uma tolerância; (b) paper: duração e número planejado de operações alcançados; (c) promoção: começar com `position fraction` pequeno; (d) realocação: aumentar/reduzir conforme estatísticas ao vivo versus esperadas; (e) desativar quando desempenho ficar abaixo da expectativa por período definido (no livro: “tempo suficiente para concluir que a teoria de sustentação deixou de ter apoio empírico”).
* **Motivo:** combina com a filosofia de segurança da plataforma (modo ao vivo desativado por padrão, gate de paper) e dá **conteúdo** ao gate de dias no paper (livro 4, cap. 22 O2 e cap. 21 O9). A trajetória côncava de alocação (pequena, cresce, encolhe com deterioração) é regra de risco natural para conta de varejo.
* **Complexidade:** média–alta (máquina de estados, campos de evidência, interface); decisão sobre promoção automática ou manual cabe ao usuário. **Riscos:** excesso de engenharia para um usuário; começar por checklist. **Validação:** testes de transição; nenhuma ordem ao vivo pode surgir de estado que não passou pelos gates exigidos.

### O2 — Período de embargo: reservar dados futuros após o fim do backtest *(livro: C4, p. 8)*

Adicionar o conceito de **embargo futuro**: ao validar estratégia com dados até T, registrar T e avaliar depois a mesma configuração fixa com dados acumulados após T (no paper, fluxo ao vivo; em backtests, candles mais novos importados posteriormente). Comparar desempenho no embargo com expectativa do backtest. Sem modelagem adicional: usar importação existente e timestamp “validado até” armazenado no backtest/bot. **Complexidade:** baixa–média. **Validação:** avaliação usa somente candles após T; configuração imutável entre validação e embargo.

### O3 — Campo de hipótese/mecanismo e contador de tentativas em cada configuração *(livro: C3, pp. 7–8)*

Campo de texto obrigatório “por que isso deveria dar lucro (quem perde para nós)” para qualquer bot promovido além do backtest; **contador de tentativas** por família de estratégia (backtests/execuções de varredura, inclusive descartados), exibido junto aos resultados (entrada para Sharpe deflacionado, cap. 14). Igual a O2 do cap. 21 do livro 4. **Complexidade:** baixa. **Riscos:** texto serve apenas como apoio à honestidade.

### O4 — Tratar feedback do backtest como recurso consumível: separar pesquisa e avaliação *(livro: C3, p. 8)*

Backtester do livro não compartilha resultados de avaliação com pesquisa, pois realimentar resultados cria viés de seleção (explicado no cap. 11). Análogo na plataforma: **backtest de avaliação** (dados bloqueados, uma execução por família de configuração, resultado armazenado e não usado para ajuste) separado dos **backtests de pesquisa**. Igual a O5 do cap. 6 do livro 3 / O3 do cap. 21 do livro 4. **Complexidade:** média.

### O5 — Usar o restante do livro como roteiro

Mapear armadilhas da Tabela 1.2 a possíveis tarefas para a plataforma (regras, um ativo, somente comprado), por relevância: (1) estatísticas de backtest, Sharpe deflacionado e contagem de tentativas (caps. 14, 11); (2) validação purgada/com embargo e CV purgada combinatória (caps. 7, 12), se houver ML ou aprendizado de parâmetros; (3) rótulos de barreira tripla e meta-rotulagem (cap. 3) para acrescentar filtro ML **sobre** sinais atuais baseados em regras, sem substituí-los; (4) dimensionamento por probabilidades (cap. 10); (5) quebras estruturais e atributos de entropia (caps. 17–18) como diagnósticos; (6) barras de volume/dólar (cap. 2); (7) diferenciação fracionária (cap. 5) somente se forem criados atributos para modelos. Detalhes estão nos relatórios dos capítulos correspondentes.

### Não aplicável

Orientações organizacionais para equipes de PhDs, computação de alto desempenho e algoritmos quânticos (caps. 20–22; plataforma de usuário único), protocolos de dados de microestrutura de mercado (FIX) e curadoria de dados multiclasse de ativos.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Hipótese e contador de tentativas O3 | alta | – | – | baixa | – |
| 2 | Avaliação com embargo futuro O2 | alta | média | – | baixa–média | importação de candles |
| 3 | Separar pesquisa e avaliação O4 | alta | – | – | média | segmentos |
| 4 | Gates do ciclo de vida O1 | média | alta | alta | média–alta | métricas, alertas |
| 5 | Roteiro O5 | – | – | – | – | capítulos seguintes |

## 5. Arquivos afetados

`backtesting` (data validada armazenada, execuções de avaliação), `trading`/modelos de bot (máquina de estados e evidências), `analytics` (comparação entre embargo e backtest), página de detalhes do bot no app (visão dos gates), documentação.

## 6. Plano incremental

1. Hipótese e contador de tentativas (somente metadados).
2. Relatório de embargo futuro.
3. Execução de avaliação bloqueada.
4. Gates do ciclo de vida, com aprovação do usuário para cada regra.

## 7. Critérios de aceitação e testes

* Contador aumenta a cada execução e membro de varredura; avaliação de embargo exclui dados até T; gates bloqueiam transições sem evidência; padrões não alteram fluxos atuais; ruff, mypy e testes existentes aprovados.

## Ressalvas

Este capítulo argumenta com base na experiência, sem apresentar dados. Separar pesquisa de backtest e paradigma de metaestratégia são ideias para equipes institucionais; para uma pessoa, equivalem a disciplina e ferramentas que a imponham. Afirmações fortes do autor sobre a falta de ética do sobreajuste e sobre ML substituir investimento discricionário são opiniões, não resultados.
