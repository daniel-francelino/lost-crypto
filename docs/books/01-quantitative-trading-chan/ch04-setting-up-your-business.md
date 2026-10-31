# Livro 1 · Capítulo 4 — Montando o seu negócio

*Quantitative Trading*, Chan (2009). Páginas do livro (PDF = livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise.

## 1. Resumo do capítulo (pp. 69–78)

Capítulo não técnico sobre o cenário de ações dos EUA (SEC Regulation T, NASD Series 7, SIPC). A maior parte não se transfere para um sistema cripto pessoal.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Corretora de varejo (gratuita, baixa alavancagem, com seguro) vs. mesa proprietária (alta alavancagem, regras impostas, sem seguro). Regras impostas podem funcionar como gestão de risco externa; liberdade irrestrita é um risco quando chega o "grande drawdown". | Escolher quem guarda o capital e quem impõe limites. | 69–71 |
| C2 | Escolher a corretora por mais que a comissão: velocidade de execução, acesso a liquidez, variedade de produtos e, acima de tudo, uma **API** para dados e ordens mais uma **conta de paper trading**. É possível usar várias contas para comparar a qualidade real da execução. | Custos de execução ocultos; impossibilidade de testar com segurança. | 71–74 |
| C3 | Risco de contraparte: verificar a solidez financeira da empresa, o registro e a reputação de devolver capital. | Perder capital por causa do custodiante. | 74 |
| C4 | A infraestrutura física pode começar leve (PC, banda larga, nobreak). Depois, **continuidade de negócio**: rodar os programas em servidor hospedado/colocalizado para evitar quedas de Internet/energia; monitorar remotamente. A latência soma slippage em mercados rápidos. | Indisponibilidade e latência. | 75–77 |
| C5 | Mais informação em tempo real não é automaticamente melhor (estudo de corridas de cavalos citado). | Excesso de informação. | 75–76 |

Sem conteúdo sobre cripto. Tudo sobre exchanges abaixo é **adaptação nossa**.

## 2. Diagnóstico

| Conceito | Status | Evidência |
|---|---|---|
| C1 limites externos | ✅ | O live é protegido por limites definidos pelo operador (`LiveLimits`), kill switch, aprovações e `live_min_paper_days`; eles ficam no ambiente, não na API, o que combina com a ideia de limites que o operador não remove casualmente. |
| C2 API + conta paper | ✅ | Binance spot e testnet atrás de um único `ExchangeRegistry`; existe venue de execução paper (`execution/venues/paper.py`). |
| C2 comparar execução entre venues | ❌ | Uma única exchange; não há registro de preço de fill esperado vs. real, então a qualidade de execução não pode ser comparada (ver capítulo 5). |
| C3 custódia/contraparte | ⚠️ | As chaves da exchange são usadas com a exchange guardando os fundos. O sistema não exige chave sem permissão de saque nem mantém uma nota de risco da exchange. Para verificar em vez de assumir, conferir o tratamento de permissões de chave em `exchanges` antes de agir. |
| C4 continuidade | ⚠️ | Docker Compose com API + worker + Postgres; a reconciliação recupera ordens pendentes após uma queda. Sem plano documentado de hospedagem/redundância, sem teste de restauração, sem checagem externa de vida. |

## 3. Oportunidades

### O1 — Documentar o ambiente de operação e o plano de continuidade *(livro: C4, pp. 75–77 · adaptação)*
* Escrever um runbook curto: onde a stack roda (não num notebook que entra em repouso), política de reinício, backups do Postgres e uma **restauração testada**, sincronização de relógio, e o que acontece com posições abertas se o host cair. Complexidade: baixa (documentação) mais um job de backup. Validação: uma restauração real em um banco de teste.

### O2 — Política de permissão das chaves *(livro: espírito de C3, p. 74 · adaptação, não está no livro)*
* Exigir (e verificar quando a conexão é criada) que as chaves da exchange sejam **apenas de trade, sem saque**, e restritas por IP onde a exchange suportar. Precisa verificar o que o adaptador da Binance consegue detectar no endpoint de permissões da conta. Complexidade: baixa–média. Risco: algumas exchanges não expõem permissões. Validação: teste de verificação de conexão com um adaptador falso que devolve uma chave com saque habilitado.

### O3 — Checagem externa de vida *(livro: C4 monitoramento remoto, p. 77 · liga com Capítulo 1 O1)*
* Uma checagem vinda de fora da stack (healthcheck de container ou um pinger externo) para que a perda do host inteiro seja percebida; combina com os alertas propostos no Capítulo 1.

### Não aplicável
Escolha varejo vs. proprietária, Series 7, SIPC, Regulation T, dark pools, colocalização perto de uma bolsa, contratar feed de notícias.

## 4. Prioridade

| # | Item | Confiabilidade | Gestão de risco | Complexidade | Depende de |
|---|---|---|---|---|---|
| 1 | O2 política de permissão de chaves | média | **alta** | baixa–média | capacidades do adaptador da exchange |
| 2 | O1 runbook de continuidade + restauração de backup | alta | média | baixa | – |
| 3 | O3 checagem externa de vida | média | – | baixa | Capítulo 1 O1 |

## 5. Arquivos afetados
`exchanges/application` (verificação de conexão), `exchanges/infrastructure/binance.py`, `docs/` (runbook), `docker-compose.yml` (healthchecks, política de reinício), script de backup.

## 6. Plano
1. Runbook e teste de backup/restauração (sem risco de código).
2. Checagem de permissão na verificação de conexão, exibida na UI como um estado claro.
3. Checagem externa de vida quando os alertas existirem.

## 7. Critérios de aceite
* Uma restauração de backup em um banco limpo é demonstrada e documentada.
* Uma conexão com permissão de saque é recusada ou sinalizada de forma explícita na verificação.
* Nenhuma ação com dinheiro real é necessária para testar qualquer item.

## Ressalva
Os valores de custo e hardware de Chan (2008) estão desatualizados e são específicos de ações; não usar como estimativas.
