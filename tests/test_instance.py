import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.instance import _build, read_instance, read_orlib  # noqa: E402


def test_read_ft06():
    inst = read_instance(ROOT / "data" / "ft06.txt")
    assert inst.name == "ft06"
    assert (inst.n_jobs, inst.n_machines) == (6, 6)
    assert inst.jobs[0][0] == (2, 1)
    assert inst.jobs[5][5] == (2, 1)
    # moi job di qua moi may dung 1 lan
    for job in inst.jobs:
        assert sorted(m for m, _ in job) == list(range(6))


def test_bounds_ft06():
    inst = read_instance(ROOT / "data" / "ft06.txt")
    assert inst.machine_loads() == [40, 26, 26, 22, 40, 43]
    assert inst.trivial_lower_bound() == 47          # job 2 dai 47
    assert inst.trivial_lower_bound() <= 55 <= inst.trivial_upper_bound()  # 55 = toi uu da biet


def test_wrong_count_raises():
    with pytest.raises(ValueError):
        _build("bad", [2, 2, 0, 1, 1, 1, 0, 1])      # thieu so


def test_bad_duration_raises():
    with pytest.raises(ValueError):
        _build("bad", [1, 1, 0, 0])                  # duration 0 khong hop le voi Crawford


def test_read_orlib(tmp_path):
    f = tmp_path / "jobshop1.txt"
    f.write_text(
        " +++++\n instance tiny\n mot bai 2x2\n 2 2\n 0 3 1 2\n 1 2 0 4\n"
        " +++++\n instance tiny2\n 1 2\n 0 5 1 5\n",
        encoding="utf-8")
    d = read_orlib(f)
    assert set(d) == {"tiny", "tiny2"}
    assert d["tiny"].jobs == [[(0, 3), (1, 2)], [(1, 2), (0, 4)]]


def test_read_orlib_skips_invalid(tmp_path):
    f = tmp_path / "jobshop1.txt"
    f.write_text(
        " +++++\n instance ok\n 1 2\n 0 5 1 5\n"
        " +++++\n instance zero\n 1 2\n 0 0 1 5\n",   # duration 0
        encoding="utf-8")
    with pytest.raises(ValueError):
        read_orlib(f)
    skipped = {}
    d = read_orlib(f, skip_invalid=True, skipped=skipped)
    assert set(d) == {"ok"}
    assert "zero" in skipped
