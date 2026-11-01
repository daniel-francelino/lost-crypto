# Livro 3 · Capítulo 2 — A validade ilusória da análise técnica subjetiva

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** este capítulo de 70 páginas (pp. 33–102) revisa psicologia cognitiva. Li a estrutura das seções (35–101) e, na íntegra, as passagens sobre excesso de confiança (45–46), viés de confirmação (62–63), correlação ilusória (72–73), heurística da representatividade e gráficos aleatórios (93–94) e ilusão de agrupamento (100–101). As demais passagens (ancoragem, retrospectiva, informação de segunda mão e experimentos detalhados) foram apenas percorridas pelos títulos e não são resumidas em detalhe.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Análise técnica subjetiva não é conhecimento legítimo; a mente humana detecta padrões naturalmente e crenças estranhas são comuns. | Por que a leitura intuitiva de gráficos parece válida. | 35–41 |
| C2 | **Viés de excesso de confiança**: autoavaliações superam a realidade, sobretudo em tarefas difíceis ou impossíveis; **a confiança cresce com a quantidade de informação, não com a precisão**; concordância entre entradas redundantes (vários indicadores medindo a mesma coisa) aumenta a confiança sem justificativa. Exemplos: médicos com 88% de confiança acertaram 20%; gestores com 90% de confiança acertaram 50%. | Combinação subjetiva de muitos indicadores. | 45–46 |
| C3 | **Viés de informação de segunda mão**: uma boa narrativa é persuasiva. | Narrativas em vez de evidências. | 58–61 |
| C4 | **Viés de confirmação**: crenças existentes filtram evidências; êxitos ao acaso dão credibilidade gradualmente a métodos inúteis e os usuários mais experientes **são os menos capazes de perceber suas falhas**. Investimento financeiro/emocional, dissonância cognitiva e buscas enviesadas reforçam o viés. | Aprender com a experiência de forma incorreta. | 62–71 |
| C5 | **Correlação ilusória**: toda afirmação sobre sinal e resultado forma uma tabela de contingência 2×2 (sinal presente/ausente × resultado ocorre/não ocorre). Pessoas valorizam a célula superior esquerda (sinal e resultado) e negligenciam falsos positivos, falsos negativos e verdadeiros negativos. | Julgar um sinal por acertos memoráveis. | 72–81 |
| C6 | **Heurística da representatividade e falsa ideia de aleatoriedade**: dados aleatórios (por exemplo, gráfico de 300 lançamentos de moeda) parecem mostrar padrões; confundem-se padrões aparentes com estrutura (ilusão de agrupamento). Quem acredita na falácia do jogador também pode ser recompensado pelo acaso. Passeios aleatórios podem produzir as formas que analistas gráficos valorizam. | Ver padrões em ruído. | 93–101 |
| C7 | O antídoto é o método científico (capítulo 3). | – | 101 |

## 2. Diagnóstico (verificado no código e na interface)

O capítulo trata do operador humano. O sistema já evita métodos subjetivos (todas as estratégias são código). A questão relevante é se o **produto ajuda o operador a evitar esses vieses**.

| Conceito | Situação | Evidência |
|---|---|---|
| Apenas regras objetivas | ✅ | Ver livro 3, cap. 1. |
| Confiança baseada em indicadores redundantes | ⚠️ | Cada estratégia usa uma família de indicadores; ao combiná-las, a estrutura não detecta redundância entre condições. |
| Viés de confirmação na pesquisa | ⚠️ | Varreduras mostram resultados, mas não registram quantas alternativas foram testadas; o operador pode escolher a melhor execução (livro 1, cap. 3 O7; livro 2, cap. 1 O5). |
| Correlação ilusória (observar apenas acertos) | ❌ | Detalhes do backtest listam operações; não há tabela de **sinais seguidos de movimento versus não seguidos**, nem taxa-base do resultado sem sinal. |
| Ver padrões em ruído | ❌ | Curva patrimonial e gráfico de candles aparecem sozinhos; não se mostra o comportamento patrimonial de regra sem habilidade nos mesmos dados. |
| Viés narrativo | ✅/n/a | O app mostra números e trilhas de auditoria, sem comentários. |

## 3. Oportunidades

