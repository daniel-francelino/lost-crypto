# Livro 3 · Capítulo 7 — Teorias do movimento não aleatório dos preços

*Evidence-Based Technical Analysis*, Aronson (2007). Páginas do livro (PDF = livro + 16; digitalização com OCR). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 331–333, 342–343, 355–357 e 378–385 foram lidas na íntegra. As seções centrais extensas (pp. 334–341, passeio aleatório e evidência de mercados eficientes; 344–354, críticas adicionais; 359–377, vieses comportamentais e padrões de preços previstos) foram lidas apenas pelos títulos e **não são resumidas em detalhe**. É um capítulo teórico, com pouco conteúdo operacional para o código.

## 1. Resumo do capítulo

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Análise técnica só se justifica se movimentos de preços forem não aleatórios em algum grau e período; ainda assim, cada *método* precisa comprovar seu mérito por evidências. | Premissa do livro. | 331 |
| C2 | **Importância da teoria**: backtest significativo sem teoria é resultado isolado e possivelmente sortudo; resultado compatível com teoria sólida integra um “quadro mais coerente”. Exemplo: tendência em futuros de commodities como **prêmio de risco** por transferir risco dos hedgers. Teoria científica explica várias observações e gera **previsões testáveis**. | Distinguir acaso de efeitos reais. | 332 |
| C3 | **Crítica a teorias populares de análise técnica**: “o preço reflete tudo” contradiz a ideia de que padrões preveem preços (e é premissa da hipótese de mercados eficientes); justificativas vagas e improvisadas não geram previsões testáveis; “psicologia popular” não tem suporte científico. | Justificativas frágeis. | 333 |
| C4 | **Hipótese de mercados eficientes (HME) é questionada por seus paradoxos**: *inteligentes versus tolos* (arbitragem exige que os inteligentes tenham mais capital, mas eficiência diz que não ganham mais); *custo da informação* (ninguém pagaria para obter informação sem retorno: Grossman e Stiglitz). Custos de negociação e limites à venda a descoberto impedem eficiência plena. | Por que ineficiências são logicamente possíveis. | 342–343 |
| C5 | **Finanças comportamentais** para explicar movimento não aleatório: dois pilares, **limites à arbitragem** (risco, capital, paciência limitada) e **limites à racionalidade** (erros cognitivos sistemáticos). Preços podem reagir menos (tendências) ou exageradamente (reversões) em circunstâncias previsíveis. HME atribui desvios ao acaso e à curta duração; finanças comportamentais sustenta desvios sistemáticos que duram o suficiente para serem explorados. O autor observa que ainda não se sabe quais hipóteses específicas estão corretas. | Mecanismos por trás de tendências e reversões. | 355–357, 378 |
| C6 | **Movimento não aleatório pode coexistir com eficiência**: diferenças de aversão a risco criam **prêmios de risco** — prêmio de ações; **prêmio de hedge de commodities/moedas** (tendências lucrativas para seguidores de tendência); **prêmio de liquidez** (ganhos curtos ao comprar fraqueza recente: estratégias contrárias); **prêmio de informação/descoberta de preços**. Prêmios tendem a durar mais que ineficiências verdadeiras, que são efêmeras; assumir risco sem critério não gera prêmio. Sinais técnicos podem ser vistos como “anúncios de procura” por risco ou liquidez. | O que torna uma vantagem duradoura. | 378–385 |

## 2. Diagnóstico

| Conceito | Situação | Evidência |
|---|---|---|
| Justificativa de cada estratégia | ⚠️ | Docstrings descrevem regras mecânicas (`ema_crossover.py`, `donchian_breakout.py`) e catálogo tem textos `DESCRIPTION`, mas não mecanismo econômico/comportamental, previsão refutável ou regime de falha conhecido. |
| Previsões testáveis ligadas a mecanismo | ❌ | Não registradas; diagnósticos (livro 2, caps. 2 e 6) seriam o local. |
| Classificação como prêmio ou ineficiência | ❌ | Não há. |
| Estrutura específica de cripto conhecida | ❌ | Ausente do sistema e da documentação. |

