# Livro 5 · Capítulo 3 — Rotulagem

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 43–54 (rotulagem de horizonte fixo, limites dinâmicos, barreira tripla, lado e tamanho, meta-rotulagem, uso e início de remoção de rótulos) foram lidas. Exercícios e detalhes do código `dropLabels` não foram lidos; trechos foram consultados superficialmente.

**Por que este capítulo importa para a plataforma:** a lógica de negociação já tem estrutura de **barreira tripla** (stop-loss, take-profit e sinal de saída como barreira vertical). Meta-rotulagem é a forma do livro de adicionar uma camada de ML **sobre** uma estratégia baseada em regras existente (como `ema_crossover`), sendo a ideia mais diretamente aplicável.

## 1. Resumo do capítulo

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Aprendizado supervisionado exige rótulos `y` associados às linhas de atributos `X`. **Método de horizonte fixo** rotula `y_i ∈ {−1, 0, 1}` pelo retorno em `h` barras versus limite `τ`. Evitá-lo: (1) barras temporais têm propriedades estatísticas ruins (cap. 2); (2) um `τ` para todos os regimes de volatilidade gera muitos zeros em períodos calmos (ex.: τ = 1% enquanto volatilidade da barra vai de 0,01% a 1%); (3) **ignora o caminho do preço**: estratégias reais têm stop, chamada de margem ou limites; “é simplesmente irrealista criar estratégia lucrando com posições que teriam sido encerradas pelo stop”. | Rótulos inadequados. | 43–44 |
| C2 | **Limites dinâmicos**: definir larguras de realização e stop em função da volatilidade estimada, por exemplo desvio-padrão exponencialmente ponderado e móvel dos retornos (trecho 3.1, extensão em dias). | Barreiras escaladas ao risco. | 44 |
| C3 | **Método da barreira tripla**: duas barreiras horizontais (realização de lucro e stop, larguras = fator × volatilidade-alvo) e uma vertical (tempo máximo de permanência em barras). Rótulo vem da **primeira barreira tocada**: superior +1, inferior −1; vertical: sinal do retorno (ou 0). É **dependente do caminho**. Oito combinações `[pt, sl, t1]`: `[1,1,1]` padrão; `[0,1,1]`; `[1,1,0]`; `[0,0,1]` = horizonte fixo; `[1,0,1]`; `[1,0,0]`; `[0,1,0]`; `[0,0,0]` inválida. Barreiras horizontais não precisam ser simétricas. Custo computacional de até `I × h` condições (10⁹ para I = 1e6, h = 1e3), logo paralelismo. | Rótulos sensíveis ao caminho. | 45–47 |
| C4 | **Aprender lado e tamanho**: quando nenhum modelo determina o lado, barreiras devem ser simétricas (ou ausentes), pois não se distingue realização de lucro de stop sem direção. `getEvents` encontra primeiros toques para timestamps de eventos (amostragem do cap. 2), com retorno mínimo `minRet`; barreira vertical pode ser a barra seguinte a `numDays`. | Rotulagem de lado e tamanho. | 48–49 |
| C5 | **Meta-rotulagem**: quando modelo primário (regra, econométrico ou discricionário) já decide o **lado**, treinar modelo binário **secundário** para decidir operar (1) ou passar (0), ou seja, tamanho incluindo zero; rótulos vêm do **P/L condicionado ao lado** (permite barreiras assimétricas). Probabilidade do modelo secundário pode dimensionar aposta. Rótulos binários `{0, 1}`, em vez de `{−1, 0, 1}`. | Aprender tamanho da aposta sobre lado conhecido. | 50–51 |
| C6 | **Uso**: matriz de confusão, precisão/recall e F1 (média harmônica). Usar modelo primário com **recall alto** (mesmo com precisão baixa) e deixar meta-modelo filtrar falsos positivos para aumentar F1. Quatro motivos adicionais: (1) transforma modelo caixa-branca em sistema ML; (2) **limita sobreajuste**, pois ML não escolhe o lado; (3) modelos meta separados para comprado/vendido, com atributos distintos; (4) “alta precisão em apostas pequenas e baixa nas grandes arruína você” — dimensionamento importa tanto quanto seleção. O livro afirma, com base na experiência, que meta-rotulagem “pode produzir resultados mais robustos e confiáveis que modelos de rotulagem padrão” (sem dados apresentados). | Por que meta-rotulagem funciona. | 51–53 |
| C7 | **Abordagem quantamental**: acrescentar meta-rotulagem a decisões discricionárias/técnicas; atributos podem incluir estado do mercado, quebra estrutural (cap. 17) e até estado do decisor (especulativo). | Combinar regras/pessoas com ML. | 53–54 |
| C8 | **Remover rótulos raros**: alguns classificadores têm desempenho ruim com classes desbalanceadas; remover recursivamente observações cuja classe seja menos frequente que `minPct` (a menos que restem duas classes). | Desequilíbrio de classes. | 54 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Estrutura de barreira tripla na negociação | ✅ | Motor e módulo de risco usam stop percentual, take-profit opcional e sinal de saída da estratégia; stops são verificados em mínima/máxima com regra de gap na abertura (`engine.py`, `risk_management/domain/stops.py`). Não há limite de permanência. |
| Barreiras escaladas pela volatilidade | ❌ | Percentuais fixos (livro 4, cap. 20 O2). |
| Rotulagem dependente do caminho para análise | ❌ | Operações são registradas, mas não há tabela por sinal de “o que ocorreu depois” (MFE/MAE, tempo até primeiro toque de ±x·σ). |
| Atributos/rótulos/modelo ML | ❌ | Não há módulo. |
| Modelo primário com lado conhecido | ✅ | Estratégias emitem compra/venda/manter; modo comprado fixa lado comprado — cenário de meta-rotulagem. |
| Registros de sinais para um conjunto | ⚠️ | Backtests geram operações; sinais rejeitados por risco (`rejected_signals`) são contados, mas não armazenados com atributos. |

