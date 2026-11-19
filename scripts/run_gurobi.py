"""Giai MOT bai JSSP bang Gurobi (MIP), in ra 1 dong JSON. Thuong duoc goi boi run_baseline.py.

Chay tay:
    python scripts/run_gurobi.py data/ft06.txt --time-limit 60
Trang thai dac biet (child van thoat ma 0, cha doc dong JSON cuoi):
    NOT_INSTALLED  chua cai gurobipy
    LICENSE_LIMIT  giay phep gioi han kich thuoc (mo hinh qua lon)
    NO_LICENSE     khong tim thay giay phep hop le
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

ERR_NO_LICENSE, ERR_SIZE_LIMIT = 10009, 10010            # GRB.Error.NO_LICENSE / SIZE_LIMIT_EXCEEDED


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--time-limit", type=float, default=600, help="giay")
    ap.add_argument("--threads", type=int, default=1, help="1 = cong bang voi CaDiCaL / CP-SAT don luong")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lb", type=int, default=None, help="mac dinh: can duoi don gian")
    ap.add_argument("--ub", type=int, default=None, help="mac dinh: makespan cua heuristic")
    args = ap.parse_args()

    try:
        import gurobipy
    except ImportError:
        print(json.dumps({"status": "NOT_INSTALLED"}), flush=True)
        return 0
    from jssp.gurobi_solver import solve_gurobi

    inst = read_instance(args.instance)
    lb = args.lb if args.lb is not None else inst.trivial_lower_bound()
    ub = args.ub if args.ub is not None else makespan(inst, best_greedy(inst))
    try:
        r = solve_gurobi(inst, lb, ub, args.time_limit, args.threads, args.seed)
    except gurobipy.GurobiError as e:
        code = getattr(e, "errno", None)
        st = {ERR_SIZE_LIMIT: "LICENSE_LIMIT", ERR_NO_LICENSE: "NO_LICENSE"}.get(code, "ERROR")
        print(json.dumps({"status": st, "message": str(e)[:300]}), flush=True)
        return 0
    r.update(instance=inst.name, lb=lb, ub=ub)
    print(json.dumps(r), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
