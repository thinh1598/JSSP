"""Kiem thu ma hoa Crawford.

Chien luoc: voi bai TI HON, tim makespan toi uu bang VET CAN (thu moi thu tu job tren moi may),
roi kiem tra ma hoa:  S_opt thoa (va lich giai ma hop le),  S_{opt-1} khong thoa.
Solver: PySAT (CaDiCaL) neu da cai; neu chua thi dung solver DPLL nho trong src/jssp/minisolver.py.
"""
import itertools
import os
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.crawford import CrawfordEncoder  # noqa: E402
from jssp.instance import JSSPInstance, read_instance  # noqa: E402
from jssp.minisolver import solve_dpll  # noqa: E402
from jssp.sat_solve import pysat_backend, solve_le  # noqa: E402
from jssp.validate import makespan, validate_schedule  # noqa: E402

try:
    import pysat  # noqa: F401
    BACKEND = pysat_backend("cadical153")
except ImportError:
    BACKEND = solve_dpll


def make(jobs, name="t"):
    return JSSPInstance(name, len(jobs), max(m for j in jobs for m, _ in j) + 1, jobs)


def brute_force_optimum(inst):
    """Thu moi thu tu job tren moi may; lich 'som nhat' cho moi thu tu; lay makespan nho nhat."""
    ops_on = {}
    for l, job in enumerate(inst.jobs):
        for i, (m, d) in enumerate(job):
            ops_on.setdefault(m, []).append((l, i))
    machines = sorted(ops_on)
    best = None
    for perms in itertools.product(*[itertools.permutations(ops_on[m]) for m in machines]):
        preds = {(l, i): [] for l in range(inst.n_jobs) for i in range(len(inst.jobs[l]))}
        for l, job in enumerate(inst.jobs):
            for i in range(1, len(job)):
                preds[(l, i)].append((l, i - 1))
        for order in perms:
            for a, b in zip(order, order[1:]):
                preds[b].append(a)
        start = {o: 0 for o in preds}
        for _ in range(len(preds) + 1):           # Bellman-Ford tren do thi khong chu trinh
            changed = False
            for o, ps in preds.items():
                for q in ps:
                    cand = start[q] + inst.jobs[q[0]][q[1]][1]
                    if cand > start[o]:
                        start[o] = cand
                        changed = True
            if not changed:
                break
        else:
            continue                                # con chu trinh -> khong hop le
        ms = max(start[o] + inst.jobs[o[0]][o[1]][1] for o in start)
        best = ms if best is None else min(best, ms)
    return best


HAND = [[(0, 3), (1, 2)], [(1, 2), (0, 4)]]     # A:(M1,3),(M2,2)  B:(M2,2),(M1,4)  (bai tay DAY1_GUIDE)


# ------------------------------------------------------------------------------------
def test_hand_example_counts_match_hand_derivation():
    """So bien / so clause cua tung quy tac = so ta da dem tay trong buoc 2 cua bai tap giay."""
    enc = CrawfordEncoder(make(HAND, "hand"), 8)
    s = enc.stats()
    assert s["vars"] == 6 + 2 * 4 * 9                       # 6 bien pr + (sa, eb) x 4 thao tac x t=0..8
    assert {k: s[k] for k in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")} == {
        "R1": 2, "R2": 2, "R3": 4, "R4": 4, "R5": 32, "R6": 32, "R7": 25, "R8": 38, "R9": 11}
    units = {c[0] for c in enc.clauses if len(c) == 1}
    A1, A2, B1, B2 = (0, 0), (0, 1), (1, 0), (1, 1)
    assert enc.sa(A2, 3) in units and enc.sa(B2, 2) in units       # quy tac 3
    assert enc.eb(A1, 6) in units and enc.eb(B1, 4) in units       # quy tac 4
    assert enc.pr(A1, A2) in units and enc.pr(B1, B2) in units     # quy tac 1
    assert enc.format_clause([enc.pr(A1, B2), enc.pr(B2, A1)]) == "pr[A1<B2] v pr[B2<A1]"


def test_hand_example_solves():
    inst = make(HAND, "hand")
    assert brute_force_optimum(inst) == 7
    for L, expect in [(8, "SAT"), (7, "SAT"), (6, "UNSAT")]:
        r = solve_le(inst, L, backend=BACKEND)
        assert r.status == expect, (L, r.status)
        if expect == "SAT":
            assert validate_schedule(inst, r.starts, L) == []
            assert r.makespan <= L


