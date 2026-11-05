"""Kiem thu T8: Incremental SAT (ma hoa 1 lan o chan troi H, doi L bang assumptions).

Phan lon test dung solver DPLL nho qua RestartingAdapter (logic giong het, chi khong tan dung clause hoc duoc),
nen chay duoc khi chua co PySAT; test cuoi dung PySAT that va tu bo qua neu chua cai.
"""
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from jssp.crawford import CrawfordEncoder  # noqa: E402
from jssp.heuristic import best_greedy  # noqa: E402
from jssp.incremental import IncrementalSession, incremental_search, restarting_factory  # noqa: E402
from jssp.instance import read_instance  # noqa: E402
from jssp.minisolver import solve_dpll  # noqa: E402
from jssp.runner import run_with_limits  # noqa: E402
from jssp.sat_solve import solve_le  # noqa: E402
from jssp.search_multi import search  # noqa: E402
from jssp.validate import makespan, validate_schedule  # noqa: E402
from test_crawford import brute_force_optimum  # noqa: E402
from test_search import random_tiny  # noqa: E402

FT06 = ROOT / "data" / "ft06.txt"
TINY = restarting_factory(solve_dpll)


def test_assumptions_for():
    inst = read_instance(FT06)
    enc = CrawfordEncoder(inst, 59)
    n_ops = sum(len(j) for j in inst.jobs)
    a = enc.assumptions_for(55)
    assert len(a) == n_ops and all(0 < x <= enc.num_vars for x in a)
    assert enc.assumptions_for(59) == [enc.eb(op, 59 - enc._tail[op]) for op in enc._ops]   # L = H la R4 cua goc
    assert enc.assumptions_for(inst.trivial_lower_bound() - 1) is None                      # < LB don gian => UNSAT chac
    with pytest.raises(ValueError):
        enc.assumptions_for(60)                                                              # vuot chan troi


def test_session_matches_brute_force_in_any_query_order():
    """Cung mot phien, hoi L theo thu tu NGAU NHIEN: ket qua phai la 'SAT <=> L >= toi uu' (assumptions khong ro ri)."""
    rng = random.Random(5)
    for _ in range(8):
        inst = random_tiny(rng)
        opt = brute_force_optimum(inst)
        H = makespan(inst, best_greedy(inst))
        with IncrementalSession(inst, H, TINY) as ses:
            Ls = list(range(0, H + 1)) * 2
            rng.shuffle(Ls)
            for L in Ls:
                r = ses.query(L)
                assert (r["status"] == "SAT") == (L >= opt), (L, opt, r["status"])
                if r["status"] == "SAT":
                    assert validate_schedule(inst, r["starts"], L) == []
                    assert r["makespan"] <= L


def test_session_agrees_with_fresh_encoding():
    rng = random.Random(11)
    for _ in range(6):
        inst = random_tiny(rng)
        H = makespan(inst, best_greedy(inst))
        with IncrementalSession(inst, H, TINY) as ses:
            for L in range(inst.trivial_lower_bound(), H + 1):
                assert ses.query(L)["status"] == solve_le(inst, L, backend=solve_dpll).status


@pytest.mark.parametrize("method", ["descent", "binary"])
def test_incremental_search_matches_brute_force(method):
    rng = random.Random(21)
    for _ in range(8):
        inst = random_tiny(rng)
        opt = brute_force_optimum(inst)
        lo, hi = inst.trivial_lower_bound(), makespan(inst, best_greedy(inst))
        seen = []
        with IncrementalSession(inst, hi, TINY) as ses:
            lo2, hi2 = incremental_search(ses, method, lo, hi, emit=seen.append)
        assert lo2 == hi2 == opt, (method, lo2, hi2, opt)
        assert len(seen) == (0 if lo == hi else len(seen))
        for r in seen:
            assert (r["status"] == "UNSAT") == (r["L"] < opt)


def test_session_rejects_too_small_horizon():
    inst = read_instance(FT06)
    with pytest.raises(ValueError):
        IncrementalSession(inst, 10, TINY)                      # 10 < do dai mot job
    with IncrementalSession(inst, 59, TINY) as ses:
        with pytest.raises(ValueError):
            incremental_search(ses, "binary", 47, 60)           # hi vuot chan troi cua phien


@pytest.mark.parametrize("method", ["inc_descent", "inc_binary"])
def test_search_ft06_incremental(tmp_path, method):
    r = search(FT06, method, tiny=True, save_dir=tmp_path, verbose=False)
    assert r.optimal and r.status == "OPTIMAL" and r.lb == r.ub == 55, (r.status, r.lb, r.ub)
    assert validate_schedule(read_instance(FT06), r.best_starts, 55) == []
    assert r.n_calls >= 1
    for c in r.calls:
        assert (c["status"] == "UNSAT") == (c["L"] < 55), c
    assert c["status"] in ("SAT", "UNSAT") and r.calls[0]["encode_time"] >= 0
    assert (tmp_path / f"ft06_{method}_DPLL-tiny.json").exists()


def test_search_incremental_with_given_ub_and_total_timeout():
    ok = search(FT06, "inc_binary", tiny=True, lb=47, ub=55, verbose=False)
    assert ok.optimal and ok.ub == 55 and ok.calls[0]["status"] == "SAT"     # UB duoc xac nhan truoc
    r = search(FT06, "inc_binary", tiny=True, total_timeout=0, verbose=False)
    assert r.status == "TIMEOUT" and not r.optimal and r.lb == 47 and r.lb <= 55 <= r.ub


def test_runner_keeps_partial_stdout_when_killed():
    """Nen tang cua Incremental trong tien trinh con: bi giet giua chung van doc duoc cac dong da in."""
    r = run_with_limits([sys.executable, "-c",
                         "import time; print('{\"event\": \"call\"}', flush=True); time.sleep(30)"], timeout=2)
    assert r.status == "TIMEOUT" and '"event": "call"' in r.stdout


@pytest.mark.parametrize("solver", ["glucose4", "cadical153"])
def test_real_pysat_incremental_ft06(solver):
    pytest.importorskip("pysat")
    from jssp.incremental import pysat_factory
    inst = read_instance(FT06)
    with IncrementalSession(inst, 59, pysat_factory(solver)) as ses:
        assert ses.query(55)["status"] == "SAT"
        assert ses.query(54)["status"] == "UNSAT"
        assert ses.query(58)["status"] == "SAT"                # tang L sau UNSAT: gia dinh khong de lai dau vet
        assert ses.query(55)["status"] == "SAT"
        lo, hi = incremental_search(ses, "binary", 47, 59)
    assert lo == hi == 55
