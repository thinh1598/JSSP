"""Gop ket qua thi nghiem thanh bang / so lieu bao cao va kiem tra nhat quan.

    python scripts/analyze.py                     # doc results/raw/summary.csv, ghi vao results/analysis/
    python scripts/analyze.py --summary duong_dan --out thu_muc

Dau ra (trong results/analysis/):
  table_main.md/.csv/.tex   bang chinh (cac cau hinh 1 luong, bai x cach); in dam = cach tot nhat tren bai do
  table_extra.md/.csv       bang phu (SAT giam dan, hybrid)
  summary_by_method.csv/.md so bai giai xong, PAR2, khoang cach trung binh, RAM theo bac
  best_bounds.csv/.md       can duoi / can tren tot nhat moi bai va cach nao dat duoc
  cactus.csv (+ cactus.png neu co matplotlib)
  consistency.txt           kiem tra nhat quan giua cac solver (muc LOI can xem ngay)
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jssp import analysis as an  # noqa: E402


def write_csv(path: Path, rows, header=None):
    rows = list(rows)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh) if header is None and rows and isinstance(rows[0], (list, tuple)) else None
        if w:
            w.writerows(rows)
        elif rows:
            dw = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            dw.writeheader()
            dw.writerows(rows)


def md_of_dicts(rows) -> str:
    if not rows:
        return "(trong)\n"
    keys = list(rows[0].keys())
    out = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    out += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default=str(ROOT / "results" / "raw" / "summary.csv"))
    ap.add_argument("--known", default=str(ROOT / "data" / "known_bounds.csv"))
    ap.add_argument("--out", default=str(ROOT / "results" / "analysis"))
    args = ap.parse_args()

    rows, replaced = an.load_rows(args.summary)
    known = an.load_known(args.known)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = an.instance_order(rows.values())

    main_t = an.comparison_table(rows, an.MAIN_COLS)
    bold = an._bold_flags(rows, an.MAIN_COLS, names)
    (out / "table_main.md").write_text(an.to_markdown(main_t, bold), encoding="utf-8")
    (out / "table_main.tex").write_text(an.to_latex(
        main_t, bold, caption="Ket qua (giay neu giai xong, [can duoi, can tren] neu het gio), 1 luong.",
        label="tab:main"), encoding="utf-8")
    write_csv(out / "table_main.csv", main_t)
    extra_t = an.comparison_table(rows, an.EXTRA_COLS)
    (out / "table_extra.md").write_text(an.to_markdown(extra_t), encoding="utf-8")
    write_csv(out / "table_extra.csv", extra_t)

    summ = an.summary_by_method(rows, an.MAIN_COLS)
    write_csv(out / "summary_by_method.csv", summ)
    (out / "summary_by_method.md").write_text(md_of_dicts(summ), encoding="utf-8")
    bb = an.best_bounds(rows)
    write_csv(out / "best_bounds.csv", bb)
    (out / "best_bounds.md").write_text(md_of_dicts(bb), encoding="utf-8")
    cactus = an.cactus_data(rows, an.MAIN_COLS)
    write_csv(out / "cactus.csv", cactus)

    msgs = an.check_consistency(rows, known)
    lines = [f"{lvl}: {m}" for lvl, m in msgs] or ["Khong co mau thuan hay canh bao nao."]
    header = [f"Doc {len(rows)} o (da bo {replaced} dong cu bi chay lai de len).",
              f"Tong so muc LOI: {sum(1 for l, _ in msgs if l == 'LOI')}, CANH BAO: {sum(1 for l, _ in msgs if l != 'LOI')}", ""]
    (out / "consistency.txt").write_text("\n".join(header + lines) + "\n", encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        for label in dict.fromkeys(r["method"] for r in cactus):
            pts = [r for r in cactus if r["method"] == label]
            ax.step([p["solved"] for p in pts], [p["time_s"] for p in pts], where="post", marker="o", ms=3, label=label)
        ax.set_yscale("log"); ax.set_xlabel("so bai da giai xong"); ax.set_ylabel("thoi gian (s)")
        ax.legend(fontsize=7); ax.grid(alpha=.3)
        fig.tight_layout(); fig.savefig(out / "cactus.png", dpi=150)
    except Exception as e:                                   # noqa: BLE001
        print("(bo qua hinh cactus:", e, ")")

    print(an.to_markdown(main_t, bold))
    print(md_of_dicts(summ))
    print("\n".join(header + lines))
    print(f"\nDa ghi vao {out}")
    return 1 if any(l == "LOI" for l, _ in msgs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
