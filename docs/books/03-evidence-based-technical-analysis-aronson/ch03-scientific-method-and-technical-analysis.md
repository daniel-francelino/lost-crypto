# Livro 3 · Capítulo 3 — Método científico e análise técnica

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** o capítulo (pp. 103–163) é em grande parte uma história e filosofia da ciência (ciência grega, indução, dedução, Popper, Kuhn e outros; pp. 104–143). Li sua estrutura e, na íntegra, pp. 107–109 (objetividade e natureza do conhecimento científico), 144–147 e 160–163 (método hipotético-dedutivo, exemplo aplicado à análise técnica, objetivação do padrão cabeça-e-ombros e quatro classes de análise técnica). A história da filosofia nas pp. 104–143 **não** foi lida além dos títulos e não é resumida.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Conhecimento científico é **objetivo** (compartilhável e verificável), **empírico** e **quantitativo**; experiência subjetiva não pode ser verificada por terceiros. Preferir explicações simples (passeio aleatório em vez de ondas de Elliott, salvo se a teoria complexa fizer previsões melhores). | O que conta como evidência. | 107–109 |
| C2 | **Método hipotético-dedutivo**: observação → hipótese (o padrão não é artefato da amostra) → previsão (condicional: *se a hipótese for verdadeira, X será observado em novos dados*) → verificação em novas observações → conclusão por inferência estatística. Na prática, as etapas podem se sobrepor. | Procedimento para avaliar afirmações. | 144–145 |
| C3 | **Lógica do teste**: backtest lucrativo não prova a hipótese (afirmar o consequente é falácia); backtest não lucrativo pode refutá-la (negar o consequente). Portanto, formular **hipótese nula** (a regra não gera lucro) e *rejeitar a hipótese nula*. O raciocínio só é válido com observações novas e relevantes e estatística adequada. | Por que “funcionou no backtest” não é prova. | 145–146 |
| C4 | **Análise rigorosa dos resultados**: primeiro procurar explicações comuns para desempenho extraordinário: **acaso amostral** e **viés de seleção de dados**, antes de aceitar poder preditivo. | Ceticismo diante de bons resultados. | 146–147 |
| C5 | Pontos principais: hipótese nunca é provada conclusivamente; só é testável se permitir deduzir previsões sobre observações *ainda não realizadas*; hipótese que apenas explica o passado não é científica; comparar previsões com novas observações. | Critérios de evidência. | 147–148 |
| C6 | **Objetivar padrão subjetivo**, por exemplo cabeça-e-ombros. O estudo citado (Chang e Osler, “C&O”, mais de 3.100 sinais, 1962–1993) cria benchmark com **históricos de preços fictícios: variações reais reordenadas aleatoriamente**, preservando as estatísticas das ações reais, mas destruindo a estrutura temporal. Os padrões também aparecem nos dados falsos; sinais reais de cabeça-e-ombros perderam cerca de 0,25% em 10 dias, contra 0,03% nos dados fictícios. Outro estudo (Lo et al.) não conseguiu rejeitar que fossem “inúteis”. Outra fonte é descartada porque não define o padrão objetivamente nem considera a tendência do mercado. | Exemplo concreto de placebo. | 160–161 |
| C7 | **Quatro classes de análise técnica**: subjetiva; objetiva com significância desconhecida; objetiva, testada e **não significativa** (“inútil”, provavelmente a maioria, pois a maior parte das ideias propostas falha em todas as ciências); objetiva e significativa. EBTA abrange as duas últimas. O essencial é **ter procedimento para descartar métodos que não funcionam**. A maioria das regras provavelmente só agrega valor quando combinada. | Classificar e descartar métodos. | 161–163 |

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Testes objetivos, quantitativos e reproduzíveis | ✅ | Backtests determinísticos, com semente e hash SHA-256 dos candles registrados (`backtesting/domain/models.py`). |
| Formulação da hipótese nula | ❌ | Não há H₀ nem valor-p (livro 2, cap. 1 O1). |
| Teste com observações *novas* | ⚠️ | Existe reserva cronológica; paper é obrigatório antes da operação real (`live_min_paper_days`), constituindo teste prospectivo. Nenhum dos dois está ligado a hipótese formal. |
| Benchmark de preços fictícios (variações embaralhadas) | ❌ | Não implementado. |
| Classificação e descarte de regras inúteis | ❌ | Não há estados de ciclo de vida da estratégia (hipótese → testada/não significativa → útil) nem registro de falhas. |
| Combinação de regras fracas | ❌ | Estratégias são independentes. |

## 3. Oportunidades

### O1 — Placebo com retornos embaralhados (históricos de preços fictícios) *(livro: C6, pp. 160–161)*

