"""Kiem thu T11: baseline Gurobi (MIP).

Phan 1 (luon chay, khong can Gurobi): cong thuc MIP trong mip.py duoc kiem chung bang phep vet can doc lap
        (thu moi cach chon y, tim lich som nhat) - doi chieu voi brute_force_optimum; khung chay bang tien trinh con GIA.
Phan 2 (can `pip install gurobipy` + giay phep, tu bo qua neu khong co): giai that.
"""
import csv
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import jssp.baselines as bl  # noqa: E402
from jssp.gurobi_solver import map_status  # noqa: E402
from jssp.heuristic import best_greedy  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.mip import (CMAX, build_mip, check_assignment, earliest_for_fixed_y,  # noqa: E402
                      optimum_by_enumeration, y_from_starts)
from jssp.runner import CsvLog, RunInfo  # noqa: E402
from jssp.search_multi import SUMMARY_FIELDS  # noqa: E402
from jssp.suite import Cell, run_suite, solver_label  # noqa: E402
from jssp.validate import makespan, validate_schedule  # noqa: E402
from test_cpsat import FT06, OPT55, fake_child  # noqa: E402
from test_crawford import HAND, brute_force_optimum, make  # noqa: E402
from test_search import random_tiny  # noqa: E402


# ------------------------------------------------------------------ cong thuc MIP (khong can solver)
def test_model_size_on_ft06():
    inst = read_instance(FT06)
    spec = build_mip(inst, 47, 59)
    assert len(spec.ops) == 36 and len(spec.ykeys) == 6 * 15                      # moi may: C(6,2) cap
    assert len(spec.cons) == 6 * 5 + 6 + 2 * 90                                   # thu tu job + makespan + 2/cap
    assert (spec.lo[CMAX], spec.hi[CMAX]) == (47, 59)


def test_start_windows_use_head_and_tail():
    inst = make(HAND)                      # A:(M1,3),(M2,2)  B:(M2,2),(M1,4)
    spec = build_mip(inst, 6, 10)
    assert (spec.lo[(0, 0)], spec.hi[(0, 0)]) == (0, 10 - 2 - 3)                  # tail=2
    assert (spec.lo[(0, 1)], spec.hi[(0, 1)]) == (3, 10 - 0 - 2)                  # head=3
    assert (spec.lo[(1, 1)], spec.hi[(1, 1)]) == (2, 10 - 4)


def test_known_optimal_schedule_satisfies_every_constraint():
    inst = read_instance(FT06)
    spec = build_mip(inst, 47, 59)
    y = y_from_starts(spec, OPT55)
    s = {(l, i): OPT55[l][i] for l in range(6) for i in range(6)}
    assert check_assignment(spec, s, y, 55) == []
    assert check_assignment(spec, s, y, 54)                                      # C nho hon makespan that: phai vi pham
    bad = dict(s)
    bad[(0, 0)] = bad[(0, 0)] + 5                                                # day 1 thao tac -> pha thu tu/chong nhau
    assert check_assignment(spec, bad, y, 55)


def test_greedy_schedules_are_feasible_for_the_model():
    rng = random.Random(5)
    for inst in [read_instance(FT06)] + [random_tiny(rng) for _ in range(15)]:
        starts = best_greedy(inst)
        ub = makespan(inst, starts)
        spec = build_mip(inst, inst.trivial_lower_bound(), ub)
        s = {(l, i): starts[l][i] for l in range(inst.n_jobs) for i in range(len(inst.jobs[l]))}
        assert check_assignment(spec, s, y_from_starts(spec, starts), ub) == []    # big-M khong cat mat loi giai hop le


def test_model_optimum_equals_brute_force_on_random_tiny():
    rng = random.Random(11)
    for _ in range(25):
        inst = random_tiny(rng)
        ub = makespan(inst, best_greedy(inst))
        want = brute_force_optimum(inst)
        spec = build_mip(inst, inst.trivial_lower_bound(), ub)
        assert optimum_by_enumeration(spec) == want
        spec_exact_ub = build_mip(inst, inst.trivial_lower_bound(), want)         # ub = toi uu van kha thi
        assert optimum_by_enumeration(spec_exact_ub) == want
        if want > inst.trivial_lower_bound():
            assert optimum_by_enumeration(build_mip(inst, inst.trivial_lower_bound(), want - 1)) is None


