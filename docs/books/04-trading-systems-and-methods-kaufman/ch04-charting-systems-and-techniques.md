# Livro 4 · Capítulo 4 — Sistemas e técnicas gráficas

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 151–153 e 167–180 foram lidas. A parte do método de impulso de Dunnigan até o sistema de ação/reação (pp. 152–166: congestionamento de Nofri, dias externos/internos e pivôs) foi percorrida por alto no início e **não foi resumida**. O pdftotext cortou várias páginas (fórmulas parcialmente perdidas; na p. 178 aparece “13 the number”, provavelmente onde deveria haver uma fração).

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Coletânea de métodos gráficos que podem ser **automatizados**; em muitos, tempo não importa, apenas nível. Primeiros operadores sistemáticos (impulso de Dunnigan: oscilação percentual definida numa janela temporal, com tamanho diferente por mercado) ensinam que “o que parece pouco sofisticado pode ser essencial”. | Origem de regras sistemáticas. | 151–152 |
| C2 | **Negociação em números inteiros**: ordens se agrupam em preços redondos (estudo do Fed de Nova York citado, com maior atividade em números inteiros); passagem por esses níveis é “rompimento menor”. É possível pôr ordem logo além do nível (venda de rompimento em US$ 60 colocada a US$ 60,25) para se antecipar à multidão. | Agrupamento de ordens. | 167 |
| C3 | **Rompimento de canal** por duas formas automatizáveis: (a) máximas/mínimas de oscilações e reta de regressão entre pontos recentes; (b) **reta de mínimos quadrados dos fechamentos** em relação a inteiros sequenciais (não datas, por causa das lacunas de fim de semana), linhas paralelas nas maiores excursões `B_U`/`B_L`, **projetadas um período à frente** pela inclinação. Fecho além da faixa projetada inverte tendência; entradas contra tendência perto da borda e aumento gradual são possíveis; sair quando romper linha oposta; fechos são mais conservadores que máximas/mínimas. | Canal tendencial objetivo. | 167–170 |
| C4 | **Canal móvel**: centro `M = (H+L+C)/3` médio em `n` dias; faixa `R` = amplitude média; bandas `M_t + (M_t − M_{t−1}) ± f·R/2` projetadas um dia; fecho além da banda aciona entrada; alvo de lucro a uma largura de canal do rompimento, recalculado diariamente conforme volatilidade. | Canal ajustado à volatilidade. | 170–171 |
| C5 | **Índice do Canal de Commodities (CCI)**: `CCI = (preço típico − média de n dias) / (0,015 × desvio médio)`. Melhor para reversão à média; regras simples de sobrecompra/sobrevenda dão ganhos pequenos frequentes e uma perda ocasional muito grande quando o preço permanece sobrecomprado por semanas. | Oscilador de reversão e risco de cauda. | 171–172 |
| C6 | **Wyckoff** (preço, volume, ponto-e-figura e ondas) e **Sequential de DeMark** (configuração de nove fechos abaixo do fecho de quatro dias antes, teste de interseção, contagem regressiva de 13 fechos abaixo do fecho de dois dias antes, opções de entrada/saída e stops de amplitude verdadeira). Padrão excessivamente específico só pode ser validado em mercados não relacionados. | Padrões de contagem complexa. | 172–176 |
| C7 | **Lo, Mamaysky e Wang (2000)**: dez formações definidas numa série suavizada por kernel (ex.: cabeça-e-ombros, E3 acima de E1/E5, E1/E5 dentro de 1,5% da média, janela móvel de 38 dias; topo duplo com extremos separados por mais de 22 dias). Centenas de ações dos EUA, 1962–1996; formações muito menos frequentes em séries aleatórias sintéticas; **retornos dos três dias seguintes foram positivos para todas menos uma e estatisticamente significativos para cinco**; volume crescente geralmente melhorou resultados. | Detecção objetiva de padrões. | 176–178 |
| C8 | **Classificações de padrões de Bulkowski** (ex.: melhor padrão de alta, topo retangular com rompimento para cima, cunha descendente com rompimento para cima). O autor observa que rompimento ascendente de triângulo simétrico em tendência de baixa se comporta ao contrário do esperado nos manuais. | Estatísticas de padrões. | 178–179 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Rompimento de canal por extremos de preço | ✅ | `donchian_breakout` implementa rompimento de n barras (máxima anterior em `entry_period`, mínima anterior em `exit_period`). |
| Canal de regressão linear projetado | ❌ | Não consta no catálogo; sem auxiliar de regressão em `strategies/domain`. |
| Canal móvel ajustado à volatilidade/amplitude | ❌ | Donchian usa extremos, não amplitude média; não há auxiliar ATR/amplitude. |
| CCI/osciladores de reversão | ❌ | Não existe estratégia de reversão à média. |
| Consideração de números redondos | ❌ | Ver livro 4, cap. 3 O3 (H-ROUND). |
| Detecção de máximas/mínimas de oscilação | ❌ | Não existe. |
| Detecção de padrões (cabeça-e-ombros etc.) | n/a | Família subjetiva excluída. |

