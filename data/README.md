# 数据说明

## statements.csv

一行 = 一家公司一个报告期。**金额单位统一为 LAK（老挝基普，整数元）。**

| 字段 | 含义 | 备注 |
|---|---|---|
| firm_id | 内部编号 | 不要用真实公司名做 ID |
| name | 显示名 | 模拟数据用「示例XX」 |
| period | 报告期 | 如 2025，指该财年 |
| report_date | 披露日 | **与报告期不同**，见 questions/PROTOCOL.md |
| currency | 币种 | 统一 LAK |
| total_assets | 总资产 | |
| total_liabilities | 总负债 | |
| equity | 所有者权益 | 空值 = 缺失，不要填 0 |
| current_assets | 流动资产 | |
| current_liabilities | 流动负债 | 0 会导致比率无法计算，属正常 |
| revenue | 营业收入 | |
| net_income | 净利润 | |
| operating_cash_flow | 经营活动现金流 | 可为负 |

## 规则

1. **空值就是空值**，不要用 0 代替。缺失本身是"报告质量"要测的东西。
2. 恒等式容差 0.5%（`report_checks.py` 里的 `TOLERANCE`），超过才算错。
3. 「提示」不是错误。权益为负、流动比率<1 都可能正常经营，只标记不判定。
4. 每新增一批数据，必须记录来源和披露日，否则不可比。

## 当前状态

`statements.csv` 里 6 行全部是**模拟数据**，用于测试规则引擎。

真实数据已下载 10 份 BCEL 财报，放在 `data/raw/bcel/`（不进版本库，体积大）：

```bash
python scan_reports.py --dir data/raw/bcel --out data/reports_meta.csv
```

扫描结果见 `data/reports_meta.csv`：10 份里 5 份有文字层，
但即使有文字层，三张报表所在页面仍是纯图片。

## 目录

```
data/
├── statements.csv        规则引擎的输入（人工录入的结构化数据）
├── reports_meta.csv      扫描结果：每份 PDF 的页数 / 有字页 / 纯图片页
└── raw/bcel/             原始 PDF（gitignore，不入库）
```

