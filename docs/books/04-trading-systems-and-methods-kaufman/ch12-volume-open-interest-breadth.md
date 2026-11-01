# Livro 4 · Capítulo 12 — Volume, posições em aberto e amplitude

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 527–530 e 554–558 foram lidas; títulos de pp. 536–553 e 559–564 foram percorridos. Catálogo de indicadores de volume (volume em saldo, índices de acumulação/amplitude, pp. 535–553), volume intradiário e filtros (559–564) **não** foram lidos em detalhe nem resumidos.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Volume é um dos poucos dados além do preço tradicionalmente aceitos por analistas técnicos; há pouca pesquisa em futuros. **Amplitude** (ações em alta/baixa e novas máximas/mínimas) e **posições em aberto** medem participação relacionada. Volume de futuros é específico ao contrato e aumenta quando ele se aproxima do vencimento; analisar **volume total** entre contratos. **Volume de ticks** (número de variações de preço) aproxima volume quando não há volume real. | Dados de volume e suas particularidades. | 527–529 |
| C2 | **Padrão intradiário em W**: volume alto na abertura, cai, sobe modestamente ao meio-dia, cai e aumenta até o fecho. Portanto, confirmação intradiária deve comparar volume com o **normal naquele horário**. Posições em aberto e amplitude também têm sazonalidade sem significado especial por si só. | Evitar leitura errada de volume intradiário. | 529 |
| C3 | **Variância do volume**: muito maior que a do preço (Microsoft: desvio-padrão do volume diário ~38% da média, versus 2,9% do preço); análise usa volume suavizado ou médio. | Ruído do volume. | 529–530 |
| C4 | **Picos de volume**: dia com volume ≥2× (talvez 3–4×) norma recente; interpretado como comportamento de multidão e, tradicionalmente, **exaustão** do movimento. Exemplos AOL/Microsoft mostram picos em viradas, “embora reversão nem sempre seja grande”. “Não há testes abrangentes disponíveis”. Detectar por `V_t > T × AV_{t−1}`; melhora **atrasando a média cinco dias**, para pico de 2–3 dias não se diluir na própria alta: `V_t > T × mean(V_{t−n−5} … V_{t−5})`. | Volume como detector de extremos. | 530, 554–555 |
| C5 | **Volume confirma ou sinaliza reversão**: muitos osciladores tratam volume alto como confirmação de nova direção e volume *extremo* como reversão; queda do volume sugere equilíbrio e exige confirmação adicional. | Dois usos do volume. | 554 |
| C6 | **Confirmação de volume para entrada tendencial**: exigir volume atual acima da média de dez dias para posição tendencial de 20 dias (Saitta); Waxenberg confirma mudança com aumento de 20% sobre média de dez dias e considera ~40% extremo; opcionalmente trocar percentuais por bandas Bollinger (2σ). Filtro “elimina quantidade substancial de operações”; **se retornos líquidos iguais, versão filtrada é muito melhor** (menos exposição, reversões e maior liquidez). | Filtrar operações por volume. | 556–557 |
| C7 | Sistemas de amplitude (padrão avanço/declínio Connors–Hayward e amplitude como indicador contrário) usam limites que devem ser reajustados com volatilidade (gatilho de 10 pb criado em 1995 agora negocia diariamente). | Limites que derivam. | 557–558 |

Detalhes de amplitude de ações/futuros não se aplicam. Adaptações cripto são **nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Volume armazenado | ✅ | `Candle.volume` persiste (`market_data/domain/models.py`). |
| Volume em estratégias/risco | ❌ | `StrategyContext` expõe candle, logo volume acessível, mas nenhuma estratégia o usa; `RiskLimits` não tem limite por volume (também livro 1, cap. 5). |
| Normalização intradiária | ❌ | Não há. |
| Detecção de picos | ❌ | Não há. |
| Filtro de confirmação por volume | ❌ | Não há. |
| Qual volume | ⚠️ | Volume é **por corretora e símbolo**; em cripto algumas bolsas podem inflá-lo por wash trading; cada corretora representa parcela do mercado (ponto ausente no livro). |
| Amplitude/posições em aberto | n/a | À vista, símbolo único. |

