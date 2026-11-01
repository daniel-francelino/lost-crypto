# Livro 4 · Capítulo 15 — Reconhecimento de padrões

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 685–692 e 732–734 foram lidas, além das primeiras linhas da p. 732. Projeções de pivôs/DeMark (688), detalhes de timing intradiário (692–698), lacunas de abertura (699–710), tabelas de dias da semana/fins de semana/reversão (711–731) e métodos de IA (735–736) **não** foram lidos nem resumidos em detalhe.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Reconhecimento de padrões sustenta a maioria dos sistemas; parte do conhecimento inicial é **folclore** (“alta segunda, baixa terça”, “operadores locais zeram na sexta”, “atenção às reversões-chave”), que vale testar por computador. **Contagem de sequências**: registrar todos padrões de alta/baixa de 2 dias (4), 3 dias (8), 4 dias (16)… e medir frequência do movimento seguinte para avaliar previsão; “fonte de muitas ideias valiosas e também caminhos falsos”. | Testar folclore objetivamente. | 685–686 |
| C2 | Estatísticos dizem que melhor previsão de amanhã é preço de hoje (longo prazo: média); ainda assim operadores projetam faixas diárias: **pontos de pivô** `P=(H+L+C)/3`, `R1=2P−L`, `S1=2P−H`, `R2`, `S2`; projeções DeMark condicionam faixas ao preço de abertura versus fecho anterior. | Projeções de níveis. | 687–688 |
| C3 | **Horário do dia**: volume intradiário clássico (máximo perto da abertura, depois do fecho, mínimo ao meio-dia); hábitos (análise à noite → ordens pela manhã; fecho para liquidação; instituições negociam com volume alto ou usam VWAP; queda de liquidez no almoço pode gerar reversão temporária). Estrutura não alterou padrões temporais apesar de HFT. | Sazonalidade intradiária. | 689–690 |
| C4 | **Seis padrões intradiários de Tubbs** (ex.: alta que retorna ao preço de abertura até 13h implica fecho mais fraco); regras anedóticas de leitura de fita. | Folclore de mercado. | 690 |
| C5 | **Estatísticas de dias de reversão** (S&P): após dia de máxima maior e fecho menor, próxima abertura continua baixa 52% das vezes, mas próximo fecho só 43% (reversão de abertura não persiste; alta da abertura ao fecho). Após mínima menor e fecho maior, abertura seguinte sobe 40%, mas fecho 53%. Autor observa que superam viés geral de alta dos índices; mercados diferem (trigo/petróleo exibem outros padrões). | Comportamento condicional do dia seguinte. | 731–732 |
| C6 | **Reconhecimento por computador com perfis de operação** (método anterior de Aronson): definir *resultado* desejado (preço sobe ≥3% em 20 dias sem perda maior que 0,5%); marcar os cinco dias anteriores como “dias de compra” (e simetricamente “venda”); buscar indicadores (direção da média, RSI/sentimento, direção do volume, momentum de dez dias) e **combinações presentes sobretudo nesses dias**. Sinal ideal sem perdas na zona não existe na prática; avaliar sinais pelo retorno líquido e risco. Análogo à regressão múltipla. | Rotular resultados e descobrir preditores. | 732–734 |

Referências a cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Estatísticas de sequências alta/baixa | ❌ | Nenhuma. |
| Estatísticas por hora/dia da semana | ❌ | Nenhuma (planejadas no livro 4, cap. 10 O1). |
| Estatísticas condicionais de dia de reversão | ❌ | Nenhuma. |
| Rotulagem para aprendizado supervisionado | ❌ | Sem rótulos, atributos ou módulo ML; assunto do livro 5. |
| Projeções de nível por pivôs | ❌ | Nenhuma; não recomendadas sem evidência. |

## 3. Oportunidades

### O1 — Diagnóstico de sequências de N candles (probabilidades condicionais do seguinte) *(livro: C1, pp. 685–686)*

No módulo de diagnóstico, tabular para `k=2…5` frequências de sequências alta/baixa e probabilidade condicional (e média) de retorno positivo do candle seguinte; incluir tamanho de amostra, base incondicional e **contagem de correção** (número de padrões examinados: 2+4+8+16=30 tabelas até k=4, além de definições de movimento futuro). Exibir como “ideias e caminhos falsos” do livro: apenas triagem.

**Benefício:** responde rapidamente se alguma sequência curta prevê direção num par/intervalo. **Complexidade:** baixa. **Riscos:** alto risco de testes múltiplos; autocorrelação/volatilidade em grupos fazem sequências parecer informativas; vantagens fracas somem com custos; não transformar em estratégia sem melhor de N e validação (livro 3). **Validação:** passeio aleatório sintético deve gerar cerca de 5% de tabelas “significativas” a p=0,05 antes da correção.

### O2 — Estudos de dia de reversão/lacuna como condicionamentos das mesmas tabelas *(livro: C5, pp. 731–732)*

Condicionar tabelas O1 pelo tipo de candle anterior (externo/interno, máxima maior com fecho menor etc.) e reportar abertura-fecho do próximo período. Resultados de índices do livro mostram que comportamento condicional pode divergir bastante da deriva incondicional. Em cripto, “abertura seguinte” é apenas abertura do próximo candle, sem lacuna; hipótese é persistência entre candles. **Complexidade:** baixa, com mesma cautela de testes múltiplos.

### O3 — Fluxo de rotulagem de resultados (ponte para livro 5) *(livro: C6, pp. 732–734)*

Definir resultado como “movimento de pelo menos x% em n dias sem movimento adverso maior que y%” é rótulo de **barreira**; marcar dias anteriores e buscar indicadores discriminantes equivale a aprendizado supervisionado. Antecipação de López de Prado (barreira tripla, meta-rotulagem), analisada no [livro 5](../05-advances-in-financial-ml-lopez-de-prado). Não implementar aqui: desenho pertence a essa análise (vazamento, rótulos sobrepostos, validação purgada).

### O4 — Formato de volume/horário como atributo, não regra *(livro: C3, pp. 689–690 · adaptação)*

Usar normalização de volume por hora e volatilidade (livro 4, cap. 12 O1), em vez de regras como “se a alta voltar à abertura às 13h”, dependentes de sessão de ações que cripto à vista não tem. **Complexidade:** parte do cap. 12 O1.

### Não aplicável

Projeções pivô/DeMark (sem evidência), padrões Tubbs/leitura de fita e estrutura de abertura/fecho de ações.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 diagnóstico de sequências | baixa | – | – | baixa | módulo de diagnósticos |
| 2 | O2 tabelas condicionais do próximo candle | baixa | – | – | baixa | O1 |
| 3 | O3 ponte de rotulagem | – | – | – | – | análise do livro 5 |
| 4 | O4 atributos horário/volume | baixa | – | – | baixa | cap. 12 O1 |

## 5. Arquivos afetados

`analytics/domain/` (contagem de sequências/condicionais), endpoint e página de diagnóstico no app e testes.

## 6. Plano incremental

1. Funções de tabulação e contagem de correções.
2. Relatório no app com comparação à hipótese nula.
3. Planejar rotulagem após livro 5.

## 7. Critérios de aceitação e testes

* Em passeio aleatório sintético, cerca de 5% das células excedem p=0,05 sem correção; dependência inserida é identificada; tudo somente leitura; Ruff, mypy e testes passam.

## Ressalvas

Estatísticas citadas referem-se a futuros/índices de ações (muitas vezes anos 1980–2000); algumas são “interessantes” sem teste de significância. São hipóteses de pesquisa, não evidência.
