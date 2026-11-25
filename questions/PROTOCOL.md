# 出题规则

## 铁律

> **`expected` 必须能指向一份我们实际打开过的文件。**
> 不能指向任何人的记忆——包括模型、包括我、包括老师。

违反这条的题，一律不进题库。

## 为什么

2026-11-25 的教训：Q001 假设"2024 年 3 月没有大规模收购"，据此把模型判为"在错误前提下编造"。
一条搜索就推翻了：[EQT 与 Equitrans Midstream 合并，350 亿美元，2024 年 3 月 11 日宣布](https://es.marketscreener.com/noticias/ultimas/EQT-y-Equitrans-Midstream-se-fusionar-n-para-crear-una-firma-de-35-000-millones-de-d-lares-46139146/)。

错的不是模型，是题。**前提和答案都要核实。**

## 字段

| 字段 | 含义 | 谁给 |
|---|---|---|
| `id` | 唯一编号，一经分配永不复用 | — |
| `question` | 题面 | — |
| `category` | `filing_date` / `past_event` / `false_premise` / `fabricated` / `future_event` | — |
| `expected` | 标准答案 | 必须来自 evidence_url |
| `evidence_url` | 权威来源链接 | 手动核实或程序生成 |
| `evidence_note` | 来源里的关键字段（如 reportDate） | 同上 |
| `verified_on` | 核实日期 | 同上 |

## 两族出题方式

### 第一族：程序生成（多数）

答案直接来自权威元数据，**不可能错**。

```bash
python gen_filings.py --out questions/v2_filings.csv
```

数据源：SEC EDGAR `submissions` API。
关键字段：`reportDate`（报告期结束日）、`filingDate`（实际提交日）——正是本项目「报告期 vs 披露日」的核心。

### 第二族：人工核实（少数）

用于测"记忆"和"错误前提"这类元数据给不出的行为。每道题验收四项：

- [ ] 事件确实发生过（不是前提假设）
- [ ] 时间精确到日，且与来源一致
- [ ] 金额/主体/口径与来源一致
- [ ] `evidence_url` 能打开，且是**一手来源**（公司公告、SEC 文件、路透）

一手来源优先级：SEC 文件 > 公司新闻稿 > 路透/彭博 > 其他媒体。
**不要用"我记得"。**

## 缺陷处理

已冻结的题库**不修改**。发现缺陷时：

1. 写进 `v1_ERRATA.md`，说明哪道题、错在哪、怎么处理
2. 分析时显式排除该题
3. 修正后的版本进下一个版本号

冻结不等于不认错——**冻结的是文件，不是判断。**

## 维护

- 链接会腐坏。每年重跑一次 evidence 检查，标记 404 的题。
- 公司会改名、会退市、会被收购。题面写"当时的名称"。
- 新增题目开新文件，不进老文件。