## 3. Oportunidades

### O1 — Volume relativo normalizado pelo horário *(livro: C2, C3, p. 529)*

Criar auxiliar `relative_volume = volume / média(volume no mesmo horário do dia nos últimos N dias)` (e variante sobre n candles anteriores), fundamento para regras de volume e controle de ciclos intradiários/semanais regulares como sinais (padrão W). Ciclos regionais de cripto ainda não foram verificados.

**Benefício:** referência correta para filtros/regras de risco com volume. **Complexidade:** baixa. **Validação:** série sintética com ciclo intradiário inserido deve ter volume relativo ≈1 ao longo do tempo.

### O2 — Detector de picos e diagnóstico de “exaustão” *(livro: C4, pp. 530, 554–555)*

Implementar teste de média defasada (`V_t > T × média(V_{t−n−5…t−5})`, `T=2` padrão, `n` configurável) e reportar retorno futuro após picos versus retorno futuro incondicional, por símbolo/intervalo, com tamanho de amostra e eras (estilo livro 4, cap. 10 O1). Testa afirmação tradicional “pico = exaustão”, sem testes abrangentes segundo o livro. **Complexidade:** baixa a média. **Riscos:** testes múltiplos (limite e horizonte); volume cripto depende da bolsa. **Validação:** série sintética com reversões pós-pico inseridas.

### O3 — Filtro de confirmação por volume nas entradas de tendência *(livro: C6, pp. 556–557)*

Parâmetro opcional nas tendências: entrar apenas se `relative_volume ≥ x` (ou volume exceder média n barras em ≥20%, ou banda 2σ). Livro afirma que filtro reduz operações e, se retorno não cair, reduz risco; testar em cripto. **H-VOLUME-FILTER**, contar em N, desligado por padrão. **Complexidade:** baixa a média. **Validação:** efeito sobre operações/drawdown pelo fluxo de validação; teste de truncamento.

### O4 — Usar volume para dimensionar posição e limitar liquidez *(livro: C1, C2; relacionado ao livro 1, cap. 5 O3)*

Mesmo volume relativo pode orientar limite (tamanho da ordem ≤ fração do volume recente) e filtro de candle suspeito (amplitude anormal com volume excepcionalmente baixo pode indicar preço incorreto). **Complexidade:** baixa a média; parte do trabalho de risco.

### Não aplicável

Posições em aberto, indicadores de amplitude, volume de mês de entrega, substituto volume de ticks e sistemas de avanço/declínio de ações.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 volume relativo | média | média | – | baixa | – |
| 2 | O4 volume no risco | – | média | média | baixa–média | O1; livro 1, cap. 5 O3 |
| 3 | O2 diagnóstico de picos | média | – | – | baixa–média | O1; módulo diagnóstico |
| 4 | O3 experimento de filtro | baixa | – | – | baixa–média | O1; fluxo de validação |

## 5. Arquivos afetados

`strategies/domain/` (auxiliar), `risk_management/domain/models.py` (limite opcional), `analytics/domain/`, endpoint de diagnósticos, formulários do app e testes, incluindo truncamento.

## 6. Plano incremental

1. Auxiliar de volume relativo com testes.
2. Diagnóstico de picos (somente leitura).
3. Limite de risco por volume (opcional).
4. Teste do filtro de volume pelo fluxo.

## 7. Critérios de aceitação e testes

* Volume relativo ≈1 em série com ciclo intradiário puro; detector sinaliza apenas picos inseridos; opções novas desligadas por padrão; Ruff, mypy e testes passam.

## Ressalvas

O próprio texto observa que não há testes abrangentes da regra de pico e as páginas lidas não dão números de desempenho dos filtros. Volume de uma única corretora talvez não represente atividade total do mercado.