### O1 — Tabela de contingência do sinal e taxa-base *(livro: C5, pp. 72–81)*

* **Problema:** as entradas de uma estratégia são julgadas pelas operações lembradas, não pelas quatro células possíveis.
* **Proposta:** nos diagnósticos, para horizonte futuro `h` e definição de resultado escolhidos (por exemplo, “retorno futuro após custos > 0”), apresentar a tabela 2×2: entradas seguidas de resultado positivo; entradas seguidas de resultado não positivo; barras sem entrada seguidas de resultado positivo; barras sem entrada seguidas de resultado não positivo. Incluir a **taxa-base** de resultado positivo em todas as barras e comparação da taxa de acerto. Em estratégias comprado/neutro, “sem entrada” significa barras em que a estratégia está neutra.
* **Benefício:** responde diretamente à pergunta do livro: o sinal supera a frequência incondicional? **Complexidade:** baixa. **Riscos:** uma diferença significativa numa tabela 2×2 ainda requer teste e correção por testes múltiplos (próximos capítulos); horizontes sobrepostos não são independentes (livro 2, cap. 6 O1). **Validação:** dados sintéticos com sinal inserido versus ruído; contagens conferidas manualmente.

### O2 — Visualização “poderia ser acaso?” com curvas patrimoniais placebo *(livro: C6, pp. 93–101 · adaptação)*

Na página do backtest, desenhar a curva patrimonial da estratégia com um conjunto de curvas de entradas aleatórias (mesmo número de operações e duração; ver livro 2, cap. 1 O1 etapa 2 e livro 3, cap. 1 O2). Ver que regras sem habilidade também podem parecer impressionantes ajuda a calibrar a intuição. **Complexidade:** média (reutiliza o motor placebo). **Risco:** poluição visual e desempenho; calcular as curvas sob demanda. **Validação:** teste de interface com semente fixa.

### O3 — Pré-registro de hipóteses e faixas de parâmetros *(livro: C4, pp. 62–71 · adaptação)*

Antes de uma varredura ou experimento relevante, permitir ao operador registrar hipótese, faixas de parâmetros e critério de sucesso (amplia as notas propostas no livro 2, cap. 4 O1). A página do resultado informa se a escolha final respeitou o plano pré-registrado. **Complexidade:** baixa a média. **Risco:** atrito; disciplina opcional. **Validação:** teste da API ligando plano e varredura.

### O4 — Aviso sobre condições redundantes *(livro: C2, p. 46)*

Se for criada uma estratégia combinada, calcular a correlação entre os sinais de suas condições e avisar quando forem redundantes (aumentam confiança, não informação). Adiar até existir estratégia com várias condições. **Complexidade:** baixa a média.

### Não aplicável

Material didático sobre experimentos de percepção e padrões gráficos subjetivos.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 tabela de contingência + taxa-base | alta | – | – | baixa | módulo de diagnósticos (livro 2, cap. 2 O1) |
| 2 | O3 pré-registro | média | – | – | baixa–média | notas (livro 2, cap. 4 O1) |
| 3 | O2 gráfico de placebo | média | – | – | média | motor placebo (livro 2, cap. 1 O1) |
| 4 | O4 aviso de redundância | baixa | – | – | baixa–média | estratégia com várias condições |

## 5. Arquivos afetados

`analytics/domain/` (contagens da tabela), endpoint de diagnósticos de dados de mercado, `backtesting/application/service.py` (planos), páginas de detalhes do backtest e dados de mercado no app e testes.

## 6. Plano incremental

1. Incluir tabela de contingência no módulo de diagnósticos.
2. Criar registros de hipótese/plano (notas).
3. Acrescentar gráfico placebo quando existir executor de entradas aleatórias.

## 7. Critérios de aceitação e testes

* As quatro células somam o número de observações; a taxa-base equivale à frequência incondicional.
* Execuções placebo são determinísticas para uma semente fixa.
* Nenhuma mudança no comportamento de negociação; Ruff, mypy e testes existentes passam.

## Ressalvas

Os experimentos citados (médicos, gestores, previsões de resultados) vêm da revisão bibliográfica do autor e não foram verificados novamente aqui. Conhecer os vieses não os elimina; as propostas apenas acrescentam contrapontos e etapas de controle.
