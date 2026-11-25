"""probe.py — 多模型一致性探针

设计目标：**题库是常量，模型是变量。**

  - 加一个模型 = 在 models.toml 里加一段配置，不改代码
  - 题库冻结成 v1，以后只新增 v2，永不修改 v1
    （改了历年结果就不可比，长期项目的价值就没了）

用法:
    pip install -r requirements.txt
    python probe.py --check                 # 列出各模型可用 ID
    python probe.py                         # 跑默认题库
    python probe.py --model gemini-3.5-flash-lite
    python probe.py --qset questions/v1.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Windows 控制台默认不是 UTF-8，中文会变乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

FIELDS = [
    "ts_utc",
    "qset",
    "qid",
    "run",
    "model",
    "model_id",
    "question",
    "answer",
    "latency_s",
    "label",
    "note",
]


def load_models(path: str = "models.toml") -> list[dict]:
    with open(path, "rb") as f:
        return tomllib.load(f)["model"]


def load_questions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("question") or "").strip()]


def build_clients(models: list[dict], wanted: list[str]) -> dict[str, tuple[OpenAI, dict]]:
    active: dict[str, tuple[OpenAI, dict]] = {}
    for m in models:
        name = m["name"]
        if m.get("enabled", True) is False:
            continue
        if wanted and name not in wanted:
            continue
        env_key = m.get("env_key", "")
        key = os.getenv(env_key, "").strip() if env_key else ""
        if env_key and not key:
            print(f"[skip] {name}: 没找到 {env_key}", file=sys.stderr)
            continue
        active[name] = (OpenAI(base_url=m["base_url"], api_key=key or "no-key"), m)
    return active


def ask(client: OpenAI, model_id: str, question: str, retries: int = 3) -> str:
    """调一次模型。遇到 429/5xx 自动退避重试，免费额度很容易 503。"""
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model_id,
                temperature=0,
                messages=[{"role": "user", "content": question}],
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            status = getattr(e, "status_code", None)
            transient = status in (429, 500, 502, 503, 504)
            if attempt == retries or not transient:
                raise
            print(
                f"   ... {status} 过载，{delay:.0f}s 后重试 ({attempt}/{retries - 1})",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def check_models(active: dict[str, tuple[OpenAI, dict]]) -> int:
    """列出每家当前可用的模型 ID。模型名过时的时候先跑这个。"""
    for name, (client, m) in active.items():
        print(f"\n=== {name} ({m['model_id']}) ===")
        try:
            ids = [x.id for x in client.models.list().data]
        except Exception as e:
            print(f"  列不出来（有的厂商不支持 /models）: {type(e).__name__}: {e}")
            continue
        for i in sorted(ids)[:40]:
            print("   ", i)
        if len(ids) > 40:
            print(f"    ... 共 {len(ids)} 个")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qset", default="questions/v1.csv", help="题库文件，默认 v1")
    ap.add_argument("--out", default="experiments/results.csv")
    ap.add_argument("--model", action="append", default=[], help="只跑指定模型，可重复")
    ap.add_argument(
        "--repeat",
        type=int,
        default=3,
        help="每题重复次数，默认 3（temperature=0 也不保证确定性）",
    )
    ap.add_argument("--models-file", default="models.toml")
    ap.add_argument("--check", action="store_true", help="只列各家可用模型，不发问题")
    args = ap.parse_args()

    load_dotenv()

    qset_path = Path(args.qset)
    if not qset_path.exists():
        print(f"题库不存在: {qset_path}", file=sys.stderr)
        return 1
    qset = qset_path.stem  # "v1"

    active = build_clients(load_models(args.models_file), args.model)
    if not active:
        print("没有可用的模型，检查 .env 和 models.toml", file=sys.stderr)
        return 1

    if args.check:
        return check_models(active)

    questions = load_questions(qset_path)
    if not questions:
        print(f"{qset_path} 里没有题目", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists()

    with out.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()

        for q in questions:
            for name, (client, m) in active.items():
                for run in range(1, args.repeat + 1):
                    t0 = time.time()
                    try:
                        ans = ask(client, m["model_id"], q["question"])
                    except Exception as e:  # 免费额度会 429/超时，记下来继续
                        ans = f"[ERROR] {type(e).__name__}: {e}"
                    dt = round(time.time() - t0, 2)

                    w.writerow(
                        {
                            "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "qset": qset,
                            "qid": q.get("id", ""),
                            "run": run,
                            "model": name,
                            "model_id": m["model_id"],
                            "question": q["question"],
                            "answer": ans.replace("\n", " ")[:2000],
                            "latency_s": dt,
                            "label": "",  # 人工填，见 README
                            "note": "",
                        }
                    )
                    f.flush()
                    print(
                        f"{q.get('id', '?'):>6} {name:<26} #{run} {dt:>6.1f}s  {ans[:50]}"
                    )

    print(f"\n写入 {out} —— 记得打开填 label 列")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
