# Livro 5 · Capítulo 10 — Dimensionamento de apostas

*Advances in Financial Machine Learning*, López de Prado (2018). Páginas do livro (PDF = livro + 27). Referência-base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

**Profundidade da leitura:** pp. 141–147 foram lidas (dimensionamento independente da estratégia, por probabilidades previstas, média de apostas ativas, discretização, dimensionamento dinâmico e início de preços-limite). Pp. 148–150 (alternativa de função potência, exercícios) não foram lidas.

**Compatibilidade com a plataforma:** dimensiona por fração fixa e risco por operação (módulo de risco); sinais binários (compra/venda/manter). Dimensionamento proporcional à confiança do sinal é novo; **discretização** e **média de apostas ativas** também combatem excesso de operações, relevante para taxas.

## 1. Resumo do capítulo (páginas lidas)

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | “Seu algoritmo ML pode alcançar alta acurácia, mas, sem dimensionar corretamente as apostas, a estratégia inevitavelmente perderá dinheiro.” Tamanho `m ∈ [−1, 1]` (−1 vendido integral, +1 comprado integral). Exemplo: duas estratégias com previsões idênticas, mas caminhos de dimensionamento diferentes — uma ganha +0,5, outra perde −0,125 — porque a segunda foi forçada a reduzir aposta quando o mercado se moveu contra ela. | Dimensionamento importa tanto quanto direção. | 141 |
| C2 | **Dimensionamento independente da estratégia**: (1) **concorrência de apostas** `c_t = c_{t,long} − c_{t,short}` (compras ativas menos vendas) mapeada pela CDF de mistura ajustada de duas gaussianas; sinais acima do normal recebem apostas maiores e reserva-se caixa para sinais que possam se fortalecer; (2) **orçamento**: tamanho = compras simultâneas ÷ máximo de compras simultâneas − vendas simultâneas ÷ máximo de vendas simultâneas; posição máxima não é atingida antes do último sinal simultâneo; (3) **meta-rotulagem**: probabilidade do modelo secundário define tamanho. | Dimensionar pelo fluxo de sinais. | 141–142 |
| C3 | **A partir de probabilidades previstas**: para lado binário, testar `H₀: p[x=1] = 1/2` com `z = (p − 1/2)/sqrt(p(1−p))`; tamanho `m = 2 Z[z] − 1` (`Z` CDF normal padrão); multiclasse um-contra-resto com `1/X` como nulo; lado vem do rótulo previsto. | Mapear confiança a tamanho. | 142–143 |
| C4 | **Média de apostas ativas**: em vez de substituir aposta antiga a cada nova (alto giro), calcular média dos tamanhos de todas as apostas ainda ativas (emitidas antes de agora e ainda dentro do prazo final). | Controlar giro. | 144 |
| C5 | **Discretização do tamanho**: `m = round(m/d)·d`, `d ∈ (0, 1]`, para evitar negociar pequenas alterações (oscilações de sobreoperação); limitar a [−1, 1]. | Taxas por oscilações. | 144–145 |
| C6 | **Tamanhos dinâmicos e preços-limite**: com preço previsto `f` e preço atual `p`, posição-alvo `q = int(m[w, f − p]·Q)`, usando sigmoide `m = x/√(w + x²)` da divergência `x = f − p`; quando `p → f`, alvo tende a zero (realização de ganhos). **Preço-limite de equilíbrio** da ordem é média da função inversa entre tamanhos atual e alvo; largura `w` calibrada por par `(x, m)` desejado (ex.: 0,95 com divergência 10 dá `w = x²(m⁻² − 1)`; com Q = 100 e f = 115, limite 112,37). Alternativa por função potência não foi lida. | Dimensionar sem realizar perdas. | 145–147 |

## 2. Diagnóstico (verificado no código)

| Conceito | Status | Evidência |
|---|---|---|
| Tamanho como função da força do sinal | ❌ | Sinais discretos; tamanho vem de `position_fraction` e risco por operação via distância do stop (`assess_signal`). |
| Controle de giro de mudanças de tamanho | n/a | Posições entram/saem integralmente (sem redimensionamento). |
| Apostas concorrentes/média | ❌ | Um bot mantém uma posição por vez. |
| Preços-limite dinâmicos | ❌ | Ordens a mercado no paper e stops nativos ao vivo; sem entrada por limite (livro 1, cap. 5 O2). |
| Efeito de taxas por excesso de operações | ✅ (contabilizado) | Taxas/slippage em cada execução; número de operações informado. |

## 3. Oportunidades

### O1 — Fração de posição escalada pela força para estratégias com sinal contínuo (pesquisa) *(livro: C3, pp. 142–143)*

