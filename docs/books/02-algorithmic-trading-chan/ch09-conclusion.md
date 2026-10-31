# Book 2 · Conclusion

*Algorithmic Trading*, Chan (2013), pp. 187–189. Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. The bibliography, author and website pages were not analysed.

## 1. Summary

| ID | Concept | Pages |
|---|---|---|
| C1 | The book illustrates concepts, not recipes: its strategies may still contain the pitfalls of Chapter 1 and can fall victim to regime change; readers should test them out of sample. | 187 |
| C2 | Understand the **inefficiency first**, then build a simple (linear) model; avoid arbitrary rules. | 187 |
| C3 | Treat trading **scientifically**: hypothesis → model → test on unseen data → if it fails, find the reason (GLD/GDX and oil) rather than adding rules. | 187–188 |
| C4 | **Judgment calls remain**: lowering leverage before a major event (author: if the model survived prior stress, don't; start conservative), pooled versus per-strategy Kelly (author: per strategy lets underperformers die quickly). | 188 |
| C5 | Live divergence often comes from **regime shifts**, not backtest errors; the manager's role is to judge whether the models are still valid; algorithms beat expert judgment where uncertainty is high (Kahneman). | 188–189 |

## 2. Diagnosis and opportunities
All points are already covered by earlier items:

* C2/C3 → the post-mortem and hypothesis records ([ch. 4 O1](ch04-mean-reversion-stocks-etfs.md)), diagnostics before strategies ([ch. 2 O1](ch02-basics-of-mean-reversion.md)), and the hypothesis IDs `H-MOM-REV` and `H-RISK-INDICATOR`.
* C4 → document policies ([ch. 8 O7](ch08-risk-management.md)); per-strategy sizing is already how bots work ([ch. 8 O5](ch08-risk-management.md)).
* C5 → named regime breaks and live-vs-backtest monitoring ([ch. 5 O1](ch05-mean-reversion-currencies-futures.md), [ch. 1 O4](ch01-backtesting-and-automated-execution.md)).

No new opportunities.

## Caveat
The author states the book's strategies are not guaranteed pitfall-free and may fail under regime change (p. 187). Nothing here is a statement about expected returns.
