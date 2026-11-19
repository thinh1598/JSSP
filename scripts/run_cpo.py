"""Giai MOT bai JSSP bang CPLEX CP Optimizer (docplex.cp), in ra 1 dong JSON. Thuong duoc goi boi run_baseline.py.

Chay tay:
    python scripts/run_cpo.py data/ft06.txt --time-limit 60
Trang thai dac biet (child van thoat ma 0): NOT_INSTALLED (chua cai docplex), LICENSE_LIMIT (ban community bi gioi han).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.heuristic import best_greedy  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.validate import makespan  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--time-limit", type=float, default=600, help="giay")
    ap.add_argument("--workers", type=int, default=1, help="1 = cong bang voi CaDiCaL / CP-SAT don luong")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lb", type=int, default=None)
    ap.add_argument("--ub", type=int, default=None)
    args = ap.parse_args()

    try:
        import docplex.cp.model  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "NOT_INSTALLED"}), flush=True)
        return 0
    from jssp.cpo import solve_cpo

    inst = read_instance(args.instance)
    lb = args.lb if args.lb is not None else inst.trivial_lower_bound()
    ub = args.ub if args.ub is not None else makespan(inst, best_greedy(inst))
    try:
        r = solve_cpo(inst, lb, ub, args.time_limit, args.workers, args.seed)
    except Exception as e:                                   # noqa: BLE001
        msg = str(e).strip()
        low = msg.lower()
        st = "LICENSE_LIMIT" if ("community" in low or "size limit" in low or "limits exceeded" in low) else "ERROR"
        print(json.dumps({"status": st, "message": msg[:300]}), flush=True)
        return 0
    r.update(instance=inst.name, lb=lb, ub=ub)
    print(json.dumps(r), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
