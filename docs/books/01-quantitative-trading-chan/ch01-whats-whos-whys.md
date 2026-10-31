# Livro 1 · Capítulo 1 — O quê, quem e por quê do trading quantitativo

*Quantitative Trading*, Ernest P. Chan (Wiley, 2009). As páginas são **páginas do livro** (página do PDF = página do livro + 22). Linha de base: [00-system-baseline](../00-system-baseline.md). Status: apenas análise, nada implementado.

## 1. Resumo do capítulo (pp. 1–8)

Introdutório. Sem fórmulas. As afirmações são opiniões e anedotas do autor, não evidência.

| ID | Conceito | Problema que aborda | Páginas |
|---|---|---|---|
| C1 | Trading quantitativo = operações decididas estritamente por algoritmos testados no histórico; fundamentos e notícias contam se virarem números; padrões gráficos subjetivos não. | Separar estratégias codificáveis de opinião. | 1–2 |
| C2 | Estratégias simples; a matemática avançada não ajudou o autor (relato próprio de perdas em instituições). | Complexidade como fonte de perdas. | 2–3 |
| C3 | Manter poupança; não precisar de lucro imediato; os retornos têm seu próprio ritmo. | Pressão por resultados rápidos. | 4 |
| C4 | Escalar mudando a alavancagem; alerta contra alavancagem excessiva. | Escalonamento descontrolado. | 5 |
| C5 | A interferência manual muitas vezes piora os resultados; o autor admite a vontade de sair nas oscilações de P&L. | Intervenção humana. | 5–6 |
| C6 | Automatizar passo a passo: baixar dados, iniciar e parar programas, **alertar um celular/suporte quando algo der errado**. | Operar sem ficar olhando a tela. | 6–7 |
| C7 | A pesquisa deve continuar porque a concorrência corrói os lucros. | Decaimento da vantagem (edge). | 6–7 |
| C8 | Começar pequeno, crescer com o conhecimento. | Risco de ruína no início. | 4–5 |

O livro não discute cripto, mercados 24/7 nem taxas de corretora. Tudo sobre cripto abaixo é **adaptação nossa**.

## 2. Diagnóstico

| Conceito | Status | Evidência |
|---|---|---|
| C1 | ✅ | As estratégias são classes registradas; os sinais são intenções explícitas. |
| C2 | ⚠️ | Catálogo pequeno; não há medida comparando estratégias simples e complexas. |
| C3/C8 | ✅ | Paper → testnet → live, limites no live, mínimo de dias em paper, aprovação digitando o nome. |
| C4 | n/a | Apenas spot; sem alavancagem. Existem limites de exposição, mas não uma política de alavancagem. |
| C5 | ⚠️ | `pause`/`stop`/`reset` são auditados, mas nenhum motivo é registrado e não existe métrica de intervenção. |
| C6 dados | ⚠️ | O trader busca candles recentes por conta própria; a importação histórica é apenas manual. |
| C6 **alertas** | ❌ | Nenhum canal de notificação (busquei `alert`, `notif`, `webhook`, `telegram`, `email`, `smtp` em `api/src`: nada). O heartbeat do worker existe, mas só é lido pela UI. |
| C7 | ✅ | Backtest, sweep e comparação existem. |

## 3. Oportunidades

### O1 — Alertas de falha *(livro: C6, p. 7 · canal e gatilhos são adaptação nossa)*
* **Problema:** worker parado, heartbeat de bot desatualizado, kill switch acionado, divergência na reconciliação, ordem live rejeitada e limite diário atingido passam despercebidos sem alguém olhando.
* **Proposta:** uma porta `Notifier` com uma implementação por canal (webhook primeiro, depois chat), um arquivo por integração. Um avaliador no worker emite eventos de alerta com deduplicação, cooldown e mensagem de recuperação. Os críticos também vão para o log de auditoria.
* **Benefício:** falhas percebidas em minutos, sem supervisão.
* **Complexidade:** média (tarefa periódica no worker, segredo do canal).
* **Riscos:** o caminho do alerta morre junto com o worker (precisa de uma checagem externa de vida, por exemplo healthcheck do container); um novo segredo a proteger; fadiga de alertas.
* **Validação:** testes unitários de limites e deduplicação; teste de integração que para o worker e espera um alerta via notifier falso; segredos ausentes de logs/API.

