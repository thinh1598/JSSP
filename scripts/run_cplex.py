"""Giai MOT bai JSSP bang CPLEX MIP (viet file .lp, goi cplex.exe cua Studio), in ra 1 dong JSON.

Chay tay:
    python scripts/run_cplex.py data/ft06.txt --time-limit 60
Trang thai dac biet: NOT_INSTALLED (khong thay cplex.exe), LICENSE_LIMIT (ban community bi gioi han).
Muon chi dinh cplex.exe: dat bien moi truong JSSP_CPLEX_EXE.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.cplex_mip import solve_cplex_mip  # noqa: E402
from jssp.heuristic import best_greedy  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.validate import makespan  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--time-limit", type=float, default=600, help="giay")
    ap.add_argument("--threads", type=int, default=1, help="1 = cong bang voi CaDiCaL / CP-SAT / Gurobi don luong")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lb", type=int, default=None)
    ap.add_argument("--ub", type=int, default=None)
    args = ap.parse_args()

    inst = read_instance(args.instance)
    lb = args.lb if args.lb is not None else inst.trivial_lower_bound()
    ub = args.ub if args.ub is not None else makespan(inst, best_greedy(inst))
    r = solve_cplex_mip(inst, lb, ub, args.time_limit, args.threads, args.seed)
    r.update(instance=inst.name, lb=lb, ub=ub)
    print(json.dumps(r), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
