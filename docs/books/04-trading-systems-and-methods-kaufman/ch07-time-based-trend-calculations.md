# Livro 4 · Capítulo 7 — Cálculos tendenciais baseados no tempo

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 279–281 e 293–304 foram lidas. Média móvel simples e variantes (pp. 281–292: ponderada, triangular e geométrica) e fim do capítulo sobre representação de atrasos/avanços (pp. 305–308) **não** foram lidos em detalhe. EMA, usada por `ema_crossover`, aparece na parte lida.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Métodos tendenciais removem ruído para revelar direção; podem coexistir várias tendências; **não há tendência “correta”, apenas benefícios e concessões**. Modelos preditivos degradam ao **extrapolar fora da faixa histórica**. Distinguir **previsão** (preço com confiança) de **acompanhamento** (avaliação autorregressiva da direção atual: alta/baixa/lateral). Seguidores presumem que passado indica direção futura. | O que um filtro tendencial oferece. | 279–280 |
| C2 | **Atraso é zona de incerteza** que permite ignorar ruído; reduzi-lo aumenta falsos sinais. Melhores resultados históricos muitas vezes decorrem de **sobreajuste**. | Concessão entre atraso e ruído. | 280 |
| C3 | **Efeito de descarte** (mudança abrupta quando dado antigo sai da janela, `(p_t − p_{t−n})/n`): médias simples, regressões e ponderadas sofrem; ponderação frontal e **suavização exponencial** reduzem efeito. Médias acumuladas dependem da data inicial. | Comportamento de filtros por janela. | 293 |
| C3b | **Suavização exponencial**: `E_t = E_{t−1} + a·(p_t − E_{t−1})`, inicializada em `E₁ = p₁`; desenvolvida na Segunda Guerra para rastreamento. Conversão de dias `a = 2/(n+1)` (Hutson) ignora atraso; fórmula geral de impacto residual `c = 1 − RI^{1/n}`. Com `2/(n+1)`, impacto residual dos dados antigos é constante, **13–14%**. | Definição e equivalência da EMA. | 293–298 |
| C4 | **EMA versus média simples**: não são equivalentes; exponencial nunca descarta dados antigos, então suavização “10%” é mais lenta que MA de 10 dias. Em rampa estável, MA de cinco dias estabiliza com atraso 1; EMA de 20% apenas se aproxima e **muda de direção um período após o pico**. | Por que sinais EMA/SMA diferem. | 298–299 |
| C5 | **Distribuição de testes**: constantes de suavização igualmente espaçadas fazem metade dos testes corresponder a médias de três dias ou menos; **espaçar constantes igualmente é melhor distribuição de testes que espaçar dias igualmente**; relação constante/dias é quase logarítmica. | Grades de parâmetros para otimização. | 299–301 |
| C6 | **Reduzir atraso/suavizar**: suavização com correção de erro (suavizar atraso `e_t = p_t − E_t` e somá-lo; linha corrigida fica no meio do movimento, “boa candidata” à reversão à média); **suavização dupla** torna linha mais lenta, com pesos triangulares; **suavização dupla das variações de preço** de Blau (momentum) recupera velocidade, com primeira suavização longa e segunda curta (ex.: 250/5), mas resultado deixa de estar na escala de preço. | Técnicas de redução de atraso. | 301–304 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Definição de EMA | ✅ | `ema_crossover.py`: `alpha = 2/(period+1)`, inicializada com **SMA dos primeiros `period` fechamentos** e atualizada incrementalmente. Livro inicializa `E₁=p₁`; ambas são válidas, diferem apenas no aquecimento inicial. |
| Tratamento do aquecimento | ✅ | Sem sinal durante aquecimento e no candle em que termina (documentado no módulo). |
| Efeito de descarte de janela fixa | n/a | Só há EMA. |
| Grades da constante de suavização | ⚠️ | Estratégia recebe períodos inteiros; grades lineares são densas em períodos longos e esparsas nos curtos. |
| Atraso como característica apresentada | ❌ | Não é mostrado. |
| EMA com correção de erro/suavização dupla/momentum Blau | ❌ | Não existe. |
| Cuidado com extrapolação fora da faixa | n/a | Não há previsões. |

## 3. Oportunidades

### O1 — Grades logarítmicas para períodos (confirma espaçamento ×1,5 de Aronson) *(livro: C5, pp. 299–301)*

Argumento de Kaufman (passos iguais na constante superam passos iguais em dias; relação quase logarítmica) reforça a grade geométrica proposta no livro 3, cap. 8 O1. Acrescentar justificativa à documentação do auxiliar de varredura e oferecer gerador em períodos ou constantes de suavização. **Complexidade:** muito baixa.

### O2 — Mostrar atraso esperado de cada filtro tendencial *(livro: C2, C4, pp. 280, 298–299)*

Exibir atraso aproximado das EMAs rápida/lenta e impacto residual efetivo, explicando compromisso velocidade/ruído. Para rampa estável de uma unidade por barra, EMA com constante `a` fica `(1−a)/a` unidades atrás em regime estacionário; por exemplo, 4 para `a=0,2` (resultado padrão derivado da definição, não apresentado assim pelo livro). Compatível com Tabela 7.7: subida de uma unidade por barra, EMA 20% fica 3,83 abaixo no ponto 15 e se aproxima de 4. Fórmula fechada é nossa; testar contra a tabela. **Complexidade:** muito baixa (exibição).

### O3 — Permitir constante de suavização diretamente nas varreduras *(livro: C3b, C5, pp. 295–301)*

Opcional: velocidade EMA ainda expressa em `n` dias, mas gerar `n` por gerador logarítmico (O1), sem novo parâmetro. Baixa prioridade; em grande parte coberto por O1.

### O4 — Variantes de redução de atraso como experimentos *(livro: C6, pp. 301–304)*

Suavização dupla de momentum (Blau) e EMA corrigida por erro são indicadores objetivos com parâmetros. Acrescentam parâmetros (duas janelas); autor alerta que melhores resultados históricos muitas vezes vêm de sobreajuste. Registrar **H-LAG-REDUCTION**; testar apenas com fluxo de evidências e contando parâmetros em N. **Complexidade:** média.

### Não aplicável

Médias acumuladas/geométricas e gráficos de atrasos/avanços (não lidos).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 grades logarítmicas | média | – | – | muito baixa | livro 3, cap. 8 O1 |
| 2 | O2 exibir atraso | baixa | – | – | muito baixa | – |
| 3 | O3 varredura por constante | baixa | – | – | baixa | O1 |
| 4 | O4 variantes de redução de atraso | baixa | – | – | média | fluxo de validação |

## 5. Arquivos afetados

Formulário/auxiliar de varredura, `strategies/domain/ema_crossover.py` apenas para exibição, documentação e testes.

## 6. Plano incremental

1. Documentar justificativa da grade e publicar gerador.
2. Adicionar indicação de atraso/impacto residual ao formulário.
3. Testar variantes somente pelo fluxo.

## 7. Critérios de aceitação e testes

* Testes do gerador e, em O2, do atraso calculado comparado à EMA de 20% da Tabela 7.7.
* Estratégias atuais não mudam; Ruff, mypy e testes passam.

## Ressalvas

Impacto residual de 13–14% e equivalências de suavização são propriedades matemáticas gerais da EMA; distribuição de testes é recomendação prática do autor. Fórmula fechada de atraso de O2 é nossa, verificada apenas contra Tabela 7.7.
