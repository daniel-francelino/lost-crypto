# Livro 4 · Capítulo 10 — Sazonalidade e padrões de calendário

*Trading Systems and Methods*, 5.ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 427–436 (enquadramento, ressalvas dos dados, decomposição e remoção de tendência) e 478–483 (efeitos de calendário em ações) foram lidas. A parte intermediária longa (pp. 436–477: cálculo de médias/medianas sazonais, índices, filtros e exemplos de commodities) **não** foi lida em detalhe nem é resumida.

## 1. Resumo (páginas lidas)

| ID | Conceito | Problema que procura resolver | Páginas |
|---|---|---|---|
| C1 | Sazonalidade é **ciclo anual ligado a causas reais** (plantio/colheita, demanda de energia, viagens). Mesmo quando não é visível, persistem fatores (pressão de venda na colheita, custo de armazenamento nos preços futuros). Padrões podem enviesar tamanho de posição, sinalizar mudança de risco, afetar direção e ser explorados. Mudanças estruturais (oferta globalizada) alteram padrões. | Por que existem efeitos de calendário. | 427–428 |
| C2 | Padrões sazonais são mais fáceis de encontrar que ciclos longos, pois repetem-se a cada ano; estudar com **dados mensais** (intervalos menores têm mais ruído); iniciar ano num ponto neutro se início da temporada for desconhecido. | Método. | 429–430 |
| C3 | **Ressalvas dos dados**: futuros contínuos ajustados retroativamente não podem ser expressos em porcentagens e diferem de preços à vista (trigo em 1965: US$1,72 à vista versus US$12,45 ajustado); desdobramentos alteram percentuais históricos; preferir preços à vista em estudos sazonais. | Qualidade dos dados sazonais. | 430 |
| C4 | **Decomposição/remoção de tendência**: separar tendência, sazonalidade, ciclo e ruído (diferenças sazonais com período 12 em dados mensais e ~252 em diários); remover tendência por regressão e usar resíduos. Como tendência é deriva mensal constante, não muda formato sazonal. | Isolar componente sazonal. | 430–431 |
| C5 | **Efeitos de calendário em ações**: padrões **mudaram** entre 1982–2000 e anos seguintes (fraqueza de verão do S&P e “vender em maio” deixaram de valer regularmente; força outubro–novembro persistiu). “Só sobrevivem os padrões mais significativos”. **Efeito feriado** (Merrill, Fosback): dia antes de feriado subiu 67,9% das vezes (1897–1964), versus ~54% em dia comum. Estratégia de Fosback rendeu 880% em 1928–1975, 70% vencedoras e poucos dias expostos ao ano; Freeburg achou lucro ainda existente, mas menos impressionante. **Efeito de fim do mês**, **efeito/barômetro de janeiro**: em 12 anos até 2010, só 7 previsões corretas, saldo de 14 pontos (“confirmação, porém muito fraca”; eventos geopolíticos podem dominar). Regra de janeiro de McGinley tem qui-quadrado 8–82 na tabela, mas texto extraído está corrompido. | Efeitos de calendário e sua perda de força. | 478–483 |

Exemplos são futuros e ações dos EUA. Cripto não tem ciclo de colheita nem feriados de bolsa. Referências a cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Situação | Evidência |
|---|---|---|
| Recursos de calendário/tempo disponíveis às estratégias | ❌ | `StrategyContext` tem candle fechado e quantidade da posição; não há campos explícitos de calendário além de `candle.open_time` (que existe). |
| Decomposição sazonal/análise sem tendência | ❌ | Não consta nos diagnósticos. |
| Verificação de persistência por subperíodo | ❌ | Não há comparação temporal (livro 1, cap. 2 O5; livro 2, cap. 5 O1). |
| Gestão de mudança estrutural num padrão | ❌ | Nenhuma. |

## 3. Oportunidades

### O1 — Diagnósticos de calendário com teste de persistência *(livro: C2, C4, C5, pp. 430–431, 478–479)*

* **Problema:** operadores de cripto frequentemente presumem efeitos de dia/hora/mês; exemplo do S&P no livro mostra efeitos que aparecem numa era e desaparecem em outra.
* **Proposta:** ampliar diagnósticos (livro 2, cap. 2 O1 e cap. 4 O3) para calcular médias/medianas de retornos sem tendência por **hora UTC, dia da semana e dia do mês**, separadamente em **duas ou mais eras** (metade inicial/final ou por ano), exibindo amostras. Usar retornos percentuais (cripto à vista não tem problema de futuros ajustados) e remover tendência subtraindo média amostral (livro 3, cap. 1).
* **Benefício:** avaliação simples e honesta de estrutura de calendário e sua persistência. **Complexidade:** baixa a média (agregação pura).
* **Riscos:** seleção de dados em grupos 24×7×pares; declarar quantidade de grupos examinados e aplicar lógica do melhor entre N (livro 3, cap. 6). Padrões semanais/horários podem refletir volume regional; efeitos pequenos perante custos. **Validação:** dado sintético com efeito horário inserido; dados nulos produzem falsos grupos na taxa esperada (~5% com p=0,05 antes da correção).

### O2 — Filtro de janela temporal para estratégias atuais (só experimento) *(livro: C1, C5, pp. 428, 479–480)*

Se O1 encontrar janela persistente, adicionar filtro opcional de “horas/dias permitidos”, contando seus parâmetros em N. Efeito de feriado mostra como pequena exposição pode dominar retorno, padrão fácil de sobreajustar. **H-CALENDAR-WINDOW**; não desenvolver sem evidência de O1 que sobreviva ao fluxo. **Complexidade:** baixa.

### O3 — Usar eventos programados conhecidos para controlar exposição *(livro: C1, p. 428 · adaptação)*

O livro cita fatores sazonais para dimensionamento e mudanças de risco. Analogia cripto: desbloqueios de tokens, atualizações, manutenção de corretoras e eventos macro. Não há calendário de eventos no sistema (também B-EVENTS, livro 2, cap. 7). Apenas registrar; se desenvolvido, usar para **reduzir risco ou pausar**, não prever retornos.

### Não aplicável

Métodos sazonais agrícolas, preços à vista versus futuros, feriados de bolsas e regras de janeiro/barômetro.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Dependências |
|---|---|---|---|---|---|---|
| 1 | O1 diagnósticos de calendário | baixa–média | – | – | baixa–média | módulo de diagnósticos |
| 2 | O2 filtro de janela | baixa | – | – | baixa | evidência O1 |
| 3 | O3 calendário de eventos | – | média | – | média | B-EVENTS |

## 5. Arquivos afetados

`analytics/domain/` (agregação agrupada), `market_data/presentation/router.py`, diagnóstico da página de dados de mercado e testes.

## 6. Plano incremental

1. Funções de agregação e testes sintéticos.
2. Separação por eras e exibição da contagem de grupos em cada tabela.
3. Experimentar filtro somente se o efeito persistir fora da amostra.

## 7. Critérios de aceitação e testes

* Agregações conferem com cálculo manual; cada célula exibe tamanho amostral e quantidade de células examinadas.
* Diagnósticos são somente leitura; não alteram negociação; Ruff, mypy e testes passam.

## Ressalvas

Efeitos de feriados/janeiro são para ações dos EUA ao longo de décadas e, segundo o autor, enfraqueceram. Não sustentam efeito algum em cripto. Tabela da p. 483 (resultados McGinley) estava corrompida e não foi interpretada.