def test_hand_instance_optimum():
    inst = make(HAND)
    spec = build_mip(inst, inst.trivial_lower_bound(), inst.trivial_upper_bound())
    assert optimum_by_enumeration(spec) == brute_force_optimum(inst)


def test_inconsistent_orders_are_infeasible():
    inst = make([[(0, 1)], [(0, 1)], [(0, 1)]])                 # 3 job, moi job 1 thao tac tren cung 1 may
    spec = build_mip(inst, 3, 3)
    (a, b), (a2, c), (b2, c2) = spec.ykeys
    cyc = {(a, b): 1, (a2, c): 0, (b2, c2): 1}                  # a<b, b<c, c<a: vong tron, khong the
    assert earliest_for_fixed_y(spec, cyc) is None
    ok = {(a, b): 1, (a2, c): 1, (b2, c2): 1}                   # a<b<c
    assert earliest_for_fixed_y(spec, ok)[CMAX] == 3
    assert optimum_by_enumeration(spec) == 3
    assert optimum_by_enumeration(build_mip(inst, 0, 2)) is None  # 3 viec don vi tren 1 may khong the xong truoc 3


# ------------------------------------------------------------------ khung chay (child gia)
def test_status_mapping():
    assert map_status(2, 1) == "OPTIMAL"
    assert map_status(3, 0) == "INFEASIBLE" and map_status(4, 0) == "INFEASIBLE"
    assert map_status(9, 3) == "FEASIBLE" and map_status(9, 0) == "UNKNOWN"      # het gio co / chua co loi giai
    assert map_status(17, 0) == "UNKNOWN"


def test_solver_label_for_gurobi():
    assert solver_label("gurobi", "cadical153", False, 1) == "gurobi-t1"
    assert solver_label("gurobi", "cadical153", True, 4) == "gurobi-t4"


def test_gurobi_optimal_is_logged_and_saved(monkeypatch, tmp_path):
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 55.00003, "starts": OPT55})
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = bl.run_gurobi(FT06, time_limit=10, summary_log=log, save_dir=tmp_path / "sch", verbose=False)
    assert r.optimal and r.lb == r.ub == 55 and r.method == "gurobi" and r.solver == "gurobi-t1"
    row = list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8")))[0]
    assert row["method"] == "gurobi" and row["solver"] == "gurobi-t1" and row["lb_init"] == "47"
    assert (tmp_path / "sch" / "ft06_gurobi_gurobi-t1.json").exists()


def test_gurobi_bound_rounding_tolerates_solver_noise(monkeypatch):
    fake_child(monkeypatch, {"status": "FEASIBLE", "makespan": 55, "best_bound": 50.00004, "starts": OPT55})
    r = bl.run_gurobi(FT06, verbose=False)
    assert (r.lb, r.ub, r.status) == (50, 55, "TIMEOUT")        # 50.00004 la 50 + sai so, KHONG phai can duoi 51
    fake_child(monkeypatch, {"status": "FEASIBLE", "makespan": 55, "best_bound": 50.3, "starts": OPT55})
    assert bl.run_gurobi(FT06, verbose=False).lb == 51          # that su > 50.0001 thi tran len 51


def test_gurobi_never_claims_a_bound_above_its_schedule(monkeypatch):
    fake_child(monkeypatch, {"status": "FEASIBLE", "makespan": 55, "best_bound": 56.0, "starts": OPT55})
    r = bl.run_gurobi(FT06, verbose=False)
    assert r.lb <= r.ub == 55


@pytest.mark.parametrize("st", ["NOT_INSTALLED", "NO_LICENSE", "LICENSE_LIMIT"])
def test_license_problems_write_nothing(monkeypatch, tmp_path, capsys, st):
    fake_child(monkeypatch, {"status": st, "message": "x"})
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = bl.run_gurobi(FT06, summary_log=log, save_dir=tmp_path / "sch")
    assert r.status == st and not r.optimal
    assert not (tmp_path / "s.csv").exists() or list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8"))) == []
    assert not (tmp_path / "sch").exists()
    assert st in capsys.readouterr().out


