"""Smoke test: verify PySAT solvers and OR-Tools CP-SAT work."""
import importlib, sys, time

def try_import(name):
    try:
        m = importlib.import_module(name)
        print(f"[ok]   import {name}")
        return m
    except Exception as e:
        print(f"[FAIL] import {name}: {e}")
        return None

print("Python", sys.version.split()[0])

# ---- PySAT -----------------------------------------------------------
if try_import("pysat"):
    from pysat.solvers import Solver
    # (a ∨ b) ∧ (¬a ∨ b) ∧ (¬b ∨ c): satisfiable;  adding (¬c) makes b false -> UNSAT
    cnf = [[1, 2], [-1, 2], [-2, 3]]
    for name in ["cadical153", "glucose4", "minisat22", "maplechrono"]:
        try:
            with Solver(name=name, bootstrap_with=cnf) as s:
                sat = s.solve()
                model = s.get_model()
                # incremental use: assumptions
                unsat = not s.solve(assumptions=[-3])
            print(f"[ok]   solver {name:12s} sat={sat} model={model} "
                  f"assume(-3)->unsat={unsat}")
        except Exception as e:
            print(f"[FAIL] solver {name}: {e}")

# ---- OR-Tools CP-SAT -------------------------------------------------
if try_import("ortools"):
    from ortools.sat.python import cp_model
    m = cp_model.CpModel()
    x = m.NewIntVar(0, 10, "x"); y = m.NewIntVar(0, 10, "y")
    m.Add(x + y == 7); m.Maximize(x - y)
    s = cp_model.CpSolver(); st = s.Solve(m)
    print("[ok]   CP-SAT status:", s.StatusName(st), "x,y =", s.Value(x), s.Value(y))

# ---- Optional commercial solvers ------------------------------------
for opt in ["docplex", "cplex", "gurobipy"]:
    try_import(opt)
