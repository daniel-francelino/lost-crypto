# Livro 3 · Capítulo 9 — Resultados do estudo de caso e futuro da análise técnica (e apêndice)

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 441–448, 455–465 e a estrutura dos títulos em 449–454 e 466–474 foram lidas. A tabela das 100 melhores regras (pp. 445–446) foi apenas observada rapidamente. O restante da crítica ao estudo de caso (449–454), fim da discussão sobre combinações de aprendizado de máquina (465–474), **Apêndice** (prova de que remover tendência equivale a benchmark com o mesmo viés de posição, pp. 475–476) e notas **não** foram lidos em detalhe.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | **Resultado:** nenhuma das 6.402 regras teve retorno médio suficiente para rejeitar a hipótese nula ao nível 0,05 após corrigir seleção de dados. Melhor regra: **10,25% ao ano em dados sem tendência**; valor-p corrigido por seleção: **0,8164** (bootstrap) e **0,8194** (permutação), abaixo do centro da distribuição amostral. | Resultado honesto de uma grande busca. | 441–442 |
| C2 | **Hipótese nula do melhor de N não é centrada em zero**: para as 6.402 regras, retorno esperado da melhor entre N regras inúteis é cerca de **11% ao ano**, não zero; acima de ~15% seria significativo a 0,05 e acima de ~17% altamente significativo (p < 0,001). Depende de N, quantidade de observações, correlação entre regras e dados. | Calibrar “quão bom precisa ser”. | 442–443 |
| C3 | **Teste ingênuo teria induzido ao erro**: teste comum de regra isolada daria p=0,0005 para a melhor; cerca de **320 das 6.402 regras (~5%)** pareceriam significativas a 0,05, exatamente o esperado pelo acaso. | Escala do ouro de tolo. | 443–444 |
| C4 | Intervalos de confiança que consideram seleção de dados são intervalos **conjuntos** (80%) para todas as regras (ex.: melhor regra: −2,9% a +23,5%); relatam-se três testes (bootstrap aprimorado, Reality Check original e Monte Carlo aprimorado). Nível de 5% mantém chance de 1 em 20 de falsa rejeição mesmo neste desenho. | Relatar incerteza. | 444–448 |
| C5 | **Crítica positiva ao estudo**: usou benchmark sem habilidade; controlou tendência do mercado (remoção da tendência); controlou antecipação (execução na abertura do dia seguinte); controlou viés de seleção de dados e evitou espiar os dados. | Lista de verificação do desenho. | 448–449 |
| C6 | **Extensões do estudo**: combinar regras **linearmente** (votação por maioria; **posição fracionária** proporcional à diferença líquida entre regras compradas/vendidas num tema, Hsu e Kuan); aprender regras (escolher a melhor recentemente); indicadores de difusão (fração de regras compradas); remover regras inversas para evitar soma zero. **Regras não lineares induzidas por máquina** (redes neurais, árvores, SVM, programação genética) exigem busca de parâmetros *e* complexidade; em 2007, segundo o autor, não existia teste de significância robusto para isso. | Próximos caminhos. | 455–457 |
| C7 | **Esquema de três segmentos para busca de complexidade**: treino, teste e **validação**. Ciclo interno: otimizar parâmetros numa complexidade dada sobre treino; externo: aumentar complexidade enquanto o desempenho no **teste** melhora; parar quando atingir pico e piorar (fronteira entre sobreajuste/subajuste); então o **segmento de validação**, intocado até esse momento, fornece a única estimativa não enviesada (resultado de teste sofre viés por consultas repetidas). Também pode ser walk-forward, deslizando janela tripartida. Exemplo: cruzamento de médias com 2 parâmetros, 30% treino/15% teste; adicionar filtro RSI (4 parâmetros), 50%/20%; continuar até resultado de teste cair. | Controlar sobreajuste ao adicionar regras. | 457–461 |
| C8 | **Futuro da análise técnica**: deve tornar-se baseada em evidências ou será marginalizada; previsões de especialistas mal superam não especialistas (boletins de Armstrong, Cowles e Hulbert: menos de 10% superaram índice amplo em dez anos). Limite da EBTA: experimentos controlados são impossíveis e **o mesmo histórico é reutilizado**, alimentando viés de seleção; regressão pode controlar parcialmente fatores de confusão (Fosback; Jacobs e Levy encontraram reversão mensal de ações fracas como efeito forte e consistente). **Parceria humano–computador**: pessoas propõem hipóteses e são ruins em descartá-las; computadores combinam muitas variáveis, mas sofrem com a **maldição da dimensionalidade** (densidade de dados cai exponencialmente com indicadores). | Direção do campo. | 461–465 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Relato honesto de busca ampla | ❌ | Varredura lista resultados sem referência do melhor entre N (ver cap. 6). |
| Limite calibrado de resultado “suficientemente bom” | ❌ | Não se estima que retorno seria incomum para o tamanho da grade. |
| Significância ingênua e corrigida lado a lado | ❌ | Nenhuma. |
| Disciplina dos três segmentos (treino/teste/validação) | ⚠️ | Há treino/teste, sem validação; segmento de teste é reutilizado em cada seleção. |
| Combinação linear (votação/posição fracionária) | ❌ | Um bot por estratégia; posição investida por inteiro ou neutra (contrato não tem tamanho-alvo). |
| Aprender/reselecionar regras recentes | ❌ | Não existe. |
| Maldição da dimensionalidade/controle de indicadores | ✅ por construção | Estratégias têm baixa dimensionalidade. |
| Reutilização do histórico | ⚠️ | Mesmos candles em experimentos; contagem não registrada. |

