"""Chay hang loat nhieu bai x nhieu cach (SAT nhieu lan, Incremental SAT, CP-SAT), co the de qua dem va chay tiep.

Xem truoc ke hoach, KHONG chay gi:
    python scripts/run_suite.py --tier medium --dry-run
Chay (toi da 6 tieng, o nao da co ket qua thi bo qua):
    python scripts/run_suite.py --tier medium --max-hours 6
Chon bai / cach / ngan sach rieng:
    python scripts/run_suite.py --instances la16 la17 --methods inc_binary,cpsat --budget 900
Chay lai nhung o da het gio / het RAM voi ngan sach lon hon:
    python scripts/run_suite.py --tier large --budget 7200 --retry-incomplete
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.search_multi import resolve_instance  # noqa: E402
from jssp.suite import (ALL_METHODS, TIERS, build_plan, load_done, run_suite,  # noqa: E402
                        write_environment)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", nargs="+", choices=list(TIERS), help="bac bai: small / medium / large")
    ap.add_argument("--instances", nargs="+", help="chon bai thu cong (thay cho --tier)")
    ap.add_argument("--methods", help=f"cach giai, cach nhau dau phay, trong: {','.join(ALL_METHODS)}")
    ap.add_argument("--budget", type=float, help="giay cho MOI o (bai x cach); mac dinh theo bac")
    ap.add_argument("--solver", default="cadical153")
    ap.add_argument("--workers", type=int, default=1, help="so luong CP-SAT (mac dinh 1, cong bang voi CaDiCaL)")
    ap.add_argument("--mem-limit-mb", type=float, default=None,
                    help="vuot muc nay thi dung o do (MEMOUT). Mac dinh: 70%% RAM cua may")
    ap.add_argument("--max-hours", type=float, default=None, help="het gio phien thi dung, khong bat dau o moi")
    ap.add_argument("--force", action="store_true", help="chay lai ca o da co ket qua")
    ap.add_argument("--retry-incomplete", action="store_true", help="chay lai cac o da co nhung chua OPTIMAL")
    ap.add_argument("--dry-run", action="store_true", help="chi in ke hoach")
    ap.add_argument("--tiny", action="store_true", help="DPLL nho thay PySAT (chi de thu)")
    ap.add_argument("--out", default=str(ROOT / "results" / "raw"))
    args = ap.parse_args()

    if not args.tier and not args.instances:
        ap.error("can --tier hoac --instances")
    names, methods, budget = [], None, args.budget
    for t in (args.tier or []):
        tnames, tbudget, tmethods = TIERS[t]
        names += [n for n in tnames if n not in names]
        budget = budget or tbudget
        methods = methods or tmethods
    if args.instances:
        names = args.instances
    if args.methods:
        methods = args.methods.split(",")
    methods = methods or ["inc_binary", "binary", "cpsat"]
    budget = budget or 900
    bad = [m for m in methods if m not in ALL_METHODS]
    if bad:
        ap.error(f"cach khong hop le: {bad}")

    paths = []
    for n in names:
        try:
            paths.append(resolve_instance(n))
        except FileNotFoundError:
            print(f"[bo qua] khong thay bai '{n}' (da chay scripts/fetch_benchmarks.py chua?)")

    mem = args.mem_limit_mb
    if mem is None:
        try:
            import psutil
            mem = 0.7 * psutil.virtual_memory().total / 2**20
        except Exception:
            mem = None

    out = Path(args.out)
    cells = build_plan(paths, methods, args.solver, args.tiny, args.workers, load_done(out / "summary.csv"),
                       args.force, args.retry_incomplete)
    todo = [c for c in cells if c.run]
    print(f"{'bai':8s} {'kich co':>7s} {'cach':12s} viec")
    for c in cells:
        print(f"{c.name:8s} {c.size:>7s} {c.method:12s} {'CHAY' if c.run else 'bo qua':7s} ({c.reason})")
    print(f"\nngan sach moi o: {budget:.0f}s | gioi han RAM moi o: "
          f"{'khong' if mem is None else f'{mem:.0f} MB'} | so o can chay: {len(todo)} "
          f"| toi da (neu o nao cung het gio): {len(todo) * budget / 3600:.1f} gio")
    if args.dry_run or not todo:
        return 0

    write_environment(out / "environment.txt")
    try:
        results, stopped = run_suite(cells, budget, args.solver, args.tiny, args.workers, mem, out,
                                     None if args.max_hours is None else args.max_hours * 3600)
    except KeyboardInterrupt:
        print("\nBi ngat. Cac o da xong da duoc ghi; chay lai cung lenh de tiep tuc.")
        return 130

    print("\n" + "=" * 78)
    print(f"{'bai':8s} {'cach':12s} {'ket qua':14s} {'LB':>6s} {'UB':>6s} {'giay':>9s}")
    for r in results:
        verdict = f"toi uu {r.ub}" if r.optimal else r.status
        print(f"{r.instance:8s} {r.method:12s} {verdict:14s} {r.lb:6d} {r.ub:6d} {r.total_time:9.1f}")
    print(f"\nDa ghi: {out / 'summary.csv'}" + ("  (phien bi dung do het gio)" if stopped else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
