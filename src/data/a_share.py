"""
A 股数据层（InsightCN 派生自 ai-hedge-fund）

用东方财富公开接口替换原项目的美股 FINANCIAL_DATASETS_API，
返回与 ``src.data.models`` 完全一致的 Pydantic 对象，
从而让 19 个分析智能体“零改动”即可分析 A 股。

已实装：
  - get_prices / get_price_data  : 日线行情（前复权），push2his kline
  - get_financial_metrics        : 估值指标（PE/PB/PS/PCF/PEG/总市值），价值分析接口
  - get_market_cap               : 总市值

暂为占位（接口保留，返回空并打日志，待接入）：
  - search_line_items           : 三大财务报表明细
  - get_insider_trades          : 高管/股东增减持
  - get_company_news            : 个股新闻

> 说明：A 股代码识别为 6 位数字（如 600519）。带市场前缀 SH600519 也已兼容。
"""

import logging
import re

import requests

from src.data.models import (
    CompanyNews,
    FinancialMetrics,
    InsiderTrade,
    LineItem,
    Price,
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

# A 股 6 位代码，或 SH/SZ 前缀
_A_SHARE_RE = re.compile(r"^(SH|SZ|sh|sz)?(\d{6})$", re.IGNORECASE)


def is_a_share(ticker: str) -> bool:
    """判断是否为 A 股标的（6 位数字代码）。"""
    return bool(_A_SHARE_RE.match((ticker or "").strip()))


def _normalize_code(ticker: str) -> str:
    """提取纯 6 位代码。"""
    m = _A_SHARE_RE.match((ticker or "").strip())
    return m.group(2) if m else ticker


def _secid(code: str) -> str:
    """东方财富 secid：市场前缀.代码（1=沪市，0=深市）。"""
    prefix = "1" if code[0] == "6" else "0"
    return f"{prefix}.{code}"


def _get_json(url: str, params: dict, timeout: int = 15) -> dict | None:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        return r.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("A股请求失败 %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# 行情
# ---------------------------------------------------------------------------
def get_prices(
    ticker: str, start_date: str, end_date: str, api_key: str = None
) -> list[Price]:
    code = _normalize_code(ticker)
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": "101",   # 日线
        "fqt": "1",     # 前复权
        "secid": _secid(code),
        "beg": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
    }
    data = _get_json(url, params)
    if not data or not (klines := (data.get("data") or {}).get("klines")):
        return []
    rows: list[Price] = []
    for k in klines:
        p = k.split(",")
        if len(p) < 7:
            continue
        rows.append(
            Price(
                time=p[0],
                open=float(p[1]),
                close=float(p[2]),
                high=float(p[3]),
                low=float(p[4]),
                volume=int(float(p[5])),
            )
        )
    return [r for r in rows if start_date <= r.time <= end_date]


def get_price_data(
    ticker: str, start_date: str, end_date: str, api_key: str = None
):
    import pandas as pd

    prices = get_prices(ticker, start_date, end_date, api_key=api_key)
    df = pd.DataFrame([p.model_dump() for p in prices])
    if df.empty:
        return df
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    for col in ["open", "close", "high", "low", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df


# ---------------------------------------------------------------------------
# 估值指标（价值分析接口）
# ---------------------------------------------------------------------------
def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[FinancialMetrics]:
    code = _normalize_code(ticker)
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_VALUEANALYSIS_DET",
        "columns": (
            "SECURITY_CODE,SECURITY_NAME_ABBR,TOTAL_MARKET_CAP,"
            "NOTLIMITED_MARKETCAP_A,CLOSE_PRICE,CHANGE_RATE,TOTAL_SHARES,"
            "PE_TTM,PB_MRQ,PS_TTM,PCF_OCF_TTM,PCF_OCF_LAR,PEG_CAR,TRADE_DATE"
        ),
        "filter": f'(SECURITY_CODE="{code}")',
        "pageSize": "1",
        "source": "WEB",
    }
    data = _get_json(url, params)
    if not (data and data.get("success")):
        return []
    rec = (data.get("result") or {}).get("data") or [{}]
    d = rec[0]
    trade_date = str(d.get("TRADE_DATE") or "")[:10]
    return [
        FinancialMetrics(
            ticker=code,
            report_period=trade_date,
            period=period,
            currency="CNY",
            market_cap=d.get("TOTAL_MARKET_CAP"),
            enterprise_value=None,
            price_to_earnings_ratio=d.get("PE_TTM"),
            price_to_book_ratio=d.get("PB_MRQ"),
            price_to_sales_ratio=d.get("PS_TTM"),
            enterprise_value_to_ebitda_ratio=None,
            enterprise_value_to_revenue_ratio=None,
            free_cash_flow_yield=None,
            peg_ratio=d.get("PEG_CAR"),
            gross_margin=None,
            operating_margin=None,
            net_margin=None,
            return_on_equity=None,
            return_on_assets=None,
            return_on_invested_capital=None,
            asset_turnover=None,
            inventory_turnover=None,
            receivables_turnover=None,
            days_sales_outstanding=None,
            operating_cycle=None,
            working_capital_turnover=None,
            current_ratio=None,
            quick_ratio=None,
            cash_ratio=None,
            operating_cash_flow_ratio=None,
            debt_to_equity=None,
            debt_to_assets=None,
            interest_coverage=None,
            revenue_growth=None,
            earnings_growth=None,
            book_value_growth=None,
            earnings_per_share_growth=None,
            free_cash_flow_growth=None,
            operating_income_growth=None,
            ebitda_growth=None,
            payout_ratio=None,
            earnings_per_share=None,
            book_value_per_share=None,
            free_cash_flow_per_share=None,
        )
    ]


def get_market_cap(ticker: str, end_date: str, api_key: str = None) -> float | None:
    metrics = get_financial_metrics(ticker, end_date, api_key=api_key)
    if not metrics:
        return None
    return metrics[0].market_cap


# ---------------------------------------------------------------------------
# 占位接口（保持契约一致，后续接入）
# ---------------------------------------------------------------------------
def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
    api_key: str = None,
) -> list[LineItem]:
    logger.info("A股财务报表明细(line_items)暂未接入，返回空。ticker=%s", ticker)
    return []


def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[InsiderTrade]:
    logger.info("A股股东增减持数据暂未接入，返回空。ticker=%s", ticker)
    return []


def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
    api_key: str = None,
) -> list[CompanyNews]:
    logger.info("A股个股新闻暂未接入，返回空。ticker=%s", ticker)
    return []