## 3. Oportunidades

### O1 — Exibir retorno “necessário para ser incomum” na varredura *(livro: C2, C3, pp. 442–444)*

* **Problema:** resultado de +40% não mostra se é excepcional *para uma grade desse tamanho*.
* **Proposta:** a partir da distribuição de permutação do melhor entre N (livro 3, cap. 6 O1), mostrar junto ao melhor resultado mediana e percentil 95 do nulo “melhor de N”, retornos necessários para p=0,05 e p=0,001 e quantidade de células que pareceriam significativas por acaso (≈5% × N com regras independentes). **Complexidade:** baixa após cap. 6 O1. **Validação:** numa varredura aleatória, ~5% das células excedem o limite de regra única.

### O2 — Protocolo de três segmentos (treino/teste/validação) com validação bloqueada *(livro: C7, pp. 457–461)*

Ampliar configuração de `test_fraction` para `validation_fraction` opcional; ocultar validação de varreduras e classificações; avaliar apenas quando operador **confirma** uma configuração escolhida e registrar confirmação na auditoria para marcar o segmento como consumido. Depois, avisar que já não fornece estimativa sem viés (livro 3, cap. 6 C7). **Complexidade:** média (segmentos, estado de bloqueio e interface). **Risco:** operador pode criar novos dados “de validação” mudando datas; auditoria e contagem de universo (cap. 6 O2) limitam o problema. **Validação:** API confirma que classificação ignora validação e sinaliza segunda avaliação do mesmo segmento.

### O3 — Regra de parada por complexidade *(livro: C7, pp. 459–461)*

Ao adicionar condições/parâmetros, informar desempenho de treino e teste por nível de complexidade e marcar o primeiro nível em que o teste deixa de melhorar (fronteira de sobreajuste/subajuste). Na prática: registrar sequência de variantes de estratégia (número de parâmetros) num estudo e representar treino versus teste. **Complexidade:** baixa a média (estudos do livro 3, cap. 2 O3 e cap. 6 O2). Só faz sentido com mais de uma família.

### O4 — Combinação linear de regras como pesquisa *(livro: C6, pp. 455–456)*

Combinar várias regras simples do mesmo tema por votação ou posição fracionária é o próximo passo sugerido pelo livro. Exige (a) múltiplas estratégias num bot ou estratégia de sinal combinado e (b) sinal de posição-alvo/tamanhos parciais no contrato (mesmos pré-requisitos B-SCALE-IN e B-TRANCHES). Registrar **H-VOTE**; não desenvolver antes da ferramenta de significância e da decisão sobre esses itens. Regras inversas não se aplicam (apenas comprado).

### O5 — Regressão para controlar fatores de confusão em diagnósticos *(livro: C8, p. 464 · apenas referência)*

O livro cita indicadores “purificados” por regressão. Analogia cripto seria regredir retornos por barra da estratégia em fatores gerais, como retornos de BTC, para isolar desempenho não explicado pelo mercado. É adaptação nossa; requer contexto multiativo (B-MULTI-ASSET) e deve esperar.

### Não aplicável

Classificação de boletins e especialistas. O apêndice não foi lido, mas seu resultado (remoção da tendência equivale a benchmark com mesmo viés) é aplicado no livro 3, cap. 1 O1.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 exibir retorno necessário | alta | – | – | baixa | livro 3, cap. 6 O1 |
| 2 | O2 validação bloqueada | **alta** | – | – | média | livro 3, cap. 6 O2 |
| 3 | O3 parada por complexidade | média | – | – | baixa–média | estudos |
| 4 | O4 votação | média | – | – | alta | contrato de sinais |
| 5 | O5 regressão | baixa | – | – | alta | multiativo |

## 5. Arquivos afetados

`backtesting/domain/models.py` (`validation_fraction`), `backtesting/domain/segments.py`, `backtesting/application/service.py` (confirmação/bloqueio), eventos de auditoria, `docs/openapi.json`, páginas de backtest/varredura e testes.

## 6. Plano incremental

1. Exibição do retorno necessário após a implementação do melhor entre N.
2. Segmento de validação com confirmação/bloqueio e auditoria.
3. Gráfico de treino/teste por complexidade no estudo.
4. Votação/posição fracionária como projeto separado (depende de decisão sobre contrato de sinais).

## 7. Critérios de aceitação e testes

* Classificações e varreduras nunca consultam validação antes da confirmação.
* Segunda avaliação de segmento consumido gera aviso visível e registro de auditoria.
* Execuções e APIs existentes continuam compatíveis; Ruff, mypy e testes passam.

## Ressalvas

O resultado de que **nenhuma regra foi significativa** refere-se a dados do S&P 500 de 1980–2005 e às regras testadas; não prova que regras técnicas nunca funcionem ou que regras cripto não funcionem. O autor espera efeitos fracos e raros; a questão interessante é como avaliar uma busca, não qual regra venceu.
