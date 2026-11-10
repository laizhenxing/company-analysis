#!/usr/bin/env python3
"""Deterministic calculations for the six-dimension company research workflow.

This script does not fetch data or make investment recommendations. All monetary
values must use one currency and unit. Rates and probabilities are decimals.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path


def is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rounded(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    if isinstance(value, float):
        return round(value, 6)
    return value


def ratio(numerator, denominator):
    if not is_num(numerator) or not is_num(denominator) or denominator == 0:
        return None
    return numerator / denominator


def cagr(start, end, years):
    if not all(is_num(v) for v in (start, end, years)) or start <= 0 or end < 0 or years <= 0:
        return None
    if end == 0:
        return -1.0
    return (end / start) ** (1 / years) - 1


def require_number(obj, key, path, errors, positive=False, nonnegative=False):
    value = obj.get(key)
    if not is_num(value):
        errors.append(f"{path}.{key} 必须是有限数值")
        return
    if positive and value <= 0:
        errors.append(f"{path}.{key} 必须大于 0")
    if nonnegative and value < 0:
        errors.append(f"{path}.{key} 不得小于 0")


def validate(data):
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["输入根节点必须是 JSON 对象"], warnings
    for key in ("company", "as_of", "currency", "unit"):
        if not isinstance(data.get(key), str) or not data.get(key).strip():
            errors.append(f"缺少字符串字段 {key}")
    if data.get("as_of") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["as_of"]):
        errors.append("as_of 必须使用 YYYY-MM-DD")

    annuals = data.get("annuals")
    if not isinstance(annuals, list) or len(annuals) < 2:
        errors.append("annuals 至少需要两个完整年度")
        annuals = []
    years = []
    for i, row in enumerate(annuals):
        path = f"annuals[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{path} 必须是对象")
            continue
        if not isinstance(row.get("year"), int):
            errors.append(f"{path}.year 必须是四位整数年份")
        else:
            years.append(row["year"])
        require_number(row, "revenue", path, errors, positive=True)
        require_number(row, "net_profit_parent", path, errors)
        for key in ("cogs", "operating_cash_flow", "capex", "cash", "short_term_debt", "debt_due_within_1y", "long_term_debt"):
            if key in row and not is_num(row[key]):
                errors.append(f"{path}.{key} 必须是有限数值")
    if len(years) != len(set(years)):
        errors.append("annuals.year 不得重复")
    if years and years != sorted(years):
        warnings.append("annuals 未按年份升序，计算时将自动排序")

    latest = data.get("latest")
    if latest is not None:
        if not isinstance(latest, dict):
            errors.append("latest 必须是对象")
        else:
            if not latest.get("period"):
                errors.append("latest.period 不得为空")
            require_number(latest, "revenue", "latest", errors, positive=True)
            require_number(latest, "net_profit_parent", "latest", errors)
            warnings.append("latest 为累计期时，只与上年同累计期比较，不与完整年度直接同比")

    market = data.get("market")
    if not isinstance(market, dict):
        errors.append("market 必须是对象")
        market = {}
    require_number(market, "price", "market", errors, positive=True)
    require_number(market, "shares", "market", errors, positive=True)
    if "market_cap" in market:
        require_number(market, "market_cap", "market", errors, positive=True)
    forecasts = market.get("consensus_profit", {})
    if not isinstance(forecasts, dict):
        errors.append("market.consensus_profit 必须是对象")
        forecasts = {}
    for year, value in forecasts.items():
        if not re.fullmatch(r"\d{4}", str(year)) or not is_num(value):
            errors.append(f"market.consensus_profit[{year}] 年份或数值无效")

    for i, row in enumerate(data.get("history", [])):
        path = f"history[{i}]"
        for key in ("price", "shares"):
            require_number(row, key, path, errors, positive=True)
        require_number(row, "net_profit_parent", path, errors)
    for i, row in enumerate(data.get("peers", [])):
        path = f"peers[{i}]"
        if not row.get("name"):
            errors.append(f"{path}.name 不得为空")
        require_number(row, "market_cap", path, errors, positive=True)
        for year, value in row.get("forecast_profit", {}).items():
            if not re.fullmatch(r"\d{4}", str(year)) or not is_num(value):
                errors.append(f"{path}.forecast_profit[{year}] 年份或数值无效")

    reverse = data.get("reverse")
    if reverse is not None:
        for key in ("base_profit",):
            require_number(reverse, key, "reverse", errors, positive=True)
        require_number(reverse, "required_return", "reverse", errors, nonnegative=True)
        for key in ("base_year", "target_year"):
            if not isinstance(reverse.get(key), int):
                errors.append(f"reverse.{key} 必须是整数年份")
        if isinstance(reverse.get("base_year"), int) and isinstance(reverse.get("target_year"), int):
            if reverse["target_year"] <= reverse["base_year"]:
                errors.append("reverse.target_year 必须晚于 base_year")
        if not isinstance(reverse.get("exit_pes"), list) or not reverse["exit_pes"]:
            errors.append("reverse.exit_pes 至少需要一个退出 PE")
        else:
            for pe in reverse["exit_pes"]:
                if not is_num(pe) or pe <= 0:
                    errors.append("reverse.exit_pes 必须全部大于 0")

    scenarios = data.get("scenarios")
    if scenarios is not None:
        require_number(scenarios, "discount_rate", "scenarios", errors, nonnegative=True)
        require_number(scenarios, "discount_years", "scenarios", errors, positive=True)
        cases = scenarios.get("cases")
        if not isinstance(cases, list) or len(cases) < 2:
            errors.append("scenarios.cases 至少需要两个情景")
            cases = []
        probability_sum = 0
        for i, case in enumerate(cases):
            path = f"scenarios.cases[{i}]"
            require_number(case, "net_profit", path, errors, nonnegative=True)
            require_number(case, "exit_pe", path, errors, positive=True)
            require_number(case, "probability", path, errors, nonnegative=True)
            if is_num(case.get("probability")):
                probability_sum += case["probability"]
        if cases and abs(probability_sum - 1) > 1e-9:
            errors.append(f"情景概率合计必须为 1，当前为 {probability_sum:.8f}")
    return errors, warnings


def period_metrics(row):
    result = dict(row)
    result["gross_margin"] = ratio(row.get("revenue", 0) - row.get("cogs", 0), row.get("revenue")) if "cogs" in row else None
    result["net_margin_parent"] = ratio(row.get("net_profit_parent"), row.get("revenue"))
    result["ocf_to_net_profit"] = ratio(row.get("operating_cash_flow"), row.get("net_profit_parent"))
    if "operating_cash_flow" in row and "capex" in row:
        result["simple_fcf"] = row["operating_cash_flow"] - row["capex"]
    else:
        result["simple_fcf"] = None
    if "cash" in row:
        debts = sum(row.get(k, 0) for k in ("short_term_debt", "debt_due_within_1y", "long_term_debt"))
        result["simple_net_cash"] = row["cash"] - debts
    else:
        result["simple_net_cash"] = None
    return result


def calculate(data):
    annuals = sorted(data["annuals"], key=lambda row: row["year"])
    annual_metrics = [period_metrics(row) for row in annuals]
    first, last = annuals[0], annuals[-1]
    years = last["year"] - first["year"]
    market = data["market"]
    shares = market["shares"]
    market_cap = market.get("market_cap", market["price"] * shares)

    result = {
        "meta": {
            "company": data["company"], "ticker": data.get("ticker"), "as_of": data["as_of"],
            "currency": data["currency"], "unit": data["unit"],
            "evidence": "model_result",
            "note": "仅复算输入数据，不验证来源，不构成投资建议。"
        },
        "annual_metrics": annual_metrics,
        "latest_metrics": period_metrics(data["latest"]) if data.get("latest") else None,
        "cagr": {
            "from_year": first["year"], "to_year": last["year"], "years": years,
            "revenue": cagr(first["revenue"], last["revenue"], years),
            "net_profit_parent": cagr(first["net_profit_parent"], last["net_profit_parent"], years)
        },
        "market": {
            "market_cap": market_cap,
            "forward_pe": {year: ratio(market_cap, profit) for year, profit in market.get("consensus_profit", {}).items()}
        },
        "history_pe": [
            {**row, "simple_pe": ratio(row["price"] * row["shares"], row["net_profit_parent"])}
            for row in data.get("history", [])
        ],
        "peer_forward_pe": [
            {"name": row["name"], "pe": {year: ratio(row["market_cap"], profit) for year, profit in row.get("forecast_profit", {}).items()}}
            for row in data.get("peers", [])
        ]
    }

    reverse = data.get("reverse")
    if reverse:
        n = reverse["target_year"] - reverse["base_year"]
        required_cap = market_cap * (1 + reverse["required_return"]) ** n
        result["reverse_valuation"] = {
            "base_year": reverse["base_year"], "target_year": reverse["target_year"],
            "required_return": reverse["required_return"], "required_future_market_cap": required_cap,
            "cases": [
                {"exit_pe": pe, "required_net_profit": required_cap / pe,
                 "implied_profit_cagr": cagr(reverse["base_profit"], required_cap / pe, n)}
                for pe in reverse["exit_pes"]
            ]
        }

    scenarios = data.get("scenarios")
    if scenarios:
        scenario_shares = scenarios.get("shares", shares)
        divisor = (1 + scenarios["discount_rate"]) ** scenarios["discount_years"]
        cases = []
        for case in scenarios["cases"]:
            future_price = case["net_profit"] * case["exit_pe"] / scenario_shares
            present_value = future_price / divisor
            cases.append({**case, "future_price": future_price, "present_value": present_value,
                          "weighted_present_value": present_value * case["probability"]})
        result["scenario_valuation"] = {
            "target_year": scenarios.get("target_year"), "shares": scenario_shares,
            "discount_rate": scenarios["discount_rate"], "discount_years": scenarios["discount_years"],
            "cases": cases, "weighted_present_value": sum(c["weighted_present_value"] for c in cases)
        }
        weighted = result["scenario_valuation"]["weighted_present_value"]
        result["scenario_valuation"]["premium_to_observed_price"] = weighted / market["price"] - 1

    warnings = []
    for row in annual_metrics:
        cash_conversion = row.get("ocf_to_net_profit")
        if cash_conversion is not None and row.get("net_profit_parent", 0) > 0 and cash_conversion < 0.8:
            warnings.append(f"{row.get('period', row['year'])} OCF／归母净利低于 0.8，检查营运资本和利润质量")
        if row.get("simple_fcf") is not None and row["simple_fcf"] < 0:
            warnings.append(f"{row.get('period', row['year'])} 简化 FCF 为负，检查扩张资本开支和现金回收")
    result["qc_warnings"] = warnings
    return rounded(result)


def main():
    parser = argparse.ArgumentParser(description="六维公司研究确定性计算器")
    parser.add_argument("command", choices=("validate", "calculate"))
    parser.add_argument("input", type=Path, help="输入 JSON 文件")
    parser.add_argument("--output", type=Path, help="输出 JSON 文件；缺省打印到标准输出")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取输入：{exc}", file=sys.stderr)
        return 2
    errors, warnings = validate(data)
    if errors:
        print("校验失败：", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    if args.command == "validate":
        output = {"status": "valid", "warnings": warnings,
                  "message": "输入可计算；仍须人工核对来源、报告期和口径。"}
    else:
        output = calculate(data)
        output["input_warnings"] = warnings
    text = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"已写入 {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
