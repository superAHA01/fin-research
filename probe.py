"""probe.py — 多模型一致性探针

同一批问题打给多个模型，答案存成 CSV，人工打标签后统计。

用法:
    pip install -r requirements.txt
    cp .env.example .env                 # 填至少一个 key
    python probe.py                      # 默认跑 questions.csv
    python probe.py --models gemini      # 只跑一个

设计原则:
    1. 只依赖 OpenAI 兼容接口 —— 换厂商只改 MODELS，别的代码不动
    2. 没有 key 的模型自动跳过，不会崩
    3. 结果 append 到 CSV，不覆盖历史；每次带时间戳
    4. temperature=0，保证可复现
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# name: (base_url, env_key, model_id)
# 模型名以各家当前免费列表为准，过时了只改这里
MODELS = {
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "GEMINI_KEY",
        "gemini-2.5-flash",
    ),
    "groq": (
        "https://api.groq.com/openai/v1",
        "GROQ_KEY",
        "llama-3.3-70b-versatile",
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1",
        "OPENROUTER_KEY",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
}

FIELDS = ["ts_utc", "qid", "model", "question", "answer", "latency_s", "label", "note"]


def load_questions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("question") or "").strip()]


def build_clients(wanted: list[str]) -> dict[str, tuple[OpenAI, str]]:
    active: dict[str, tuple[OpenAI, str]] = {}
    for name in wanted:
        if name not in MODELS:
            print(f"[warn] 未知模型 {name}，跳过", file=sys.stderr)
            continue
        base, env_key, model_id = MODELS[name]
        key = os.getenv(env_key)
        if not key:
            print(f"[skip] {name}: 没找到 {env_key}", file=sys.stderr)
            continue
        active[name] = (OpenAI(base_url=base, api_key=key), model_id)
    return active


def ask(client: OpenAI, model_id: str, question: str) -> str:
    resp = client.chat.completions.create(
        model=model_id,
        temperature=0,
        messages=[{"role": "user", "content": question}],
    )
    return (resp.choices[0].message.content or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="questions.csv")
    ap.add_argument("--out", default="experiments/results.csv")
    ap.add_argument("--models", default="", help="逗号分隔；默认全部有 key 的")
    args = ap.parse_args()

    load_dotenv()
    wanted = [m.strip() for m in args.models.split(",") if m.strip()] or list(MODELS)
    active = build_clients(wanted)
    if not active:
        print("没有可用的模型，检查 .env", file=sys.stderr)
        return 1

    questions = load_questions(Path(args.questions))
    if not questions:
        print(f"{args.questions} 里没有题目", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists()

    with out.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()

        for q in questions:
            for name, (client, model_id) in active.items():
                t0 = time.time()
                try:
                    ans = ask(client, model_id, q["question"])
                except Exception as e:  # 免费额度会 429/超时，记下来继续
                    ans = f"[ERROR] {type(e).__name__}: {e}"
                dt = round(time.time() - t0, 2)

                w.writerow(
                    {
                        "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "qid": q.get("id", ""),
                        "model": name,
                        "question": q["question"],
                        "answer": ans.replace("\n", " ")[:2000],
                        "latency_s": dt,
                        "label": "",  # 人工填: correct / wrong / refuse
                        "note": "",
                    }
                )
                f.flush()
                print(f"{q.get('id', '?'):>6} {name:<11} {dt:>6.1f}s  {ans[:60]}")

    print(f"\n写入 {out} —— 记得打开填 label 列")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
