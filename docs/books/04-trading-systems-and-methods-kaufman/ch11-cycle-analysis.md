# Livro 4 · Capítulo 11 — Análise de ciclos

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 485–489 foram lidas. Métodos de detecção (análise de Fourier/espectral, ajuste trigonométrico), entropia máxima (MESA), índice de canal cíclico, indicador de ciclo curto e faseamento (pp. 494–526) foram percorridos apenas pelos títulos e **não** são resumidos. Apêndice 3 (regressão trigonométrica) não foi lido.

## 1. Resumo (páginas lidas)

| ID | Conceito | Páginas |
|---|---|---|
| C1 | **Ciclo** é um dos três componentes ordenados de preço (tendência, sazonalidade e ciclo; o quarto é ruído). Tipos: sazonal, início/parada de produção, inventário, comportamental, astronômico e eleição presidencial. Pode ser periódico (intervalo regular) ou amplitude regular e período irregular. Métodos comuns: ajuste de curvas trigonométricas e análise Fourier/espectral; entropia máxima de Ehlers funciona com poucos dados. Ciclos curtos são atribuídos ao comportamento (cap. 15). | 485 |
| C2 | Para isolar componente, remover os outros: primeiras diferenças retiram tendência; subtrair média de um ano (ou valor de 252 dias antes) remove sazonalidade, restando ciclo e ruído. Referência de 20 dias úteis corresponde ao mês lunar e quatro semanas. Ciclos frequentemente somam subciclos harmonicamente relacionados; qualquer série pode ser decomposta. | 486 |
| C3 | **Antes de analisar, verificar ciclo dominante e entender sua causa para evitar padrões espúrios**: razões fundamentais/industriais (inventário, tempo de reprodução/alimentação, fechamento/retomada de minas, política de juros). Exemplo: **ciclo do gado** claro de 9–11 meses (picos variam até um mês, variância ~20%) com causa produtiva; **ciclo do franco suíço** tem subciclo de 24–35 semanas (variância 40%), sem causa fundamental específica; padrões “não precisam ser rígidos”. | 486–487 |

## 2. Diagnóstico

| Conceito | Situação | Evidência |
|---|---|---|
| Análise espectral/cíclica | ❌ | Não há Fourier, MESA nem código de ciclos. |
| Exigir causa plausível para padrão | ❌ (processo) | Ver livro 3, cap. 7 O1 (bloco de tese). |
| Estratégias baseadas em ciclos | ❌ | Nenhuma. |

## 3. Oportunidades

### O1 — Aplicar regra “primeiro a causa” às hipóteses de ciclo; ainda não criar ferramentas espectrais *(livro: C3, p. 486)*

A lição metodológica mais reutilizável é que um ciclo sem explicação causal provavelmente é espúrio. Folclore cripto sugere ciclos plurianuais (por exemplo, em torno de redução de emissão), mas histórico disponível contém poucos ciclos, quase sem poder estatístico; ciclos do livro têm variação de período de 20–40% mesmo em mercados entendidos. **Recomendação:** não implementar detecção cíclica agora. Se houver hipótese, registrá-la com mecanismo e previsão que a refute (livro 3, cap. 7 O1) e testar pelo fluxo, contando cada período tentado em N. Registrar **H-CYCLES**. **Complexidade se construída:** média–alta (estimativa espectral em funções puras).

### O2 — Remover tendência/sazonalidade antes de procurar estrutura *(livro: C2, p. 486)*

Quando módulo de diagnósticos (calendário, livro 4, cap. 10 O1) crescer, retirar primeiro média/tendência (primeiras diferenças ou série de retornos), evitando que tendência mascare componentes. Já incluído nesses itens.

### Não aplicável

Ciclos astronômicos/presidenciais, gado e moedas específicos, implementação de MESA/Fourier (não lida).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 regra de hipótese | – | – | – | nenhuma | bloco de tese |
| 2 | O2 nota sobre remoção de tendência | – | – | – | trivial | diagnósticos |

## 5–7. Arquivos, plano e aceitação

Não há código proposto. Apenas documentação: incluir diretriz “primeiro a causa” nas orientações de tese de estratégia.

## Ressalvas

Exemplos de gado/franco suíço são observações gráficas de futuros de 1980–2002; as páginas lidas não reportam significância estatística. Nada demonstra ciclos cripto.