## 3. Oportunidades

### O1 — Bloco de tese por estratégia: mecanismo, previsão e regime de falha *(livro: C2, C3, C6, pp. 332–333, 378–385)*

* **Problema:** estratégias descrevem o que fazem, não por que deveriam funcionar; um bom backtest fica isolado, sem critério para aposentá-las quando o mecanismo muda.
* **Proposta:** ampliar metadados (`catalog.py`/`base.py`) com (a) mecanismo hipotético (por exemplo, “reação tardia e efeito manada geram tendência em N horas”; “oferta de liquidez após venda forçada gera reversões”); (b) *previsão observável* que a refutaria, ligada a diagnóstico (autocorrelação no horizonte, livro 2, cap. 6 O1; meia-vida, cap. 2 O1); (c) classificação como **prêmio de risco/liquidez** (mais duradouro) ou ineficiência explorável (efêmera); (d) condições de falha. Exibir no app junto aos parâmetros e resultados.
* **Benefício:** vincula pesquisa a afirmações testáveis, notas pós-morte (livro 2, cap. 4 O1) e pré-registro (livro 3, cap. 2 O3 e cap. 3 O3). **Complexidade:** baixa (metadados e interface). **Risco:** texto pode virar decoração; só ajuda se a previsão for verificada por diagnóstico. **Validação:** todas as estratégias registradas precisam preencher o bloco (teste do catálogo).
* Mecanismos específicos de cripto são **propostas nossas**; o livro oferece estrutura teórica (prêmios de risco, reação insuficiente/exagerada e limites à arbitragem), não evidência sobre cripto.

### O2 — Diagnóstico que verifica a previsão da própria estratégia *(livro: C2, p. 332)*

Implementar diagnósticos citados em O1 (autocorrelação/meia-vida no intervalo da estratégia; persistência de tendência após choques de volume/volatilidade, como possibilidade) e apresentar estado confirmado/refutado/inconclusivo por par e intervalo. Depende do livro 2, cap. 2 O1 e cap. 6 O1; não é trabalho separado. **Complexidade:** conforme dependências.

### O3 — Plano para durabilidade da vantagem *(livro: C6, p. 380 · adaptação)*

Registrar em cada bot implantado se a tese é prêmio ou ineficiência e definir frequência de revisão: teses efêmeras exigem monitoramento mais frequente (monitor de deterioração, livro 2, cap. 4 O1). **Complexidade:** baixa. **Risco:** classificação subjetiva.

### Não aplicável

Debate sobre HME, evidências de passeio aleatório, vieses comportamentais específicos (não lidos em detalhe) e modelos de fatores de ações.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 metadados da tese | média | média | – | baixa | – |
| 2 | O2 verificar previsão | alta | – | – | conforme dependências | livro 2, caps. 2/6 |
| 3 | O3 revisão de durabilidade | – | média | – | baixa | monitor de deterioração |

## 5. Arquivos afetados

`strategies/domain/base.py`, `strategies/catalog.py`, `strategies/presentation/` (schema), `docs/openapi.json`, páginas de estratégias no app e `lib/shared/strategies`, `check:consistency` e testes do catálogo.

## 6. Plano incremental

1. Adicionar metadados e preenchê-los para as duas estratégias existentes.
2. Exibi-los no app.
3. Vincular aos diagnósticos O2 à medida que forem criados.

## 7. Critérios de aceitação e testes

* Toda estratégia registrada informa mecanismo, previsão e regime de falha; teste falha se faltar algum.
* Comportamento das estratégias não muda; Ruff, mypy e testes passam.

## Ressalvas

Teorias explicam e limitam hipóteses, não garantem resultados. O próprio livro afirma que não está claro quais hipóteses comportamentais são corretas (p. 378). Grande parte do capítulo (detalhes de comportamento e HME) não foi lida em profundidade.
