"""Tim toi uu bang INCREMENTAL SAT trong MOT tien trinh (ma hoa 1 lan, doi L bang assumptions).

Moi lan hoi in ra 1 dong JSON (flush ngay), nen neu bi giet giua chung tien trinh cha van doc duoc cac lan da xong.
Thuong duoc goi boi search_multi (method inc_descent / inc_binary); cung chay tay duoc:

    python scripts/run_inc.py data/ft06.txt --method binary
    python scripts/run_inc.py data/ft10.txt --method binary --solver glucose4
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.heuristic import best_greedy  # noqa: E402
from jssp.incremental import (IncrementalSession, incremental_search, pysat_factory,  # noqa: E402
                              restarting_factory)
from jssp.instance import read_instance  # noqa: E402
from jssp.validate import makespan  # noqa: E402


def out(obj) -> None:
    print(json.dumps(obj), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--method", choices=["descent", "binary"], default="binary")
    ap.add_argument("--solver", default="cadical153", help="solver PySAT HO TRO assumptions (cadical153, glucose4, ...)")
    ap.add_argument("--lo", type=int, default=None, help="can duoi (mac dinh: can duoi don gian)")
    ap.add_argument("--hi", type=int, default=None, help="can tren = chan troi H (mac dinh: heuristic)")
    ap.add_argument("--tiny", action="store_true", help="DPLL nho (khong incremental that, chi de thu)")
    args = ap.parse_args()

    inst = read_instance(args.instance)
    lo = args.lo if args.lo is not None else inst.trivial_lower_bound()
    hi = args.hi if args.hi is not None else makespan(inst, best_greedy(inst))
    if args.tiny:
        from jssp.minisolver import solve_dpll
        factory = restarting_factory(solve_dpll)
    else:
        factory = pysat_factory(args.solver)

    with IncrementalSession(inst, hi, factory) as ses:
        out({"event": "encoded", "H": hi, "vars": ses.num_vars, "clauses": ses.num_clauses,
             "encode_time": round(ses.encode_time, 3)})
        t0 = time.perf_counter()
        lo, hi = incremental_search(ses, args.method, lo, hi, emit=lambda r: out({"event": "call", **r}))
        out({"event": "done", "lo": lo, "hi": hi, "total_solve_time": round(time.perf_counter() - t0, 3)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
