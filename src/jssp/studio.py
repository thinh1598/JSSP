"""Tim chuong trinh cua IBM ILOG CPLEX Optimization Studio (cplex.exe, cpoptimizer.exe).

Thu tu: bien moi truong JSSP_CPLEX_EXE / JSSP_CPO_EXE  ->  bien CPLEX_STUDIO_DIR*  ->  thu muc cai mac dinh tren
Windows (C:\\Program Files\\IBM\\ILOG\\CPLEX_Studio*)  ->  PATH. Tra ve None neu khong thay.
"""
from __future__ import annotations

import glob
import os
import shutil
from typing import List, Optional

SUBDIR = {"cplex": ("cplex", "cplex.exe", "cplex"), "cpoptimizer": ("cpoptimizer", "cpoptimizer.exe", "cpoptimizer")}
ENV_OVERRIDE = {"cplex": "JSSP_CPLEX_EXE", "cpoptimizer": "JSSP_CPO_EXE"}


def studio_dirs() -> List[str]:
    dirs = [v for k, v in os.environ.items() if k.upper().startswith("CPLEX_STUDIO_DIR")]
    for pat in (r"C:\Program Files\IBM\ILOG\CPLEX_Studio*", r"C:\Program Files (x86)\IBM\ILOG\CPLEX_Studio*",
                "/opt/ibm/ILOG/CPLEX_Studio*"):
        dirs += sorted(glob.glob(pat), reverse=True)          # ban moi nhat truoc
    return dirs


def find_exe(kind: str) -> Optional[str]:
    """kind: 'cplex' hoac 'cpoptimizer'."""
    sub, exe_win, exe_nix = SUBDIR[kind]
    override = os.environ.get(ENV_OVERRIDE[kind])
    if override and os.path.exists(override):
        return override
    for d in studio_dirs():
        for pat in (os.path.join(d, sub, "bin", "x64_win64", exe_win),
                    os.path.join(d, sub, "bin", "x86-64_linux", exe_nix)):
            hits = glob.glob(pat)
            if hits:
                return hits[0]
    return shutil.which(exe_win) or shutil.which(exe_nix)