* **Proposta:** permitir que estratégias emitam opcionalmente **convicção em [0, 1]** (ex.: distância normalizada entre EMAs, margem de rompimento em unidades ATR ou probabilidade de modelo) e módulo de risco escale fração configurada por `m = 2Z[z] − 1` ou mapa linear limitado, nunca além dos limites existentes. Somente comprado: `m ∈ [0, 1]`.
* **Motivo:** transforma entrada binária em exposição graduada, analogia mais próxima da ideia central do capítulo. **Ressalvas:** convicção de regra é ad hoc; benefício precisa ser demonstrado (tamanho fixo versus escalado nos mesmos sinais, por métrica ajustada a risco e pipeline completo); escala pode concentrar risco em extremos de rompimento (volatilidade alta); limite de risco por operação segue valendo. **Complexidade:** média (mudar interface de estratégia para convicção opcional; motor e trader). **Validação:** convicção 1 equivale ao comportamento atual; tamanho escalado nunca excede limite; determinístico.

### O2 — Discretização do tamanho para evitar microajustes caso exista redimensionamento *(livro: C5, pp. 144–145)*

Se posições começarem a ser redimensionadas (dimensionamento por volatilidade, adicionar/remover parcelas; livro 4, cap. 23 O2), impor mudança mínima (`d`, por exemplo, 10–25% do alvo) e respeitar notional mínimo/lote da corretora para evitar giro dominado por taxas. **Complexidade:** baixa; parte de qualquer recurso de redimensionamento. **Validação:** nenhuma ordem abaixo do passo; taxa reduzida em sinal sintético oscilante.

### O3 — Métricas de giro sensíveis a taxas *(livro: C4, C5)*

Informar **giro** (soma anual das mudanças absolutas de posição) e **taxas como proporção do lucro bruto**, com alerta quando consumirem fração grande; combinar com limite de cobertura de custos (livro 4, cap. 16 O4, cap. 21 O6). **Complexidade:** baixa. **Validação:** fixtures.

### O4 — Lógica de preço dinâmico de saída (take-profit tipo limite): registrar, não recomendar *(livro: C6, pp. 145–147)*

Esquema de posição-alvo/preço-limite sigmoidal pressupõe preço previsto (`f`) de modelo; plataforma não prevê preços. Retomar caso existam previsões ML de resultados de barreira. Por ora, sobrepõe-se à lógica de take-profit (livro 4, cap. 23 O5: não adotar alvos como padrão em tendência). **Complexidade:** alta.

### O5 — Mapeamento probabilidade-tamanho pertence à linha de meta-rotulagem *(livro: C2, C3)*

Parte de O3 do cap. 3: probabilidade do modelo secundário define fração de posição pelo mapa do livro, com padrões seguros (abaixo do limite, sem operação) e limites existentes. **Complexidade:** linha ML.

### Não aplicável

Vendas e compensação entre apostas compradas/vendidas (spot somente comprado), analogia do pôquer Texas Hold’em, ajuste de mistura gaussiana para concorrência.

## 4. Prioridade

| # | Item | Qualidade do backtest | Gestão de risco | Confiabilidade | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | Métricas de giro e parcela de taxas O3 | média | – | – | baixa | métricas |
| 2 | Fração escalada por força O1 (pesquisa) | média | média | – | média | interface de estratégia |
| 3 | Discretização O2 (com redimensionamento) | – | média | – | baixa | recurso de redimensionamento |
| 4 | Dimensionamento por probabilidade O5 | potencialmente alta | média | – | linha ML | aprovação ML |
| 5 | Preços-limite dinâmicos O4 | – | – | – | alta | modelo de previsão |

## 5. Arquivos afetados

`analytics/domain/metrics.py` (giro e parcela de taxas), `strategies/domain/types.py` (convicção opcional), `risk_management/domain` (escala), `backtesting/domain/engine.py`, `trading/application/trader.py`, formulários do app, testes.

## 6. Plano incremental

1. Métricas.
2. Interface de convicção e experimento.
3. Discretização quando houver redimensionamento.
4. Dimensionamento por probabilidade com linha ML.

## 7. Critérios de aceitação e testes

* Giro e parcela de taxas correspondem a fixtures calculadas manualmente; escala por convicção respeita limites e convicção 1 reproduz comportamento atual; ruff, mypy e testes existentes aprovados.

## Ressalvas

Abordagem de duas gaussianas para concorrência, mapeamento de probabilidade para tamanho e dimensionamento sigmoidal são propostas do autor com números ilustrativos; estas páginas não mostram desempenho empírico. Dimensionamento por probabilidade prevista depende da calibração dessas probabilidades (não discutida nas páginas lidas).