## 3. Oportunidades

### O1 — Estratégia tendencial de canal de regressão *(livro: C3, pp. 167–170)*

Estratégia comprada que ajusta reta de mínimos quadrados aos fechamentos desde referência (ou janela fixa), mede excursões residuais máximas `B_U`/`B_L`, projeta canal uma barra à frente, entra no fecho acima da banda superior projetada com inclinação positiva e sai no fecho abaixo da inferior. Usar fechos, não máximas/mínimas, conforme recomendação conservadora do livro.

**Benefício:** família tendencial diferente de médias móveis e rompimentos de extremos, com faixa escalada pela dispersão dos dados. **Complexidade:** média (regressão numérica em `Decimal`, janela, arquivo de estratégia e formulário). **Riscos:** extremos residuais são sensíveis a outliers; reajuste por barra exige usar apenas dados até o candle fechado atual (coberto pelo teste de truncamento); mais parâmetros e seleção; livro não apresenta desempenho do sistema de canal. **Validação:** truncamento, sensibilidade, melhor entre N comparado a tendências e varredura de custos.

### O2 — Canal móvel ajustado à amplitude *(livro: C4, pp. 170–171)*

Alternativa mais simples: centro = média do preço típico; bandas = ±`f ×` amplitude média, projetadas uma barra com a inclinação do centro. Adapta-se à volatilidade melhor que extremos brutos e é mais simples que O1. Também produz **alvo de lucro a uma largura do canal**, atualizado com volatilidade. **Complexidade:** baixa a média. **Risco:** conceitualmente próximo das regras atuais → alta correlação entre candidatas (N efetivo, livro 3, cap. 6 O4). **Validação:** correlação com Donchian e teste de truncamento.

### O3 — Auxiliares compartilhados: ATR, preço típico e regressão linear *(livro: C3–C5)*

Funções puras em `strategies/domain`, com testes unitários e reutilizadas por O1/O2, stops/dimensionamento por volatilidade (livro 4, caps. 20 e 23) e diagnósticos. **Complexidade:** baixa. **Risco:** ampliar superfície de código; manter uma implementação por indicador.

### O4 — Aviso sobre risco de cauda dos osciladores *(livro: C5, p. 172)*

Ao criar estratégia de reversão à média, mostrar ressalva de que regras osciladoras “dão ganhos pequenos frequentes e perda ocasional muito grande” e exigir controles do livro 2, cap. 8 (stop além da pior excursão do backtest e orçamento de risco). Por ora, apenas documentação e interface.

### O5 — Usar Lo–Mamaysky–Wang como exemplo de teste **objetivo e refutável** de padrões *(livro: C7, pp. 176–178)*

O estudo define padrões objetivamente e os compara com séries aleatórias, conforme o método do livro 3. Se padrões subjetivos forem adicionados, exigir esse padrão (definição objetiva, controle aleatório sintético, horizonte fora da amostra). Nenhum trabalho agora. Efeitos relatados são para três dias em ações dos EUA, antes dos custos.

### Não aplicável

Dunnigan, Nofri, Sequential de DeMark (contagens de um único mercado, que o próprio autor diz exigirem validação em mercados não relacionados), Wyckoff e classificações de Bulkowski.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O3 auxiliares de indicadores | – | – | – | baixa | – |
| 2 | O2 canal de amplitude | média | – | – | baixa–média | O3 |
| 3 | O1 canal de regressão | média | – | – | média | O3 |
| 4 | O4 aviso de oscilador | – | média | – | muito baixa | – |
| 5 | O5 padrão para padrões | – | – | – | nenhuma | – |

## 5. Arquivos afetados

`strategies/domain/` (novos arquivos e auxiliares), `strategies/catalog.py`, registro, formulários/rótulos de estratégia no app, testes (truncamento e validação de parâmetros), `check:consistency`.

## 6. Plano incremental

1. Auxiliares com testes unitários.
2. Adicionar um canal tendencial por vez; cada um passa teste de truncamento e sensibilidade a custos antes de ser disponibilizado.
3. Avaliar pelo fluxo varredura → melhor entre N → validação (livro 3).

## 7. Critérios de aceitação e testes

* Estratégias novas são determinísticas, validam parâmetros, passam teste de truncamento (sem antecipação) e não alteram as existentes.
* Ruff, mypy e testes existentes passam.

## Ressalvas

Retornos dos estudos de padrões são de três dias, antes de custos, em ações dos EUA de 1962–1996. O livro diz que técnicas de canal são convencionais, mas não apresenta evidência cripto; estratégia nova acrescenta regra ao universo e precisa entrar na correção de testes múltiplos.
