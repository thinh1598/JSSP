"""Chay HANG LOAT: nhieu bai x nhieu cach giai, voi cung mot ngan sach thoi gian cho moi o (bai, cach).

Dac diem:
  - TIEP TUC DUOC: o nao da co dong trong summary.csv thi bo qua (tru khi --force / --retry-incomplete);
    nen bi ngat (tat may, Ctrl+C) roi chay lai cung lenh la duoc.
  - Gioi han ca phien (--max-hours): het gio thi dung khong bat dau o moi.
  - Duyet theo BAI truoc (moi bai chay xong cac cach roi moi sang bai khac), de bi ngat giua chung van co bai tron ven.
  - Moi o dung dung quy cach da kiem chung: search_multi.search (SAT) hoac baselines.run_cpsat (CP-SAT).
"""
from __future__ import annotations

import csv
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .baselines import run_cpsat
from .instance import read_instance
from .runner import CsvLog
from .search_multi import CALL_FIELDS, ROOT, SUMMARY_FIELDS, resolve_instance, search

SAT_METHODS = ("descent", "binary", "inc_descent", "inc_binary")
ALL_METHODS = SAT_METHODS + ("cpsat",)

# bac -> (danh sach bai, ngan sach giay cho MOI o, cac cach mac dinh).  Day la DU DOAN do kho, chua do tren may ban:
# o het gio van la ket qua hop le (bao khoang [LB, UB]).
TIERS: Dict[str, Tuple[List[str], int, List[str]]] = {
    "small": (["ft06", "la01", "la02", "la03", "la04", "la05", "ft10"], 600, list(ALL_METHODS)),
    "medium": (["la06", "la11", "la16", "la21", "abz5", "abz6", "orb01"], 900, ["inc_binary", "binary", "cpsat"]),
    "large": (["abz7", "abz8", "abz9", "yn1", "yn2", "yn3", "yn4"], 3600, ["inc_binary", "cpsat"]),
}


def solver_label(method: str, solver: str, tiny: bool, workers: int) -> str:
    """Nhan ghi o cot 'solver' cua summary.csv (phai khop voi search_multi / baselines)."""
    if method == "cpsat":
        return f"cpsat-w{workers}"
    return "DPLL-tiny" if tiny else solver


def load_done(summary_path) -> Dict[Tuple[str, str, str], List[str]]:
    """(bai, cach, solver) -> danh sach trang thai cua cac dong da co (theo thu tu thoi gian)."""
    done: Dict[Tuple[str, str, str], List[str]] = {}
    p = Path(summary_path)
    if not p.exists():
        return done
    with open(p, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            done.setdefault((row["instance"], row["method"], row["solver"]), []).append(row["status"])
    return done


@dataclass
class Cell:
    path: Path
    name: str            # ten bai ghi trong summary.csv
    size: str            # vd "10x10"
    method: str
    label: str           # nhan solver
    run: bool
    reason: str          # vi sao chay / bo qua


def build_plan(paths: Sequence[Path], methods: Sequence[str], solver: str, tiny: bool, workers: int,
               done: Dict[Tuple[str, str, str], List[str]], force: bool = False,
               retry_incomplete: bool = False) -> List[Cell]:
    cells: List[Cell] = []
    for path in paths:
        inst = read_instance(path)
        size = f"{inst.n_jobs}x{inst.n_machines}"
        for m in methods:
            label = solver_label(m, solver, tiny, workers)
            sts = done.get((inst.name, m, label), [])
            if force:
                run, why = True, "force"
            elif not sts:
                run, why = True, "chua chay"
            elif retry_incomplete and "OPTIMAL" not in sts:
                run, why = True, f"chay lai (da co: {sts[-1]})"
            else:
                run, why = False, f"da co: {sts[-1]}"
            cells.append(Cell(path, inst.name, size, m, label, run, why))
    return cells


def write_environment(path) -> None:
    """Ghi thong tin may + phien ban thu vien (de dua vao bao cao)."""
    lines = [f"thoi diem: {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"he dieu hanh: {platform.platform()}",
             f"CPU: {platform.processor() or 'khong ro'} | so luong logic: {os.cpu_count()}",
             f"python: {platform.python_version()}"]
    try:
        import psutil
        lines.append(f"RAM: {psutil.virtual_memory().total / 2**30:.1f} GB")
    except Exception:
        pass
    for mod in ("pysat", "ortools", "psutil"):
        try:
            m = __import__(mod)
            lines.append(f"{mod}: {getattr(m, '__version__', '?')}")
        except Exception:
            lines.append(f"{mod}: chua cai")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n---\n")


def run_suite(cells: Iterable[Cell], budget: float, solver: str = "cadical153", tiny: bool = False,
              workers: int = 1, mem_limit_mb: Optional[float] = None, out_dir=None,
              max_seconds: Optional[float] = None, clock: Callable[[], float] = time.perf_counter,
              run_sat=search, run_cp=run_cpsat, say: Callable[[str], None] = print) -> Tuple[List, bool]:
    """Chay cac o can chay. Tra ve (danh sach ket qua, bi_dung_do_het_gio_phien)."""
    out = Path(out_dir) if out_dir else ROOT / "results" / "raw"
    calls_log = CsvLog(out / "calls.csv", CALL_FIELDS)
    summary_log = CsvLog(out / "summary.csv", SUMMARY_FIELDS)
    save_dir = out.parent / "schedules"          # mac dinh results/raw -> results/schedules
    t0 = clock()
    results: List = []
    for c in cells:
        if not c.run:
            continue
        if max_seconds is not None and clock() - t0 >= max_seconds:
            say("\nHet gio phien (--max-hours): dung. Chay lai CUNG lenh de tiep tuc cac o con lai.")
            return results, True
        say(f"\n##### {c.name} ({c.size}) | {c.method} | ngan sach {budget:.0f}s | {c.reason}")
        if c.method == "cpsat":
            r = run_cp(c.path, budget, workers, 0, mem_limit_mb, summary_log, save_dir, True)
        else:
            r = run_sat(c.path, c.method, solver, None, None, budget, budget, mem_limit_mb, tiny,
                        calls_log, summary_log, save_dir, True)
        results.append(r)
    return results, False
