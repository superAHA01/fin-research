"""从 SEC EDGAR 生成「披露日期」题。

答案不来自任何人的记忆，来自 SEC 的权威元数据：
  - reportDate（报告期结束日）
  - filingDate（实际提交日）
这两个字段正是「报告期 vs 披露日」这个项目的核心。

用法:
    python gen_filings.py --out questions/v2_filings.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# SEC 要求带联系方式，否则会 403
UA = {"User-Agent": "fin-research student 13579008yyed@gmail.com"}

COMPANIES = [
    ("0000320193", "苹果公司 (Apple)"),
    ("0000789019", "微软 (Microsoft)"),
    ("0001318605", "特斯拉 (Tesla)"),
    ("0001018724", "亚马逊 (Amazon)"),
    ("0001652044", "Alphabet (Google)"),
]

TEMPLATE = "{name} 截至 {period} 的那个财季，其 10-Q 向 SEC 提交的日期是哪一天？"

FIELDS = [
    "id",
    "question",
    "category",
    "expected",
    "evidence_url",
    "evidence_note",
    "verified_on",
]


def fetch_submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def filing_index_url(cik: str, accession: str) -> str:
    acc = accession.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{acc}/{accession}-index.htm"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="questions/v2_filings.csv")
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--per-company", type=int, default=6)
    args = ap.parse_args()

    rows: list[dict] = []
    today = date.today().isoformat()
    n = 0

    for cik, name in COMPANIES:
        data = fetch_submissions(cik)
        r = data["filings"]["recent"]
        picked = 0
        for i in range(len(r["form"])):
            if r["form"][i] != "10-Q":
                continue
            period, filed = r["reportDate"][i], r["filingDate"][i]
            if not period or period < args.since:
                continue
            n += 1
            rows.append(
                {
                    "id": f"F{n:03d}",
                    "question": TEMPLATE.format(name=name, period=period),
                    "category": "filing_date",
                    "expected": filed,
                    "evidence_url": filing_index_url(cik, r["accessionNumber"][i]),
                    "evidence_note": f"EDGAR reportDate={period}, filingDate={filed}",
                    "verified_on": today,
                }
            )
            picked += 1
            if picked >= args.per_company:
                break
        print(f"{name:<24} 生成 {picked} 题")

    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"\n共 {len(rows)} 题 -> {args.out}")
    print("全部答案来自 SEC 元数据，不需要人工核。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
