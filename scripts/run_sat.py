"""Giai mot bai JSSP voi makespan <= L bang ma hoa Crawford + SAT solver.

Vi du (chay tu thu muc goc repo):
    python scripts/run_sat.py data/ft06.txt --L 55
    python scripts/run_sat.py data/ft06.txt --L 55 --solver glucose4 --gantt results/figures/ft06_55.png
    python scripts/run_sat.py data/ft06.txt --L 54          # UNSAT => (cung voi L=55 SAT) toi uu = 55
    python scripts/run_sat.py data/ft06.txt --L 55 --json   # in ra 1 dong JSON (de script khac doc)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.gantt import plot_gantt  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.sat_solve import solve_le  # noqa: E402
from jssp.validate import validate_schedule  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", help="duong dan file bai, vd data/ft06.txt")
    ap.add_argument("--L", type=int, required=True, help="gia dinh makespan <= L")
    ap.add_argument("--solver", default="cadical153",
                    help="ten solver PySAT: cadical153, glucose4, minisat22, maplechrono, ...")
    ap.add_argument("--gantt", help="neu dat: luu bieu do Gantt vao file anh nay (khi SAT)")
    ap.add_argument("--tiny", action="store_true",
                    help="dung solver DPLL nho thay PySAT (chi cho bai rat nho, de thu khi chua cai PySAT)")
    ap.add_argument("--json", action="store_true", help="chi in 1 dong JSON ket qua")
    args = ap.parse_args()

    inst = read_instance(args.instance)
    solver_name = "DPLL nho (--tiny)" if args.tiny else args.solver
    if not args.json:
        print(f"{inst.name}: {inst.n_jobs} job x {inst.n_machines} may | LB don gian = "
              f"{inst.trivial_lower_bound()} | L = {args.L} | solver = {solver_name}")
    backend = None
    if args.tiny:
        from jssp.minisolver import solve_dpll
        backend = solve_dpll
    r = solve_le(inst, args.L, args.solver, backend=backend)
    errs = validate_schedule(inst, r.starts, args.L) if r.status == "SAT" else []

    if args.json:
        print(json.dumps({"instance": inst.name, "L": args.L, "solver": solver_name, "status": r.status,
                          "makespan": r.makespan, "valid": (not errs) if r.status == "SAT" else None,
                          "starts": r.starts, "vars": r.num_vars,
                          "clauses": r.num_clauses, "encode_time": round(r.encode_time, 3),
                          "solve_time": round(r.solve_time, 3)}))
        return 0

    print(f"ket qua: {r.status}  | bien = {r.num_vars:,}  clause = {r.num_clauses:,}  "
          f"| sinh CNF {r.encode_time:.2f}s  giai {r.solve_time:.2f}s")
    if r.status == "SAT":
        print(f"makespan cua lich = {r.makespan}  | kiem tra hop le: {'OK' if not errs else errs}")
        for l, row in enumerate(r.starts):
            print(f"  job {l}: " + " ".join(f"{s:>4}" for s in row))
        if args.gantt:
            Path(args.gantt).parent.mkdir(parents=True, exist_ok=True)
            plot_gantt(inst, r.starts, args.gantt, f"{inst.name}, L={args.L}")
            print("da luu Gantt:", args.gantt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
