"""Giai MOT bai JSSP bang CP-SAT (OR-Tools), in ra 1 dong JSON. Thuong duoc goi boi run_baseline.py.

Chay tay:
    python scripts/run_cpsat.py data/ft06.txt --time-limit 60
    python scripts/run_cpsat.py data/ft10.txt --time-limit 600 --workers 1
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.cpsat import solve_cpsat  # noqa: E402
from jssp.heuristic import best_greedy  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.validate import makespan  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--time-limit", type=float, default=600, help="giay")
    ap.add_argument("--workers", type=int, default=1, help="so luong CP-SAT (1 = cong bang voi CaDiCaL don luong)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lb", type=int, default=None, help="mac dinh: can duoi don gian")
    ap.add_argument("--ub", type=int, default=None, help="mac dinh: makespan cua heuristic")
    args = ap.parse_args()

    inst = read_instance(args.instance)
    lb = args.lb if args.lb is not None else inst.trivial_lower_bound()
    ub = args.ub if args.ub is not None else makespan(inst, best_greedy(inst))
    r = solve_cpsat(inst, lb, ub, args.time_limit, args.workers, args.seed)
    r.update(instance=inst.name, lb=lb, ub=ub)
    print(json.dumps(r), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
