# Book 1 · Chapter 8 — Conclusion: Can Independent Traders Succeed?

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. The remaining pages (Appendix A, a MATLAB survey, the bibliography and index) were not analysed.

## 1. Chapter summary (pp. 157–160)

| ID | Concept | Pages |
|---|---|---|
| C1 | Independent traders can do well when large funds fail because of **capacity**: small accounts can use strategies that act like short-term liquidity providers and cannot absorb billions. Big funds need long holding periods, take regime risk, face intense competition, are pushed toward leverage and complexity (→ snooping), and end up holding similar positions (stampede risk). | 157–159 |
| C2 | Institutions impose constraints and managerial interference (forced scaling after wins, forced liquidation after losses); every constraint reduces the optimum. An independent trader is free of them **if emotionally disciplined**. | 159 |
| C3 | Agency problem: with other people's money upside is large and downside is being fired, which drives risk-taking; internal controls can be evaded (Kerviel and a second example). | 160 |

The chapter is opinion and anecdote; it adds no method. It is the author's argument, not evidence.

## 2. Diagnosis
* **C1 capacity:** accounts are small by design; the system has no capacity model, and none is needed now. If order sizes grow, chapter 5 O3 (volume cap) is the control.
* **C2 discipline:** the system encodes discipline through audited controls, live caps, typed-name approval, kill switch and mandatory paper period. What is missing is the Chapter-1/6 material (recording reasons for interventions).
* **C3 internal controls:** the operator is also the only user, but the system already has roles (admin/viewer), an audit log and reconciliation. Separation of duties between "who changes risk caps" and "who runs bots" exists only as admin vs viewer.

## 3. Opportunities
No new opportunities arise from this chapter. It reinforces earlier items:
* Chapter 1 O1 (alerts), O3 (intervention reasons).
* Chapter 6 O6 (discipline guard on parameter edits) and O7 (exposure visibility).
* Chapter 5 O3 (volume cap) as the capacity control.

## 4–7. Priority, files, plan, acceptance
Not applicable; see the referenced items.

## Caveat
The claim that independent traders have an edge over institutions is the author's thesis. It must not be read as a statement that Lost Crypto will be profitable.
