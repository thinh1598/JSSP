"""Tai benchmark JSSP tu OR-Library (nguon ma bai bao 2010 cung dung) va tach ra tung file.

Cach dung (chay tu thu muc goc cua repo):
    python scripts/fetch_benchmarks.py                      # tai jobshop1.txt roi tach
    python scripts/fetch_benchmarks.py --from-file jobshop1.txt   # dung file da tai tay
    python scripts/fetch_benchmarks.py --only ft10 abz9 yn1

Ket qua: data/instances/<ten>.txt, cung dinh dang voi data/ft06.txt:
    dong 1 "n m"; moi dong sau la mot job gom cac cap "machine duration" (machine danh so tu 0).
Luu y: file jobshop1.txt chua ft06/10/20, la01-40, abz5-9, orb01-10, swv01-20, yn1-4.
Cac bai Taillard (ta01...) KHONG co trong file nay, tai rieng sau neu can.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp.instance import JSSPInstance, read_orlib  # noqa: E402

URL = "http://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/jobshop1.txt"


def write_instance(inst: JSSPInstance, path: Path, source: str) -> None:
    lines = [f"# {inst.name} ({inst.n_jobs}x{inst.n_machines}). Nguon: {source}",
             "# Dinh dang: 'n m'; moi dong la 1 job gom cac cap 'machine duration', machine tu 0.",
             f"{inst.n_jobs} {inst.n_machines}"]
    for job in inst.jobs:
        lines.append(" ".join(f"{m} {d}" for m, d in job))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", help="dung file jobshop1.txt da tai san thay vi tai tu mang")
    ap.add_argument("--only", nargs="*", help="chi luu cac bai nay (vd: ft10 abz9)")
    ap.add_argument("--out", default=str(ROOT / "data" / "instances"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.from_file:
        src = Path(args.from_file)
        source = f"OR-Library jobshop1.txt ({src.name})"
    else:
        src = out / "_jobshop1.txt"
        print(f"Dang tai {URL} ...")
        try:
            with urllib.request.urlopen(URL, timeout=60) as r:
                src.write_bytes(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"[LOI] Khong tai duoc: {e}\n"
                  f"Hay tai tay file tu {URL} roi chay lai voi --from-file <duong dan>.")
            return 1
        source = f"OR-Library jobshop1.txt ({URL})"

    skipped: dict = {}
    insts = read_orlib(src, skip_invalid=True, skipped=skipped)
    names = sorted(insts)
    if skipped:
        print(f"[CANH BAO] Bo qua {len(skipped)} bai khong hop le voi ma hoa Crawford:")
        for n, why in sorted(skipped.items()):
            print(f"  - {n}: {why}")
    if args.only:
        wanted = {n.lower() for n in args.only}
        names = [n for n in names if n.lower() in wanted]
        missing = wanted - {n.lower() for n in names}
        if missing:
            print("[CANH BAO] Khong tim thay:", ", ".join(sorted(missing)))

    for name in names:
        write_instance(insts[name], out / f"{name}.txt", source)
    print(f"Da luu {len(names)} bai vao {out}")
    for name in names[:60]:
        i = insts[name]
        print(f"  {name:8s} {i.n_jobs:3d}x{i.n_machines:<3d} LB>={i.trivial_lower_bound()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
