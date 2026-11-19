# JSSP by SAT encoding

Exact solving of the Job-Shop Scheduling Problem (JSSP) with the Crawford SAT encoding used by Koshimura et al. (2010),
implemented with PySAT (CaDiCaL), and a controlled comparison against CP-SAT, CP Optimizer, Gurobi MIP and CPLEX MIP.

Assignment 2, *Modern Topics in CS* (HK I 2026-2027), topic 7. Authors: Do Viet Hoang, Nguyen Phuc Thinh.

Reference: M. Koshimura, H. Nabeshima, H. Fujita, R. Hasegawa, *Solving Open Job-Shop Scheduling Problems by SAT Encoding*,
IEICE Trans. Inf. & Syst., E93-D(8), 2010.

## What is in this repository

- The SAT encoding (rules R1-R9; R9 is our added boundary rule) and a decoder with an independent schedule validator.
- Two search schemes: repeated SAT (descent or bisection, a new formula per threshold) and incremental SAT
  (one formula, the threshold is set through solver assumptions).
- Baselines under one protocol: CP-SAT, CP Optimizer, Gurobi MIP, CPLEX MIP (same initial bounds, one thread,
  same time limit, every returned schedule re-validated).
- A batch runner, the analysis scripts and the LaTeX report (Elsevier cas-sc).

## Main findings (single run, one thread, one laptop)

- 16 non-trivial benchmark instances up to 20x20; time limits 600 / 900 / 3600 s (small / medium / large).
- CP Optimizer proves 13 of 16 optimal (including abz7 = 656 in 1302 s) and has the best upper bound on all four large instances.
- Incremental SAT is 1.5-28 times faster than repeated SAT where both finish, and gives the best lower bounds on abz8 and yn1.
- Gurobi and CPLEX MIP are competitive only on small instances.
- Details, tables and caveats are in `report/main.tex`; raw rows are in `results/raw/summary.csv`.

## Repository layout

```
src/jssp/      encoder, decoder, validator, search strategies, baselines, MIP model, analysis
scripts/       command-line tools (run_*.py, analyze.py, fetch_benchmarks.py, make_report_assets.py, check_*.py)
tests/         pytest suite
data/          benchmark instances (data/instances/*.txt) and known_bounds.csv (literature values)
results/raw/   summary.csv with one row per (instance, method, solver) run
results/analysis/   tables and consistency report produced by scripts/analyze.py
results/schedules/  schedules returned by solvers (JSON), re-validated by the parent process
report/        LaTeX source of the report, generated figures and tables
notes/         working notes on the encoding and the reference paper
```

## Setup

Tested with Python 3.13 on Windows 11. On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/check_env.py
```

On Linux or macOS: `python3 -m venv .venv && source .venv/bin/activate`, then the same `pip` and `check_env.py` lines.

Fetch the benchmark instances (OR-Library `jobshop1.txt`) into `data/instances/`:

```
python scripts/fetch_benchmarks.py
```

Run the tests (tests that need a solver you do not have installed are skipped):

```
python -m pytest -q
```

### Commercial solvers

- **Gurobi**: needs a valid license (an academic license works). The license file is personal and must never be committed
  (`gurobi.lic` and `*.lic` are in `.gitignore`). Check with `python scripts/check_gurobi.py`.
- **CPLEX and CP Optimizer**: need IBM ILOG CPLEX Optimization Studio installed locally (we used 22.2.0). The pip `cplex`
  package is the community edition and is too small for the larger instances. If the executables are not found, set
  `JSSP_CPLEX_EXE` and `JSSP_CPO_EXE`. Check with `python scripts/check_cplex.py`.
- Without these solvers the SAT and CP-SAT parts still run; license-related statuses are reported and no result row is written.

## Usage

Solve one instance with a fixed threshold L (SAT or UNSAT):

```
python scripts/run_sat.py data/ft06.txt --L 55
```

Find the optimum or the best interval with one search scheme:

```
python scripts/search_opt.py ft06 --method both      # repeated SAT: descent and bisection
python scripts/run_inc.py data/instances/ft10.txt --method binary    # incremental SAT
```

Run all methods on a tier (results are appended to `results/raw/summary.csv`; cells already done are skipped, so the same
command resumes an interrupted run):

```
python scripts/run_suite.py --tier small --dry-run   # preview only
python scripts/run_suite.py --tier medium --max-hours 6
python scripts/run_suite.py --instances abz9 yn1 --methods cpo,cplex --budget 3600
python scripts/run_hybrid.py --instances la21 orb01 --variants B,C --budget 900     # CP-SAT + SAT hybrid
```

Re-run a single cell with `--force`. Keep the machine awake during long runs: a sleeping laptop inflates run times.

Build the tables, figures and consistency report:

```
python scripts/analyze.py                  # results/analysis/*.md, *.csv, consistency.txt
python scripts/make_report_assets.py       # report/figures/*.pdf, report/tables/*.tex
```

`consistency.txt` lists contradictions between solvers (a lower bound above another solver's upper bound, disagreeing optima)
and suspicious rows (for example, a run far above its time limit).

## Report

`report/main.tex` uses the Elsevier `cas-sc` class (available on Overleaf as "Elsevier CAS Single Column Template").
Upload `main.tex`, `refs.bib`, `figures/` and `tables/` and compile. Figures and tables are generated from
`results/raw/summary.csv`; do not edit them by hand.

## Reproducibility notes

- Every reported bound comes from a schedule or proof that the parent process accepted; schedules are re-validated by
  `src/jssp/validate.py`, which does not use the SAT encoding.
- Each result cell is a single run on one Windows laptop (Intel Core i5-1240P, 7.7 GB RAM), one thread per solver.
  Differences of a few percent or a few seconds are not meaningful.
- The literature optima in `data/known_bounds.csv` were typed from the reference paper and are used only for comparison.

## License

No license has been chosen yet. Add one before making the repository widely reusable.
