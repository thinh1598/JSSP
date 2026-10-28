"""Kiem thu T7: heuristic, runner (timeout/RAM/CSV) va vong tim toi uu SAT nhieu lan.

Cac test chay solver DPLL nho (tiny=True) nen khong can PySAT va rat nhanh; ket qua duoc doi chieu voi
phep vet can tren bai ngau nhien nho va voi dap an FT06 = 55.
"""
import csv
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from jssp.heuristic import best_greedy, dispatch  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.runner import CsvLog, run_with_limits  # noqa: E402
from jssp.search_multi import CALL_FIELDS, SUMMARY_FIELDS, search  # noqa: E402
from jssp.validate import makespan, validate_schedule  # noqa: E402
from test_crawford import brute_force_optimum, make  # noqa: E402

FT06 = ROOT / "data" / "ft06.txt"


def write_inst(path, inst):
    lines = [f"{inst.n_jobs} {inst.n_machines}"]
    lines += [" ".join(f"{m} {d}" for m, d in job) for job in inst.jobs]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def random_tiny(rng):
    n, m = rng.choice([(2, 2), (3, 2), (2, 3), (3, 3)])
    jobs = []
    for _ in range(n):
        machs = list(range(m))
        rng.shuffle(machs)
        jobs.append([(mm, rng.randint(1, 3)) for mm in machs])
    return make(jobs)


# ------------------------------------------------------------------ heuristic
def test_greedy_schedules_are_valid_and_within_bounds():
    rng = random.Random(1)
    insts = [read_instance(FT06)] + [random_tiny(rng) for _ in range(10)]
    for inst in insts:
        for rule in ("mwkr", "spt", "lpt"):
            assert validate_schedule(inst, dispatch(inst, rule)) == []
        s = best_greedy(inst)
        assert validate_schedule(inst, s) == []
        assert inst.trivial_lower_bound() <= makespan(inst, s) <= inst.trivial_upper_bound()


# ------------------------------------------------------------------ runner
def test_runner_ok_timeout_and_csv(tmp_path):
    ok = run_with_limits([sys.executable, "-c", "print('hi')"], timeout=30)
    assert ok.status == "OK" and ok.returncode == 0 and ok.stdout.strip() == "hi"

    slow = run_with_limits([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
    assert slow.status == "TIMEOUT" and slow.wall < 15           # tien trinh bi giet, khong cho het 30s

    log = CsvLog(tmp_path / "x.csv", ["a", "b"])
    log.append({"a": 1, "b": 2})
    log.append({"a": 3, "b": 4, "extra": 9})                     # cot thua bi bo qua
    rows = list(csv.reader(open(tmp_path / "x.csv", encoding="utf-8")))
    assert rows == [["a", "b"], ["1", "2"], ["3", "4"]]          # tieu de chi ghi mot lan


def test_runner_memout():
    pytest.importorskip("psutil")
    r = run_with_limits([sys.executable, "-c",
                         "x = bytearray(300*1024*1024); import time; time.sleep(30)"],
                        timeout=60, mem_limit_mb=120)
    assert r.status == "MEMOUT" and r.wall < 30
    assert r.peak_mem_mb is not None and r.peak_mem_mb > 120


# ------------------------------------------------------------------ vong tim toi uu
def test_search_ft06_both_methods(tmp_path):
    for method in ("descent", "binary"):
        calls = CsvLog(tmp_path / "calls.csv", CALL_FIELDS)
        summ = CsvLog(tmp_path / "summary.csv", SUMMARY_FIELDS)
        r = search(FT06, method, tiny=True, calls_log=calls, summary_log=summ,
                   save_dir=tmp_path / "sched", verbose=False)
        assert r.optimal and r.status == "OPTIMAL", (method, r.status)
        assert r.lb == r.ub == 55, (method, r.lb, r.ub)
        assert validate_schedule(read_instance(FT06), r.best_starts, 55) == []
        saved = json.loads((tmp_path / "sched" / f"ft06_{method}_DPLL-tiny.json").read_text())
        assert saved["makespan"] == 55 and saved["optimal"] is True
        # moi lan giai = 1 dong calls.csv
        n_rows = sum(1 for row in csv.DictReader(open(tmp_path / "calls.csv", encoding="utf-8"))
                     if row["method"] == method)
        assert n_rows == r.n_calls >= 1
        # chuoi UNSAT/SAT phai nhat quan: moi lan UNSAT co L < 55, moi lan SAT co L >= 55
        for c in r.calls:
            assert (c["status"] == "UNSAT") == (c["L"] < 55), c
    summary = list(csv.DictReader(open(tmp_path / "summary.csv", encoding="utf-8")))
    assert [s["method"] for s in summary] == ["descent", "binary"]
    assert all(s["optimal"] == "True" and s["ub_final"] == "55" for s in summary)


def test_search_random_tiny_matches_brute_force(tmp_path):
    rng = random.Random(77)
    k = tries = 0
    while k < 4:
        tries += 1
        assert tries < 500, "khong sinh du bai can goi solver"
        inst = random_tiny(rng)
        opt = brute_force_optimum(inst)
        # chi lay bai ma heuristic KHONG tu chung minh duoc toi uu (UB > opt hoac LB < opt),
        # de vong tim thuc su phai goi SAT solver (neu khong test se qua mot cach vo nghia)
        if makespan(inst, best_greedy(inst)) == opt == inst.trivial_lower_bound():
            continue
        path = tmp_path / f"r{k}.txt"
        write_inst(path, inst)
        for method in ("descent", "binary"):
            r = search(path, method, tiny=True, verbose=False)
            assert r.optimal and r.ub == r.lb == opt, (k, method, r.lb, r.ub, opt)
            assert r.n_calls >= 1, (k, method)
            assert validate_schedule(inst, r.best_starts, opt) == []
        k += 1


def test_total_timeout_still_reports_valid_bounds():
    r = search(FT06, "binary", tiny=True, total_timeout=0, verbose=False)
    assert r.status == "TIMEOUT" and not r.optimal
    assert r.lb == 47 and r.lb <= 55 <= r.ub                      # [LB don gian, UB heuristic] van dung
    assert validate_schedule(read_instance(FT06), r.best_starts) == []


def test_given_ub_is_verified_by_a_solve():
    ok = search(FT06, "binary", tiny=True, lb=47, ub=55, verbose=False)
    assert ok.optimal and ok.ub == 55
    assert ok.calls[0]["L"] == 55 and ok.calls[0]["status"] == "SAT"    # UB duoc xac nhan truoc
    bad = search(FT06, "binary", tiny=True, ub=50, verbose=False)       # 50 < toi uu => UB sai
    assert bad.status == "UB_INVALID" and not bad.optimal
