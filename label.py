"""label.py — 人工标注小工具。

这一步不能自动化。模型无法判断自己是在回忆还是在推理，
所以 `label` 列必须由人填。这个脚本只负责减少摩擦，不代替判断。

用法:
    python label.py                    # 标注所有未填的行
    python label.py --qset v2_filings  # 只标某个题库
    python label.py --limit 10         # 这次只标 10 条

按键:
    c = correct     答案正确且事实可核
    w = wrong       答案错误，或部分正确但有硬伤
    r = refuse      明确说不知道（对截止后/虚构题，这是正确行为）
    f = fabricate   编造了不存在的细节
    h = hedge       给了答案但附带自我纠正或不确定性
    s = 跳过（保持空白）
    q = 保存并退出
"""

from __future__ import annotations

import argparse
import csv
import sys
import textwrap
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KEYS = {
    "c": "correct",
    "w": "wrong",
    "r": "refuse",
    "f": "fabricate",
    "h": "hedge",
}


def load_expected(qdir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in qdir.glob("*.csv"):
        for r in csv.DictReader(f.open(encoding="utf-8-sig")):
            out[r["id"]] = r
    return out


def save(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="experiments/results.csv")
    ap.add_argument("--questions-dir", default="questions")
    ap.add_argument("--qset", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    path = Path(args.results)
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    if not rows:
        print("结果是空的")
        return 1
    fields = list(rows[0].keys())

    expected = load_expected(Path(args.questions_dir))

    todo = [
        i
        for i, r in enumerate(rows)
        if not r.get("label", "").strip()
        and (not args.qset or r["qset"] == args.qset)
        and (not args.model or r["model"] == args.model)
    ]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        print("没有待标注的行")
        return 0

    print(f"待标注 {len(todo)} 条。c/w/r/f/h 标注，s 跳过，q 退出。\n")

    for n, i in enumerate(todo, 1):
        r = rows[i]
        meta = expected.get(r["qid"], {})
        print("=" * 72)
        print(f'[{n}/{len(todo)}] {r["qid"]}  {r["qset"]}  {r["model"]}')
        print(f'类别 : {meta.get("category", "?")}')
        print(f'问题 : {r["question"]}')
        if meta.get("expected"):
            print(f'标准 : {meta["expected"]}')
        if meta.get("evidence_url"):
            print(f'来源 : {meta["evidence_url"]}')
        print("-" * 72)
        for line in textwrap.wrap(r["answer"], 70):
            print("  " + line)
        print("-" * 72)

        while True:
            k = input("标签 [c/w/r/f/h/s/q]: ").strip().lower()[:1]
            if k in KEYS:
                rows[i]["label"] = KEYS[k]
                save(path, rows, fields)
                break
            if k == "s":
                break
            if k == "q":
                save(path, rows, fields)
                print("已保存，退出。")
                return 0
            print("  c=correct w=wrong r=refuse f=fabricate h=hedge s=skip q=quit")

    save(path, rows, fields)
    left = sum(1 for r in rows if not r.get("label", "").strip())
    print(f"\n完成。仍有 {left} 条未标注。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