def test_eight_paper_rules_alone_are_unsound_at_boundary():
    """Neu CHI dung 8 quy tac nhu doc tu bai bao (khong R9), S_6 cua bai tay van 'thoa' du toi uu = 7.
    Moi mo hinh cua S_6 deu giai ma ra lich vuot L -> R9 la can thiet cho giai ma dung."""
    inst = make(HAND, "hand")
    enc = CrawfordEncoder(inst, 6, boundary_units=False)
    model = BACKEND(enc.clauses, enc.num_vars)
    assert model is not None
    assert validate_schedule(inst, enc.decode(model), 6)            # co loi (makespan 7 > 6)
    assert BACKEND(CrawfordEncoder(inst, 6).clauses, CrawfordEncoder(inst, 6).num_vars) is None


def test_growth_per_step_matches_paper():
    """Moi lan L tang 1: so bien tang 2*(so thao tac); so clause tang 3*(so thao tac) + (so bien pr)."""
    inst = make([[(0, 2), (1, 1), (2, 3)], [(1, 2), (2, 2), (0, 1)], [(2, 1), (0, 3), (1, 2)]])
    nops = 9
    a, b = CrawfordEncoder(inst, 20), CrawfordEncoder(inst, 21)
    n_pr = len(a._pr)
    assert b.num_vars - a.num_vars == 2 * nops
    assert len(b.clauses) - len(a.clauses) == 3 * nops + n_pr
    # Bai bao: ABZ9 (20 job x 15 may): +600 bien, +6880 clause moi buoc; YN1 (20x20): +800, +9180.
    # So bien pr = n(m-1) + n(n-1)m  (cap trong job + 2 chieu cho moi cap job khac nhau tren moi may)
    for n, m, dv, dc, v661 in [(20, 15, 600, 6880, 403180), (20, 20, 800, 9180, None)]:
        pr = n * (m - 1) + n * (n - 1) * m
        assert 2 * n * m == dv
        assert 3 * n * m + pr == dc
        if v661:
            assert pr + 2 * n * m * (661 + 1) == v661            # Bang 2: N=661 -> 403180 bien


def test_job_longer_than_L_is_unsat():
    inst = make([[(0, 5), (1, 5)]])
    assert solve_le(inst, 9, backend=BACKEND).status == "UNSAT"
    assert solve_le(inst, 10, backend=BACKEND).status == "SAT"
    assert CrawfordEncoder(inst, 9).trivially_unsat


def test_random_tiny_instances_match_brute_force():
    rng = random.Random(2026)
    checked = 0
    for _ in range(14):
        n, m = rng.choice([(2, 2), (3, 2), (2, 3), (3, 3)])
        jobs = []
        for _ in range(n):
            machs = list(range(m))
            rng.shuffle(machs)
            jobs.append([(mm, rng.randint(1, 3)) for mm in machs])
        inst = make(jobs)
        opt = brute_force_optimum(inst)
        r = solve_le(inst, opt, backend=BACKEND)
        assert r.status == "SAT", (jobs, opt)
        assert validate_schedule(inst, r.starts, opt) == [], (jobs, opt, r.starts)
        assert makespan(inst, r.starts) <= opt
        assert solve_le(inst, opt - 1, backend=BACKEND).status == "UNSAT", (jobs, opt)
        assert solve_le(inst, opt + 2, backend=BACKEND).status == "SAT", (jobs, opt)
        checked += 1
    assert checked == 14


def test_validate_catches_errors():
    inst = make(HAND)
    assert validate_schedule(inst, [[0, 3], [0, 3]], 7) == []
    assert validate_schedule(inst, [[0, 2], [0, 3]])                 # job A sai thu tu
    assert validate_schedule(inst, [[0, 3], [0, 1]])                 # chong tren may
    assert validate_schedule(inst, [[0, 3], [0, 3]], 6)              # vuot L
    assert validate_schedule(inst, [[0, 3]])                         # thieu job
    assert validate_schedule(inst, [[-1, 3], [0, 3]])                # thoi diem am


def test_ft06_sat_at_55():
    """Can PySAT that (solver nho khong du manh). Bo qua neu chua cai."""
    pytest.importorskip("pysat")
    inst = read_instance(ROOT / "data" / "ft06.txt")
    r = solve_le(inst, 55, "cadical153")
    assert r.status == "SAT"
    assert validate_schedule(inst, r.starts, 55) == []


def test_ft06_unsat_at_54_slow():
    """Chung minh toi uu cua FT06 = 55. Co the lau: chi chay khi dat bien moi truong JSSP_SLOW=1."""
    pytest.importorskip("pysat")
    if os.environ.get("JSSP_SLOW") != "1":
        pytest.skip("dat JSSP_SLOW=1 de chay")
    inst = read_instance(ROOT / "data" / "ft06.txt")
    assert solve_le(inst, 54, "cadical153").status == "UNSAT"