### O2 — Importação incremental automática de dados *(livro: C6, pp. 6–7 · adaptação)*
* **Problema:** lacunas nos candles armazenados só são reparadas por jobs manuais.
* **Proposta:** uma tarefa periódica no worker que estende a cobertura dos pares ativos até o presente, reutilizando o job de importação; recuar (backoff) em lacunas de manutenção da exchange.
* **Benefício:** backtests sempre rodam com dados atuais.
* **Complexidade:** baixa. **Riscos:** limites de taxa (rate limits); lacunas legítimas sendo tentadas para sempre.
* **Validação:** teste de integração com uma fonte falsa que deixa um buraco e espera que ele seja preenchido.

### O3 — Motivo das intervenções manuais *(livro: C5, pp. 5–6 · adaptação)*
* **Problema:** não dá para saber se um stop/pause/reset foi reação a oscilações de P&L.
* **Proposta:** motivo opcional nesses comandos, guardado no payload de auditoria, mais um indicador de "intervenções por bot".
* **Benefício:** dados sobre o nosso próprio comportamento. **Complexidade:** baixa. **Risco:** um campo ignorado.
* **Validação:** teste de que o motivo chega ao evento de auditoria.

### O4 — Política de alavancagem/exposição *(livro: C4, p. 5 · adiado)*
Não existe alavancagem. Só passa a ser prioridade alta se futuros/margem forem adicionados; revisitar com o Capítulo 6.

### O5 — Comparação simples vs. complexo *(livro: C2, p. 3 · não acionável)*
Apoia-se em uma frase de opinião. Capítulos posteriores dão critérios concretos; não agir sobre este item.

## 4. Prioridade

| # | Item | Confiabilidade | Gestão de risco | Qualidade do backtest | Complexidade | Depende de |
|---|---|---|---|---|---|---|
| 1 | O1 alertas | alta | alta | – | média | agendador do worker, segredo do canal |
| 2 | O2 importação incremental | média | – | média | baixa | job de importação existente |
| 3 | O3 motivo da intervenção | baixa | média | – | baixa | auditoria existente |
| – | O4, O5 | adiados | | | | |

## 5. Arquivos afetados
* O1: novo módulo `notifications` (porta + um arquivo por canal), `worker.py`, `container.py`, `core/config.py`, auditoria, páginas de status/configurações do app.
* O2: `modules/market_data/application/service.py`, `worker.py`, `container.py`.
* O3: `modules/bots/application/service.py`, router de bots, payload de auditoria, formulários de controle do app.

## 6. Plano incremental
1. O1a: porta `Notifier`, notifier falso, avaliador de condições (sem canal real).
2. O1b: implementação de webhook, configuração por variáveis de ambiente, integração ao worker.
3. O1c: a página de status mostra alertas recentes e canais configurados.
4. O2: importação incremental periódica.
5. O3: campo de motivo.

## 7. Critérios de aceite e testes
* Um alerta por episódio em até N segundos após o rompimento do limite, mais uma mensagem de recuperação.
* Um canal com falha nunca derruba o worker; a falha é registrada em log.
* Nenhum segredo de canal em logs, auditoria ou respostas da API.
* Fluxo de ordens e salvaguardas do live inalterados; testes unitários, de integração, ruff e mypy continuam verdes.

## Ressalva
As anedotas de lucro do autor (pp. 3, 8) são relatos pessoais e não devem ser usadas como expectativa de retorno.