* **Problema:** para saber se uma estratégia tem habilidade numa série, compará-la com a mesma estratégia em séries que preservam a distribuição dos retornos, mas não a estrutura temporal.
* **Proposta:** gerar históricos fictícios determinísticos com semente, **permutando os retornos reais por candle** (ou amostrando com reposição, extensão bootstrap nossa); executar a estratégia em N séries e apresentar a distribuição de retornos/Sharpe e a classificação da estratégia. É o teste concreto “Monte Carlo sobre preços simulados” descrito por Chan (livro 2, cap. 1 O1 etapa 3), usando permutação em vez de gerador do sistema de Pearson; assim fica implementável sem estatística adicional. O mesmo mecanismo produz o gráfico placebo (livro 3, cap. 2 O2).
* **Benefício:** hipótese nula sem distribuição paramétrica para estratégias de tendência/reversão; a estratégia precisa superar o que rende em dados sem tendência e com retornos idênticos. **Complexidade:** média (motor deve aceitar candles sintéticos, reconstruir OHLC a partir de retornos, decidir tratamento de máxima/mínima, calcular custos e executar lotes).
* **Riscos:** permutação destrói agrupamento de volatilidade, podendo facilitar demais a hipótese nula para rompimentos (agrupamento cria tendências aparentes); permutação em blocos pode mitigar. Milhares de execuções custam processamento. Uma boa classificação numa série não é prova. **Validação:** estratégia criada para explorar autocorrelação deve ficar entre as melhores em dados reais e no meio em dados embaralhados; estratégia aleatória deve ter classificação uniforme.

### O2 — Ciclo de vida da estratégia e “cemitério” *(livro: C7, pp. 161–163)*

* **Problema:** o sistema registra sucessos por padrão; o livro ressalta que a maioria das ideias falha e a disciplina exige aposentá-las com registro.
* **Proposta:** status para ideias/configurações: `hypothesis → tested_insignificant → useful → retired`, incluindo evidência (IDs de backtest, significância e motivo da aposentadoria). Mostrar ideias aposentadas no app para evitar repetição às cegas. Relaciona-se às notas/análise pós-morte (livro 2, cap. 4 O1) e pré-registro (livro 3, cap. 2 O3). **Complexidade:** baixa a média. **Validação:** testes de transição da API.

### O3 — Registrar previsão antes do teste *(livro: C2, C3, pp. 144–146)*

Explicitar hipótese → previsão no pedido de backtest (qual resultado a refutaria; por exemplo, “retorno excedente da estratégia sobre benchmark ajustado à exposição é positivo com p<0,05”), armazená-la com a execução e compará-la automaticamente ao resultado. Isso impõe possibilidade de refutação. **Complexidade:** baixa a média; relaciona-se ao livro 3, cap. 1 O1 (benchmark) e livro 2, cap. 1 O1 (significância).

### O4 — Combinar deliberadamente regras fracas *(livro: C7, p. 163 · hipótese apenas)*

O autor espera que a maioria das regras úteis só funcione em combinação. Não fazer nada antes de existir ferramenta de significância; registrar como **H-RULE-COMBINATION**.

### Não aplicável

História da filosofia da ciência; críticas a ondas de Elliott e cabeça-e-ombros (não há estratégias desse tipo).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O3 previsão registrada na execução | média | – | – | baixa–média | livro 3, cap. 1 O1; livro 2, cap. 1 O1 |
| 2 | O2 ciclo de vida/cemitério | média | média | – | baixa–média | notas |
| 3 | O1 placebo com retornos embaralhados | **alta** | – | – | média | reutilização do motor e executor de tarefas |
| 4 | O4 combinação | – | – | – | – | futuro |

## 5. Arquivos afetados

`backtesting/domain/` (gerador de candles sintéticos e executor placebo), `backtesting/application/service.py` (tarefas placebo), metadados em `strategies/`, novas tabelas para ciclo de vida/hipóteses, `docs/openapi.json`, páginas de backtest e estratégias no app e testes.

## 6. Plano incremental

1. Registrar texto de hipótese/previsão em cada execução (sem lógica adicional).
2. Criar status de ciclo de vida e lista de estratégias aposentadas.
3. Implementar placebo de retornos embaralhados, primeiro permutação simples e depois permutação em blocos.
4. Verificar previsão automaticamente com os resultados de significância.

## 7. Critérios de aceitação e testes

* A permutação preserva exatamente o conjunto de retornos e é determinística para uma semente.
* As classificações placebo comportam-se conforme os critérios de validação.
* Nenhuma mudança no comportamento de negociação; Ruff, mypy e testes existentes passam.

## Ressalvas

Os resultados cabeça-e-ombros (−0,25% contra −0,03% em 10 dias) referem-se a ações dos EUA de 1962–1993 e não são transferíveis. O capítulo defende um método, não uma regra específica. As seções filosóficas não foram lidas (ver nota acima).
