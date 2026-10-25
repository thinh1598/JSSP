# JSSP by SAT Encoding (Crawford encoding)

Assignment 2 – Modern Topics in CS (HK I 2026-2027), topic: Job Shop Scheduling.
Reference paper: Koshimura et al., *Solving Open Job-Shop Scheduling Problems by SAT Encoding*, IEICE Trans. Inf. & Syst., 2010.

## Layout
- `src/`      parser, Crawford encoder, validator, search strategies (multi-SAT / incremental)
- `models/`   baselines: CP-SAT, CPLEX CP, CPLEX MIP, Gurobi
- `data/`     benchmark instances (FT, LA, ABZ, YN, TA ...)
- `results/`  raw CSV + figures
- `report/`   LaTeX (cas-sc)
- `notes/`    paper notes
- `tests/`    pytest

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/check_env.py
```

## Status
- [x] Day 1: project skeleton, environment check