## 3. Oportunidades

### O1 — Tabela de resultados dos sinais com barreira tripla (ainda sem ML) *(livro: C3, C4, pp. 45–49)*

* **Proposta:** para cada sinal de entrada gerado por uma estratégia em dados históricos (inclusive os ignorados por posição já aberta ou regra de risco), calcular o resultado sob barreira tripla configurável: superior `k_up × σ_t`, inferior `k_dn × σ_t` (σ de volatilidade EWM móvel dos retornos, helper compartilhado proposto no livro 4, cap. 20 O1) e barreira vertical de `h` barras; armazenar primeiro toque, barreira, retorno, MFE/MAE. Exibir tabela/resumo: proporções de toques superior/inferior/vertical, retorno esperado por sinal e tempo até toque.
* **Motivo:** (a) mostra se há vantagem no sinal **independente da regra de saída específica**, teste mais limpo que P/L realizado de saída dependente do caminho; (b) fornece conjunto de dados para meta-rotulagem e projeto de stop/alvo (distribuição MAE responde “quão apertado pode ser stop sem eliminar vencedores”; livro 4 caps. 21/23); (c) detecta falhas de rotulagem criticadas pelo livro (limite fixo, ignorar caminho).
* **Complexidade:** média (cálculo vetorizado; armazenamento para históricos longos). **Riscos:** resultados sobrepostos (cap. 4 trata dependência: sinais consecutivos compartilham caminho, logo contagem exagera evidência independente); `h` e multiplicadores são parâmetros; escolha do rótulo vertical (sinal ou zero). **Validação:** caminhos sintéticos com primeiros toques conhecidos (superior, inferior, vertical); tratar gaps através das barreiras (regra de preço de abertura igual ao motor); sem look-ahead (σ usa dados até a barra do evento).

### O2 — Alinhar barreiras do motor à terminologia tripla: saída por permanência máxima e stop/alvo por volatilidade *(livro: C2, C3, pp. 44–46)*

Adicionar `max_holding_bars` opcional à configuração de risco (sair na próxima abertura após atingir barreira vertical) e, com helper ATR/σ, stop/alvo ajustados à volatilidade (livro 4, cap. 20 O2). Ambos desativados por padrão. Assim, regras ao vivo e regras de rotulagem têm mesma forma, permitindo transferir para execução os achados de O1. **Complexidade:** média (motor, ambiente paper, trader ao vivo com saída por tempo). **Riscos:** mais parâmetros; saída por tempo difere de stop nativo (exige agendador do bot para ordem a mercado, já coberto pelo tratamento de saída). **Validação:** saída determinística na barreira; paridade backtest/paper.

### O3 — Filtro de meta-rotulagem para estratégias atuais (protótipo de pesquisa; requer aprovação) *(livro: C5, C6, pp. 50–53)*

