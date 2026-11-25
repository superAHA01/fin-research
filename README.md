# fin-research

个人研究仓库 · 老挝国立大学 会计学 · 长期维护

两条线并行，互不阻塞：

| 线 | 题目 | 产出 | 周期 |
|---|---|---|---|
| **A** | 金融 LLM 的记忆泄漏 / 前视偏差评测 | 可复现的评测流程 + 公开数据集 | 18 个月 |
| **B** | 老挝语金融文本数据集（前沿市场、低披露） | 500+ 份结构化披露文件 | 24 个月 |

A 线练能力，B 线立身份。见 `BRIEF.md` 了解边界与当前阶段。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env        # 填至少一个 key，全免费、无需信用卡
python probe.py --questions questions.csv --out experiments/results.csv
```

跑完打开 `experiments/results.csv`，人工填 `label` 列：
`correct` / `wrong` / `refuse`。**这一步不能交给模型。**

## 目录

```
BRIEF.md            项目宪法，见任何 AI 前先更新并粘贴
DECISIONS.md        决策日志，只记"为什么"，不记"做了什么"
probe.py            多模型一致性探针
questions.csv       问题集（逐周扩充）
experiments/        实验结果 CSV，全部进版本库
notes/              每次会话的笔记，按日期命名
```

## 三条纪律

1. `.env` 永远不进仓库。key 泄露后几分钟内就会被扫到。
2. 每次收工提交一次，哪怕只改了一行笔记。
3. 公开但粗糙，好过私有但完美。

## 数据放哪

- 代码、笔记、实验结果 → 这个仓库
- B 线的大批量 PDF / 数据集 → HuggingFace Datasets，这里只放采集脚本和索引
