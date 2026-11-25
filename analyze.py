"""analyze.py — 把 results.csv 变成能看的表。

原则：
  - 人工填了 `label` 就用人工的；没填才用启发式预分类
  - 启发式结果只能看趋势，不能当结论（写论文前必须人工核）

用法:
    python analyze.py
    python analyze.py --detail --qset v2_filings --model groq-gpt-oss-120b
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

REFUSE = [
    "无法提供", "无法回答", "无法获取", "无法确认", "尚未到来", "尚未发生",
    "未来的时间", "超出我的", "没有相关", "抱歉，我没有", "我不能提供",
    "cannot provide", "don't have", "do not have", "not available",
    "as of my knowledge", "我没有",
]

DASHES = str.maketrans({"\u202f": "-", "\u00a0": "-", "\u2011": "-", "\u2013": "-", "\u2014": "-"})


def normalize(text: str) -> str:
    t = text.translate(DASHES).replace("年", "-").replace("月", "-").replace("日", "")
    return t.replace("/", "-").replace(".", "-")


def extract_iso_dates(text: str) -> set[str]:
    """从文本里抽出所有日期，统一成 YYYY-MM-DD。"""
    t = normalize(text)
    out: set[str] = set()

    for y, m, d in re.findall(r"(20\d{2})-(\d{1,2})-(\d{1,2})", t):
        out.add(f"{y}-{int(m):02d}-{int(d):02d}")

    # July 31, 2026 / Jul 31 2026
    for mon, d, y in re.findall(
        r"(" + "|".join(MONTHS) + r")[a-z]*\.?\s+(\d{1,2}),?\s+(20\d{2})", t, re.I
    ):
        out.add(f"{y}-{MONTHS[mon[:3].lower()]:02d}-{int(d):02d}")

    # 31 July 2026
    for d, mon, y in re.findall(
        r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")[a-z]*\.?,?\s+(20\d{2})", t, re.I
    ):
        out.add(f"{y}-{MONTHS[mon[:3].lower()]:02d}-{int(d):02d}")

    return out


def is_refusal(text: str) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in REFUSE)


def classify(row: dict, expected: str, category: str) -> str:
    """返回一个粗分类。人工 label 优先。"""
    if row.get("label", "").strip():
        return row["label"].strip()

    ans = row.get("answer", "")
    if ans.startswith("[ERROR]"):
        return "error"

    if category == "meta":
        return classify_meta(row, ans)

    if is_refusal(ans):
        return "refuse"

    if category == "filing_date":
        if expected and expected in extract_iso_dates(ans):
            return "correct"
        return "wrong_date" if extract_iso_dates(ans) else "other"

    return "other"


def classify_meta(row: dict, ans: str) -> str:
    run_year = row["ts_utc"][:4]
    dates = extract_iso_dates(ans)
    years = set(re.findall(r"(20\d{2})", normalize(ans)))

    if row["qid"] == "M001":
        if any(d.startswith(run_year) for d in dates) and row["ts_utc"][:10] in dates:
            return "correct"
        if dates:
            return "correct_year" if all(d.startswith(run_year) for d in dates) else "wrong_date"
        return "other"

    if row["qid"] == "M002":
        return "stated" if dates or years else "other"

    # M003 / M004：两个日期都早于真实今天，正确答案是"过去"
    has_past = "过去" in ans
    has_future = "未来" in ans
    if has_past and not has_future:
        return "correct"
    if has_future and not has_past:
        return "wrong"
    return "unclear"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="experiments/results.csv")
    ap.add_argument("--questions-dir", default="questions")
    ap.add_argument("--qset", default="", help="只看某个题库")
    ap.add_argument("--model", default="", help="只看某个模型")
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()

    qdir = Path(args.questions_dir)
    expected: dict[str, dict] = {}
    for f in qdir.glob("*.csv"):
        for r in csv.DictReader(f.open(encoding="utf-8-sig")):
            expected[r["id"]] = r

    rows = list(csv.DictReader(open(args.results, encoding="utf-8-sig")))
    if args.qset:
        rows = [r for r in rows if r["qset"] == args.qset]
    if args.model:
        rows = [r for r in rows if r["model"] == args.model]

    if not rows:
        print("没有匹配的行")
        return 1

    stat: dict[tuple[str, str, str], int] = defaultdict(int)
    for r in rows:
        meta = expected.get(r["qid"], {})
        cat = meta.get("category", "unknown")
        cls = classify(r, meta.get("expected", ""), cat)
        stat[(r["model"], cat, cls)] += 1
        r["_cls"] = cls
        r["_cat"] = cat

    models = sorted({r["model"] for r in rows})
    cats = sorted({r["_cat"] for r in rows})
    classes = ["correct", "correct_year", "wrong_date", "wrong", "refuse", "unclear", "stated", "other", "error"]

    for cat in cats:
        print(f"\n### {cat}")
        present = [c for c in classes if any(stat[(m, cat, c)] for m in models)]
        header = f'{"model":<24}{"n":>4}' + "".join(f"{c:>13}" for c in present)
        print(header)
        print("-" * len(header))
        for m in models:
            n = sum(stat[(m, cat, c)] for c in present)
            if not n:
                continue
            cells = "".join(f"{stat[(m, cat, c)] or '':>13}" for c in present)
            print(f"{m:<24}{n:>4}{cells}")

    if args.detail:
        print("\n### 明细")
        for r in rows:
            print(f'{r["qid"]:<5} {r["model"]:<24} {r["_cls"]:<12} {r["answer"][:70]}')

    print("\n注：未填 label 的行使用启发式预分类，只能看趋势，不能当结论。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