* **Proposta (somente projeto):** manter `ema_crossover`/`donchian_breakout` como primário (lado comprado), rotular sinais passados pelo resultado da barreira tripla em `{0, 1}` (1 se P/L condicionado ao lado for positivo), treinar classificador secundário com atributos conhecidos no instante do sinal (volatilidade recente, inclinação/força da tendência, ER/ruído, razões de volume, hora, distância do canal, resultados de operações anteriores) e usar probabilidade para **filtrar** sinais (agir acima de limite) e, opcionalmente, **escalar a fração da posição** (nunca acima dos limites de risco existentes).
* **Motivo:** adequa-se à plataforma: primário baseado em regras, comprado, de um ativo e com recall alto; modelo secundário pode apenas reduzir/escalar exposição, não inventar operações, limitando danos de sobreajuste (segundo motivo do livro). Alegações de F1 e robustez maiores são experiência do autor; não há tabela empírica nestas páginas.
* **Pré-requisitos:** rótulos O1; validação cruzada com purge/embargo e pesos de amostra (caps. 4 e 7), pois rótulos sobrepostos vazam informação; avaliar sistema completo, não métricas de classificação, usando pipeline de backtest com contagem de tentativas, Sharpe deflacionado (cap. 14) e segmento final bloqueado; persistência/versão do modelo com hash dos dados; inferência no trader no instante do sinal com exatamente o mesmo código de atributos do treino (sem diferença treino/serviço); fallback ao primário sem filtro se modelo indisponível.
* **Custos/riscos:** poucos sinais independentes por ativo cripto (algumas centenas de operações) facilitam sobreajuste de classificadores; mudança de regime; vazamento de atributos; complexidade/manutenção; nova dependência (scikit-learn etc.) em projeto Python 3.12; decisões ao vivo do modelo precisam ser explicáveis e registradas. **Complexidade:** alta. **Recomendação:** implementar primeiro pré-requisitos (O1 e itens dos caps. 4, 7, 14); O3 é linha futura de pesquisa, a decidir com o usuário.

### O4 — Avaliar filtros por precisão/recall **e** P/L; relatório de matriz de confusão para regras de sinais *(livro: C6, pp. 51–53)*

Mesmo sem ML, avaliar qualquer **filtro** de sinal primário (volatilidade, força de tendência, horário) como classificador sobre resultados O1: quantos vencedores mantém (recall), quantos sinais mantidos vencem (precisão) e efeito no P/L. É versão objetiva/simples de “eliminar ou adiar” (livro 4, cap. 20) e varredura pareada (livro 4, cap. 22 O3). **Complexidade:** baixa (após O1). **Validação:** fixtures com VP/FP/FN conhecidos.

### O5 — Tratamento de rótulos raros e verificações de equilíbrio de classes (quando houver ML) *(livro: C8, p. 54)*

Registrar equilíbrio de classes por conjunto e alertar se classe ficar abaixo de um limite; não remover rótulos silenciosamente. **Complexidade:** baixa; parte de O3 quando existir.

### Não aplicável

Rótulos de horizonte fixo para treino (evitar); aprendizado de lado com barreiras simétricas (lado já conhecido); atributos biométricos/psicológicos de operadores discricionários; helpers de multiprocessamento (cap. 20 do livro).

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Tabela de resultados de sinais (barreira tripla) O1 | muito alta | alta | – | média | helper σ (livro 4, cap. 20 O1) |
| 2 | Avaliação de filtros por precisão/recall O4 | alta | – | – | baixa | O1 |
| 3 | Barreira vertical + barreiras por volatilidade no motor O2 | média | alta | média | média | helper σ/ATR |
| 4 | Verificações de equilíbrio de rótulos O5 | baixa | – | – | baixa | O1 |
| 5 | Filtro de meta-rotulagem O3 | potencialmente alta | média | – | alta | O1, caps. 4, 7, 14 |

## 5. Arquivos afetados

`analytics/domain/` (cálculo de resultados), `backtesting/application` (geração do conjunto de sinais, endpoint), `risk_management/domain` e `backtesting/domain/engine.py` (opções de barreira), `trading` (saída por tempo), `docs/openapi.json`, app (visão de resultados de sinal), testes; módulo `ml/` somente após aprovação de O3.

## 6. Plano incremental

1. Helper σ; tabela de resultados (O1) com testes; visão-resumo.
2. Avaliação de filtros (O4).
3. Opções de barreira no motor/paper (O2).
4. Retomar meta-rotulagem (O3) após implementar caps. 4, 7 e 14.

## 7. Critérios de aceitação e testes

* Tabela de resultados: cada caminho sintético produz rótulo/tempo de primeiro toque esperado; gap através de barreira segue regra do motor; sem look-ahead; saída determinística com hash do conjunto.
* Opções de barreira: desativadas por padrão reproduzem resultados atuais; ativadas, provocam saída na barra correta; paridade backtest/paper.
* ruff, mypy e testes existentes aprovados.

## Ressalvas

O livro afirma que barreira tripla e meta-rotulagem são invenções próprias, inexistentes na literatura; alegações de robustez baseiam-se em experiência, sem experimento nestas páginas. Barreiras rotulam qualidade do sinal, não rentabilidade após custos; taxas/slippage devem entrar nos retornos dos rótulos para um alvo realista. Com poucos sinais por ativo, o benefício de qualquer classificador é duvidoso.
