# Book 5 · Chapters 20–22 — High-Performance Computing Recipes

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** only the Part 5 divider and the opening of chapter 20 (pp. 301–303) were read, plus the chapter titles: ch. 20 *Multiprocessing and Vectorization* (p. 303), ch. 21 *Brute Force and Quantum Computers* (p. 319), ch. 22 *High-Performance Computational Intelligence and Forecasting Technologies* (p. 329, by Kesheng Wu and Horst Simon). The contents were **not** analysed; this file records scope and the few implications visible from the openings.

## What the chapters are about (from the pages read)

* **Ch. 20**: explains `mpPandasObj`, used throughout the book — a multiprocessing engine that partitions work ("molecules") across CPUs/servers, plus vectorisation ("array programming") as the simplest parallelisation, e.g. building a Cartesian product over a number of dimensions defined at runtime. The structure is hardware-agnostic (cores of one server or a cluster/cloud).
* **Ch. 21**: discrete optimisation by brute force and quantum computers (title only).
* **Ch. 22**: HPC and forecasting technologies (title only).

## Diagnosis (relevant platform facts)

| Topic | Status | Evidence |
|---|---|---|
| Parallel execution of sweeps/backtests | ⚠️ | Sweeps run inside the backtesting service; `MAX_SWEEP_RUNS` limits size. Verify whether runs are executed concurrently or sequentially before designing any parallelism. |
| Background execution | ✅ | Worker processes (heartbeat, reconciler) exist for trading; long jobs for research would need a similar worker. |

## Opportunities

* **O1 — Parallel/background execution for heavy research jobs** (PBO with S = 16 → 12,870 combinations of precomputed series is cheap, but CPCV with sweeps per split, null distributions on synthetic data (ch. 13 O1) and SADF are expensive). Design when those items are approved: a job table, a worker pool bounded by CPU count, deterministic seeds per job, results persisted; vectorised numpy-style evaluation of strategies where the strategy logic allows it. **Complexity:** medium–high. **Not before** the first research items (ledger, PBO, DSR) exist, since those are inexpensive.
* **O2 — Vectorised implementations in analytics** (rolling statistics, bootstrap, CSCV combination loops) instead of Python loops, to keep API latency low. Evaluate when performance becomes a problem; the project currently uses `Decimal` for money, so keep the float/vectorised boundary explicit (research statistics may use float; trading amounts stay `Decimal`).

## Not applicable

Quantum computing, GPU/distributed clusters, supercomputing-scale forecasting. A single-user platform does not need them.

## Caveats

Pages 304–360 were not read; do not infer recommendations from this note beyond the two generic points above.
