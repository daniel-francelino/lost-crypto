# Livro 4 · Capítulo 24 — Diversificação e alocação de carteira

*Trading Systems and Methods*, 5ª ed., Kaufman (2013). Páginas do livro (PDF = livro + 20). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** foram lidas as pp. 1099–1103 (introdução, diversificação, múltiplas estratégias) e 1115–1117 (teoria de carteiras aplicada a retornos de negociação). Foram vistos os títulos do restante (pp. 1103–1114: equilíbrio de risco, correlações variáveis, tipos de modelos de carteira, cálculos clássicos de alocação, Solver do Excel; pp. 1117–1146: função objetivo, restrições, solução por algoritmo genético “GASP”, subconjuntos ótimos e exemplos trabalhados). Essas partes **não foram lidas** e não são resumidas aqui.

**Compatibilidade com a plataforma:** o sistema usa um ativo por bot, spot e somente comprado. É possível ter várias carteiras de bots (vários bots ao mesmo tempo), mas não há visão nem alocador no nível da carteira. Portanto, este capítulo é relevante principalmente para **futura** alocação de capital entre vários bots e para risco sensível a correlações; tem prioridade inferior aos caps. 20–23.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | A diversificação reduz o risco **sistemático**, mas não o **risco de mercado** (choques de preço): “a crise do subprime provou que a diversificação pode desaparecer sob estresse”; os benefícios são maiores quando mercados e métodos de decisão são muito diferentes. | Limites da diversificação. | 1099–1101 |
| C2 | **Escolher ativos não relacionados** (baixa covariância/correlação; verificar histórico e fatores que hoje movem o mercado). Os “financeiros” (renda fixa, moedas, índices) são muito inter-relacionados; commodities reagem ao dólar e às taxas. Há longos períodos em que cada grupo segue fundamentos próprios, mas **em um choque todos os mercados ficam altamente correlacionados** (“o dinheiro move o mercado, não os fundamentos”). Com independência perfeita, o risco cairia para 1/N (50%, 33%, 25%); na prática, uma carteira totalmente diversificada talvez reduza o risco inicial em apenas ~50%; o benefício de incluir ativos diminui rapidamente depois de cerca de 4. | Quantos ativos escolher e quais. | 1101–1102 |
| C3 | **Várias estratégias** também diversificam, mas métodos que parecem diferentes podem ter alta correlação (média móvel, ARIMA e ponto-e-figura são todos seguidores de tendência: em algum momento mantêm as mesmas posições). Diversificar por característica funcional: seguimento de tendência versus contramovimento/reversão à média etc. | Diversificação de estratégias. | 1102–1103 |
| C4 | **Alocar com base nos retornos das estratégias, não nos preços**: a teoria clássica média-variância presume um retorno diário. Uma estratégia que fica fora do mercado parte do tempo tem dias de retorno zero; assim, seu desvio-padrão diminui e recebe uma **alocação maior, embora seu risco quando ativa seja igual**. A covariância de retornos intermitentes também fica distorcida (duas estratégias ativas 50% do tempo estão simultaneamente ativas em 25%; duas estratégias no mesmo mercado ativas em 3% dos dias podem ter risco conjunto elevado quando ambas operam, embora a estatística o esconda). Estratégias seletivas, com 10–20% de tempo no mercado, parecem fracas (beta baixa, desvio alto), mas oferecem retornos altos quando ativas e diversificação real. O autor propõe um alocador por algoritmo genético (GASP) em vez de média-variância. | Problemas de otimizar com base no patrimônio da estratégia. | 1115–1117 |

As observações sobre cripto são **adaptações nossas**.

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Vários bots operando simultaneamente | ✅ | O sistema permite diversos bots; cada um é independente (capital e limites de risco próprios). |
| Visão no nível da carteira (exposição, correlação e drawdown agregados) | ❌ | Não há módulo de carteira; o dashboard (app) mostra dados por bot; limites ao vivo são por bot (verificar se há limite global em `risk_management`; o kill switch é global). |
| Correlação entre bots/ativos | ❌ | Não existe. |
| Alocação de capital entre bots | ❌ | Manual; cada bot tem sua própria configuração `capital`. |
| Medida de diversificação de estratégias | ❌ | Não existe. |

## 3. Oportunidades

### O1 — Visão da carteira: exposição agregada, drawdown e correlação entre bots (somente leitura) *(livro: C1, C2, C3, pp. 1099–1103)*

