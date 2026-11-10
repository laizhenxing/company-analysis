# 计算器输入契约

## 目录

1. 使用规则
2. 字段说明
3. 完整示例
4. 输出解释

## 1. 使用规则

`research_calculator.py` 只使用 Python 标准库。先把专业数据源或公告中的数据规范化，再运行计算；脚本不核验来源真实性。

所有金额使用同一币种和单位。若利润使用“亿元”、股本使用“亿股”、价格使用“元／股”，则市值自动得到“亿元”。回报率和概率在输入中使用小数，例如 10% 写 `0.10`，25% 写 `0.25`。

先运行 `validate`，再运行 `calculate`。错误必须修复；警告需要逐项解释。缺失的可选分析会被跳过，不会用零填补。

## 2. 字段说明

- `annuals`：至少两个完整年度，`year` 用于计算实际年数；`revenue`、`net_profit_parent` 必填。
- `latest`：最新累计期，可选；不得与年度混算同比。
- `market`：`price`、`shares` 必填，`market_cap` 可选；缺省时用价格乘股本。
- `history`：历史静态 PE 输入，使用当时价格、当时股本和对应年度归母净利。
- `peers`：同业市值和各年预测净利；统一估值日和预测来源。
- `reverse`：反向估值；`base_profit` 可从一致预期填入，`required_return` 和 `exit_pes` 必填。
- `scenarios`：情景估值；概率合计必须为 1，`discount_years` 可不同于目标年减当前年，但须在报告解释。

## 3. 完整示例

以下纯属虚构样例，仅用于测试，不是任何真实公司的数据：

```json
{
  "company": "示例公司",
  "ticker": "000000.SZ",
  "as_of": "2026-12-31",
  "currency": "CNY",
  "unit": "亿元",
  "annuals": [
    {"year": 2023, "period": "2023", "revenue": 100, "cogs": 75, "net_profit_parent": 10, "operating_cash_flow": 8, "capex": 12, "cash": 20, "short_term_debt": 5, "debt_due_within_1y": 2, "long_term_debt": 8},
    {"year": 2024, "period": "2024", "revenue": 120, "cogs": 88, "net_profit_parent": 13, "operating_cash_flow": 15, "capex": 10, "cash": 30, "short_term_debt": 4, "debt_due_within_1y": 1, "long_term_debt": 6},
    {"year": 2025, "period": "2025", "revenue": 150, "cogs": 108, "net_profit_parent": 18, "operating_cash_flow": 22, "capex": 11, "cash": 40, "short_term_debt": 3, "debt_due_within_1y": 1, "long_term_debt": 5}
  ],
  "latest": {"period": "2026Q1-Q3", "revenue": 125, "net_profit_parent": 15, "operating_cash_flow": 18, "capex": 8},
  "market": {
    "price": 20,
    "shares": 10,
    "current_year": 2026,
    "consensus_profit": {"2026": 20, "2027": 24, "2028": 29}
  },
  "history": [
    {"label": "2024年末", "price": 12, "shares": 10, "net_profit_parent": 13},
    {"label": "2025年末", "price": 18, "shares": 10, "net_profit_parent": 18}
  ],
  "peers": [
    {"name": "可比甲", "market_cap": 180, "forecast_profit": {"2026": 18, "2027": 22}},
    {"name": "可比乙", "market_cap": 300, "forecast_profit": {"2026": 20, "2027": 25}}
  ],
  "reverse": {
    "base_year": 2026,
    "target_year": 2030,
    "base_profit": 20,
    "required_return": 0.10,
    "exit_pes": [20, 25, 30]
  },
  "scenarios": {
    "target_year": 2028,
    "discount_years": 2,
    "discount_rate": 0.10,
    "cases": [
      {"name": "悲观", "net_profit": 24, "exit_pe": 15, "probability": 0.25},
      {"name": "基准", "net_profit": 29, "exit_pe": 20, "probability": 0.50},
      {"name": "乐观", "net_profit": 36, "exit_pe": 25, "probability": 0.25}
    ]
  }
}
```

## 4. 输出解释

输出包括年度指标、首末年度 CAGR、历史 PE、同业 forward PE、反向所需利润和 CAGR、情景价格／现值／加权现值，以及质检警告。

所有计算结果在报告中标为 `model_result`。一致预期仍是预测输入，情景净利润、退出 PE 和概率仍是 `scenario_input`；计算不会提升它们的证据等级。
