"""Thi nghiem KET HOP CP-SAT + Incremental SAT (bien the B, C), ghi chung results/raw/summary.csv.

Xem truoc, KHONG chay gi:
    python scripts/run_hybrid.py --dry-run
Chay (toi da 6 tieng; o nao da co ket qua thi bo qua; chay lai cung lenh de tiep tuc):
    python scripts/run_hybrid.py --max-hours 6
Chon bai / bien the rieng:
    python scripts/run_hybrid.py --instances la21 orb01 --variants B,C --budget 900

Cach A (chi SAT) va CP-SAT thuan dung lai cac dong da co (inc_binary, cpsat) tu lan chay truoc, cung ngan sach.
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.hybrid import (DEFAULT_BUDGET, DEFAULT_INSTANCES, VARIANTS, hybrid_method,  # noqa: E402
                         hybrid_solver_label, run_hybrid)
from jssp.instance import read_instance  # noqa: E402
from jssp.runner import CsvLog  # noqa: E402
from jssp.search_multi import CALL_FIELDS, SUMMARY_FIELDS, resolve_instance  # noqa: E402
from jssp.suite import load_done, write_environment  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", nargs="+", default=DEFAULT_INSTANCES)
    ap.add_argument("--variants", default="B,C", help="B = chi lay can tren cua CP-SAT; C = ca can tren va can duoi")
    ap.add_argument("--budget", type=float, help="giay cho MOI o (mac dinh: 900 cho la21/orb01, 3600 cho cac bai con lai)")
    ap.add_argument("--warmup-frac", type=float, default=0.2, help="ti le ngan sach danh cho CP-SAT khoi dong")
    ap.add_argument("--solver", default="cadical153")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--mem-limit-mb", type=float, default=None, help="mac dinh: 70%% RAM")
    ap.add_argument("--max-hours", type=float, default=None)
    ap.add_argument("--force", action="store_true", help="chay lai ca o da co ket qua")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tiny", action="store_true", help="DPLL nho (chi de thu)")
    ap.add_argument("--out", default=str(ROOT / "results" / "raw"))
    args = ap.parse_args()

    variants = args.variants.split(",")
    if any(v not in VARIANTS for v in variants):
        ap.error(f"bien the phai thuoc {VARIANTS}")
    mem = args.mem_limit_mb
    if mem is None:
        try:
            import psutil
            mem = 0.7 * psutil.virtual_memory().total / 2**20
        except Exception:
            mem = None

    out = Path(args.out)
    done = load_done(out / "summary.csv")
    label = hybrid_solver_label(args.solver, args.tiny, args.workers)
    plan, worst = [], 0.0
    print(f"{'bai':8s} {'kich co':>7s} {'ngan sach':>9s} {'khoi dong':>9s}  bien the")
    for n in args.instances:
        try:
            path = resolve_instance(n)
        except FileNotFoundError:
            print(f"[bo qua] khong thay bai '{n}'")
            continue
        inst = read_instance(path)
        budget = args.budget or DEFAULT_BUDGET.get(inst.name, 3600)
        todo = [v for v in variants if args.force or not done.get((inst.name, hybrid_method(v), label))]
        print(f"{inst.name:8s} {inst.n_jobs}x{inst.n_machines:<4d} {budget:8.0f}s {budget * args.warmup_frac:8.0f}s  "
              f"{','.join(todo) if todo else 'da co ket qua: bo qua'}")
        if todo:
            plan.append((path, budget, todo))
            worst += budget * args.warmup_frac + len(todo) * budget * (1 - args.warmup_frac)
    print(f"\ntoi da (neu moi o deu het gio): {worst / 3600:.1f} gio | gioi han RAM moi o: "
          f"{'khong' if mem is None else f'{mem:.0f} MB'}")
    if args.dry_run or not plan:
        return 0

    write_environment(out / "environment.txt")
    calls_log, summary_log = CsvLog(out / "calls.csv", CALL_FIELDS), CsvLog(out / "summary.csv", SUMMARY_FIELDS)
    t0, rows = time.perf_counter(), []
    try:
        for path, budget, todo in plan:
            for v in todo:
                if args.max_hours is not None and time.perf_counter() - t0 >= args.max_hours * 3600:
                    print("\nHet gio phien (--max-hours): dung. Chay lai CUNG lenh de tiep tuc.")
                    raise StopIteration
                print(f"\n##### {path.stem} | bien the {v} | ngan sach {budget:.0f}s")
                rows.append(run_hybrid(path, v, budget, args.warmup_frac, args.solver, args.workers, mem,
                                       args.tiny, out, calls_log, summary_log))
    except StopIteration:
        pass
    except KeyboardInterrupt:
        print("\nBi ngat. Cac o da xong da duoc ghi; chay lai cung lenh de tiep tuc.")

    print("\n" + "=" * 78)
    print(f"{'bai':8s} {'bien the':14s} {'ket qua':14s} {'LB':>6s} {'UB':>6s} {'giay':>9s}")
    for r in rows:
        verdict = f"toi uu {r.ub}" if r.optimal else r.status
        print(f"{r.instance:8s} {r.method:14s} {verdict:14s} {r.lb:6d} {r.ub:6d} {r.total_time:9.1f}")
    print(f"\nDa ghi: {out / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
