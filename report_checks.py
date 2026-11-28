"""report_checks.py — 财务报告规则核验（Exp 1 的规则引擎基线）

只做可验证的事：
  1. 完整性：必填字段是否缺失
  2. 恒等式：资产 = 负债 + 所有者权益
  3. 跨表/比率：流动比率、负债率、ROA、经营现金流比率
  4. 合理性：负权益、流动比率异常、经营现金流为负（标记，不判定）

它不会、也不应该输出"这家公司造假"。

用法:
    python report_checks.py --in data/statements.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REQUIRED = [
    "total_assets",
    "total_liabilities",
    "equity",
    "current_assets",
    "current_liabilities",
    "revenue",
    "net_income",
    "operating_cash_flow",
]

TOLERANCE = 0.005  # 恒等式允许 0.5% 的舍入误差


def f(row: dict, k: str) -> float | None:
    v = (row.get(k) or "").strip().replace(",", "")
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def check_row(row: dict) -> tuple[list[str], dict]:
    errs: list[str] = []
    out: dict = {}

    missing = [k for k in REQUIRED if f(row, k) is None]
    if missing:
        errs.append("缺失字段: " + ", ".join(missing))

    a = f(row, "total_assets")
    l = f(row, "total_liabilities")
    e = f(row, "equity")

    if a is not None and l is not None and e is not None:
        diff = a - (l + e)
        rel = abs(diff) / a if a else 1.0
        out["identity_diff"] = diff
        if rel > TOLERANCE:
            errs.append(
                f"恒等式不平: 差 {diff:,.0f}（{rel * 100:.2f}%，容差 {TOLERANCE * 100:.1f}%）"
            )

    cr = ratio(f(row, "current_assets"), f(row, "current_liabilities"))
    dr = ratio(l, a)
    roa = ratio(f(row, "net_income"), a)
    ocfr = ratio(f(row, "operating_cash_flow"), f(row, "current_liabilities"))

    out.update({"current_ratio": cr, "debt_ratio": dr, "roa": roa, "ocf_ratio": ocfr})

    warns: list[str] = []
    if e is not None and e < 0:
        warns.append("权益为负")
    if cr is not None and cr < 1:
        warns.append("流动比率<1")
    if ocfr is not None and ocfr < 0:
        warns.append("经营现金流为负")

    out["warnings"] = warns
    return errs, out


def fmt(v: float | None, nd: int = 2) -> str:
    return "—" if v is None else f"{v:,.{nd}f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/statements.csv")
    args = ap.parse_args()

    path = Path(args.inp)
    if not path.exists():
        print(f"找不到 {path}")
        return 1

    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    if not rows:
        print("没有数据")
        return 1

    bad = 0
    print(f"共 {len(rows)} 行\n")
    for r in rows:
        fid = r.get("firm_id", "?")
        per = r.get("period", "?")
        errs, m = check_row(r)
        flag = "FAIL" if errs else "PASS"
        if errs:
            bad += 1
        print(f"[{flag}] {fid} {per}")
        print(
            f"    流动比率 {fmt(m.get('current_ratio'))}   "
            f"负债率 {fmt(m.get('debt_ratio'))}   "
            f"ROA {fmt(m.get('roa'), 3)}   "
            f"OCF比率 {fmt(m.get('ocf_ratio'))}"
        )
        for e in errs:
            print("    错误: " + e)
        for w in m.get("warnings", []):
            print("    提示: " + w + "（需人工判断，不是错误）")
        print()

    print(f"结果：{len(rows) - bad} 通过 / {bad} 有错误")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