def test_invalid_schedule_from_gurobi_is_rejected(monkeypatch):
    bad = [[0] * 6 for _ in range(6)]
    fake_child(monkeypatch, {"status": "OPTIMAL", "makespan": 55, "best_bound": 55.0, "starts": bad})
    assert bl.run_gurobi(FT06, verbose=False).status == "ERROR"


def test_suite_stops_trying_gurobi_after_license_failure(tmp_path):
    cells = [Cell(FT06, n, "6x6", "gurobi", "gurobi-t1", True, "x") for n in ("ft06", "ft06b", "ft06c")]
    calls = []

    def fake_gu(path, budget, workers, seed, mem, summary_log, save_dir, verbose):
        calls.append(path)
        return SimpleNamespace(method="gurobi", status="LICENSE_LIMIT")

    results, stopped = run_suite(cells, 60, out_dir=tmp_path / "raw", run_gu=fake_gu, say=lambda s: None)
    assert len(calls) == 1 and results == [] and not stopped       # lan dau loi giay phep -> khong thu lai, khong ghi bang


def test_run_gurobi_script_reports_missing_package():
    code = ("import sys, runpy; sys.modules['gurobipy'] = None; "
            f"sys.argv = ['run_gurobi.py', r'{FT06}']; runpy.run_path(r'{ROOT / 'scripts' / 'run_gurobi.py'}', run_name='__main__')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert json.loads(r.stdout.strip().splitlines()[-1]) == {"status": "NOT_INSTALLED"}


def load_script():
    spec = importlib.util.spec_from_file_location("run_gurobi_script", ROOT / "scripts" / "run_gurobi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("errno,expected", [(10010, "LICENSE_LIMIT"), (10009, "NO_LICENSE"), (10001, "ERROR")])
def test_run_gurobi_script_maps_gurobi_errors(monkeypatch, capsys, errno, expected):
    class GurobiError(Exception):
        pass

    stub = SimpleNamespace(GurobiError=GurobiError)
    monkeypatch.setitem(sys.modules, "gurobipy", stub)
    import jssp.gurobi_solver as gs

    def boom(*a, **k):
        e = GurobiError("Model too large for size-limited license")
        e.errno = errno
        raise e

    monkeypatch.setattr(gs, "solve_gurobi", boom)
    mod = load_script()
    monkeypatch.setattr(sys, "argv", ["run_gurobi.py", str(FT06)])
    assert mod.main() == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["status"] == expected


# ------------------------------------------------------------------ giai that (can gurobipy + giay phep)
def real_gurobi_or_skip():
    gp = pytest.importorskip("gurobipy")
    try:
        m = gp.Model()
        m.Params.OutputFlag = 0
        m.addVar()
        m.optimize()
    except gp.GurobiError as e:
        pytest.skip(f"Gurobi khong dung duoc: {e}")


def test_real_gurobi_ft06():
    real_gurobi_or_skip()
    from jssp.gurobi_solver import solve_gurobi
    inst = read_instance(FT06)
    r = solve_gurobi(inst, inst.trivial_lower_bound(), 59, time_limit=120, threads=1)
    assert r["status"] == "OPTIMAL" and r["makespan"] == 55
    assert validate_schedule(inst, r["starts"], 55) == []


def test_real_gurobi_matches_brute_force_on_random_tiny():
    real_gurobi_or_skip()
    from jssp.gurobi_solver import solve_gurobi
    rng = random.Random(3)
    for _ in range(8):
        inst = random_tiny(rng)
        ub = makespan(inst, best_greedy(inst))
        r = solve_gurobi(inst, inst.trivial_lower_bound(), ub, time_limit=30)
        assert r["status"] == "OPTIMAL" and r["makespan"] == brute_force_optimum(inst)
        assert validate_schedule(inst, r["starts"], ub) == []


def test_real_end_to_end_subprocess(tmp_path):
    real_gurobi_or_skip()
    log = CsvLog(tmp_path / "s.csv", SUMMARY_FIELDS)
    r = bl.run_gurobi(FT06, time_limit=120, summary_log=log, verbose=False)
    assert r.optimal and r.lb == r.ub == 55
    assert list(csv.DictReader(open(tmp_path / "s.csv", encoding="utf-8")))[0]["method"] == "gurobi"
