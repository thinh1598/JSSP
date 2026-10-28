"""Khung chay thuc nghiem: chay mot lenh trong TIEN TRINH RIENG voi gioi han thoi gian / bo nho, va ghi CSV.

Vi sao tien trinh rieng: SAT solver (CaDiCaL) khong ngat duoc tu ben trong Python; giet tien trinh la cach
chac chan nhat de dung mot lan giai qua lau, dong thoi do duoc bo nho dinh cua rieng lan giai do.
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    import psutil
except ImportError:  # van chay duoc, chi khong do duoc bo nho
    psutil = None


@dataclass
class RunInfo:
    status: str                      # "OK" | "TIMEOUT" | "MEMOUT"
    returncode: Optional[int]
    stdout: str
    stderr: str
    wall: float                      # giay
    peak_mem_mb: Optional[float]     # bo nho dinh (MB) cua ca cay tien trinh, None neu khong do duoc


def _tree(proc: "psutil.Process") -> list:
    try:
        return [proc] + proc.children(recursive=True)
    except Exception:
        return [proc]


def _mem_mb(ps) -> Optional[float]:
    """Tong bo nho dang dung cua tien trinh con va cac con cua no (tren Windows venv, python.exe
    la mot 'launcher' sinh ra tien trinh python that)."""
    total, ok = 0.0, False
    for p in _tree(ps):
        try:
            mi = p.memory_info()
            total += getattr(mi, "peak_wset", 0) or mi.rss
            ok = True
        except Exception:
            pass
    return total / 1048576 if ok else None


def _kill_tree(proc: subprocess.Popen) -> None:
    if psutil is not None:
        try:
            for p in _tree(psutil.Process(proc.pid))[::-1]:
                try:
                    p.kill()
                except Exception:
                    pass
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass
    proc.wait()


def run_with_limits(cmd: Sequence[str], timeout: Optional[float] = None,
                    mem_limit_mb: Optional[float] = None, poll: float = 0.05) -> RunInfo:
    t0 = time.perf_counter()
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as out, \
            tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as err:
        proc = subprocess.Popen(list(cmd), stdout=out, stderr=err)
        ps = psutil.Process(proc.pid) if psutil is not None else None
        peak: Optional[float] = None
        status = "OK"
        while proc.poll() is None:
            if ps is not None:
                m = _mem_mb(ps)
                if m is not None:
                    peak = m if peak is None else max(peak, m)
            el = time.perf_counter() - t0
            if timeout is not None and el > timeout:
                status = "TIMEOUT"
                break
            if mem_limit_mb is not None and peak is not None and peak > mem_limit_mb:
                status = "MEMOUT"
                break
            time.sleep(poll)
        if status != "OK":
            _kill_tree(proc)
        wall = time.perf_counter() - t0
        out.seek(0)
        err.seek(0)
        return RunInfo(status, proc.returncode if status == "OK" else None, out.read(), err.read(), wall, peak)


class CsvLog:
    """Ghi them (append) tung dong vao file CSV; tu viet dong tieu de khi file chua co.
    Luu y: dong file trong Excel truoc khi chay tiep, neu khong Windows se khoa file."""

    def __init__(self, path, fieldnames: List[str]):
        self.path = Path(path)
        self.fieldnames = fieldnames
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, row: Dict) -> None:
        new = not self.path.exists() or self.path.stat().st_size == 0
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=self.fieldnames, extrasaction="ignore", restval="")
            if new:
                w.writeheader()
            w.writerow(row)
