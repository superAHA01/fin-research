"""scan_reports.py — 扫描一批 PDF 财报，判断"机器能不能读"。

回答两个问题：
  1. 这份 PDF 有文字层吗（还是纯扫描件）？
  2. 有文字层的，是不是只有附注有字、三张表是图片？

用法:
    python scan_reports.py --dir data/raw/bcel --out data/reports_meta.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from pypdf import PdfReader
except ImportError:
    print("需要 pypdf：python -m pip install pypdf")
    raise SystemExit(1)

LAO = re.compile(r"[\u0E80-\u0EFF]")


def image_count(page) -> int:
    n = 0
    try:
        xo = page.get("/Resources", {}).get("/XObject")
        if xo:
            xo = xo.get_object()
            for k in xo:
                o = xo[k].get_object()
                if o.get("/Subtype") == "/Image":
                    n += 1
    except Exception:
        pass
    return n


def inspect(path: Path, sample_pages: int = 8) -> dict:
    r = PdfReader(str(path))
    pages = len(r.pages)
    chars = lao = 0
    with_text = 0
    image_only = 0

    for i, pg in enumerate(r.pages):
        t = pg.extract_text() or ""
        if len(t.strip()) > 30:
            with_text += 1
        elif image_count(pg) > 0:
            image_only += 1
        if i < sample_pages:
            chars += len(t)
            lao += len(LAO.findall(t))

    return {
        "file": path.name,
        "size_mb": round(path.stat().st_size / 1048576, 1),
        "pages": pages,
        "pages_with_text": with_text,
        "image_only_pages": image_only,
        "sample_text_chars": chars,
        "sample_lao_chars": lao,
        "text_layer": "yes" if chars > 200 else "no",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/raw/bcel")
    ap.add_argument("--out", default="data/reports_meta.csv")
    args = ap.parse_args()

    d = Path(args.dir)
    files = sorted(d.glob("*.pdf"))
    if not files:
        print(f"{d} 里没有 PDF")
        return 1

    rows = []
    for p in files:
        try:
            rows.append(inspect(p))
        except Exception as e:
            rows.append({"file": p.name, "size_mb": round(p.stat().st_size / 1048576, 1),
                         "pages": "", "pages_with_text": "", "image_only_pages": "",
                         "sample_text_chars": "", "sample_lao_chars": "",
                         "text_layer": "ERR:" + type(e).__name__})

    print(f'{"file":<28}{"MB":>6}{"页":>5}{"有字页":>7}{"纯图片页":>9}{"老挝文":>7}  文字层')
    for r in rows:
        print(f'{r["file"]:<28}{r["size_mb"]:>6}{r["pages"]:>5}'
              f'{str(r["pages_with_text"]):>7}{str(r["image_only_pages"]):>9}'
              f'{str(r["sample_lao_chars"]):>7}  {r["text_layer"]}')

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if r["text_layer"] == "yes")
    print(f"\n共 {len(rows)} 份，有文字层 {ok} 份 -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