* **Proposta:** visão analítica somente de leitura de todos os bots em execução/paper/ao vivo, mostrando capital total em uso, exposição aberta agregada por ativo (e **exposição efetiva quando há correlação entre ativos**), curva de patrimônio e drawdown combinados, além da **matriz de correlação dos retornos dos bots e dos ativos** em uma janela móvel (retornos diários do **patrimônio**, não do preço: ver C4). Alertar quando a correlação entre os ativos mantidos estiver alta (ativos cripto costumam ser correlacionados, sobretudo em quedas: observação nossa, a verificar com dados, não informação do livro).
* **Motivo:** duas lições do livro: ativos não relacionados reduzem o risco, “mas em um choque as correlações vão a 1”; portanto, o usuário deve enxergar a **concentração disfarçada de diversificação** (vários bots comprados em altcoins que seguem BTC). **Complexidade:** baixa–média (analytics + endpoint + página). **Riscos:** correlações são instáveis e dependem da amostra; mostrar janela e tamanho da amostra; não recomendar alocações. **Validação:** séries sintéticas com correlações conhecidas; lidar com bots sem posições (retornos zero) considerando o alerta C4: calcular também a correlação **somente nos dias em que ambos estão ativos** e mostrar as duas versões.

### O2 — Limites globais da carteira (projeto sujeito a aprovação) *(livro: C1, C2 e cap. 23, C1)*

Limite global para a **soma das exposições ao vivo** e para **posições simultâneas correlacionadas** (por exemplo, “no máximo X% do capital total em ativos do mesmo grupo de correlação”), além dos limites individuais dos bots. O kill switch global existente é uma versão mais ampla. Essa mudança de política de risco para um sistema de negociação ao vivo **precisa ser decidida com o usuário** antes de qualquer código. **Complexidade:** média–alta.

### O3 — Recomendação de alocação com risco igual (sem otimizador) *(livro: C2 + cap. 23, O8, pp. 1050–1054)*

Quando o usuário executar vários bots, uma recomendação informativa pode sugerir capital relativo por pesos de **volatilidade inversa (risco igual)** (cap. 23, O2/O3), em vez de valores monetários iguais; o exemplo de dimensionamento do livro mostra que o mesmo valor concentra risco no ativo mais volátil. Apresentar como informação, sem alocação automática. **Complexidade:** baixa–média. **Validação:** pesos somam 1; invariância à escala.

### O4 — **Não** construir agora um otimizador média-variância ou genético sobre o patrimônio dos bots *(livro: C4, pp. 1115–1117; restante do capítulo não lido)*

O argumento do autor é que a otimização média-variância sobre retornos de negociação intermitentes aloca mal (estratégias inativas parecem mais seguras). Além disso, otimizar alocações com retornos históricos acrescenta outra camada de sobreajuste (cap. 6 do livro 3; cap. 21 do livro 4), com poucas estratégias independentes e histórico cripto curto. Recomendação: **nenhum alocador por enquanto**; se a construção de carteira virar um objetivo, primeiro ler as pp. 1103–1146 e decidir com o usuário o objetivo (razão de retorno) e as restrições. **Complexidade:** alta.

### O5 — Classificação de diversificação das estratégias *(livro: C3, pp. 1102–1103)*

Marcar cada estratégia no catálogo com sua família funcional (seguimento de tendência, rompimento, reversão à média etc.) e mostrar na visão da carteira quantas famílias estão ativas; as estratégias atuais (`ema_crossover`, `donchian_breakout`) seguem tendência e provavelmente são correlacionadas. Isso reforça a inclusão de uma família de reversão à média (livros 1–2) como diversificadora — sujeita à própria validação. **Complexidade:** baixa.

### Não aplicável (nesta fase)

Procedimentos do Solver do Excel, fórmulas clássicas de Markowitz, implementação do GASP, setores de futuros e relações entre dólar e commodities, subconjuntos ótimos de mercados.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Visão da carteira O1 | – | alta | – | baixa–média | – |
| 2 | Classificação por família O5 | – | baixa | – | baixa | catálogo |
| 3 | Recomendação de risco igual O3 | – | média | – | baixa–média | cap. 23, O2 |
| 4 | Limites globais O2 | – | alta | alta | média–alta | decisão do usuário |
| 5 | Otimizador O4 | – | – | – | alta | **não recomendado agora** |

## 5. Arquivos afetados

Novos analytics somente de leitura (carteira) e um endpoint, `strategies/catalog.py` (campo de família), página de carteira do app; para O2, `risk_management/domain` e `trading` somente após aprovação; testes.

## 6. Plano incremental

1. O1 e O5 (somente leitura).
2. Recomendação O3 quando houver dimensionamento por volatilidade.
3. Discutir O2 com o usuário; decidir se o restante do capítulo deve ser lido.

## 7. Critérios de aceitação e testes

* Agregados de correlação e exposição correspondem a fixtures calculadas manualmente; o tratamento de dias inativos é explícito e documentado.
* Nenhuma mudança no comportamento de negociação; ruff, mypy e testes existentes aprovados.

## Ressalvas

Somente as partes introdutórias do capítulo foram lidas; a alegação do autor de que seu alocador genético supera média-variância vem de seções não consultadas. A curva de diversificação (redução máxima de risco de aproximadamente 50%) vem de uma figura do livro e de dados de futuros/ações. Para cripto, a correlação alta entre ativos é uma expectativa a verificar com os dados da plataforma, não uma conclusão comprovada.
