"""
A 股数据访问层（InsightCN）

仅服务 A 股（6 位代码，如 600519 / 000858）。所有取数经 ``src.data.a_share``
对接东方财富公开接口，返回与 ``src.data.models`` 一致的 Pydantic 对象，
供 19 个分析智能体直接使用。

已实装：
  - get_prices / get_price_data  : 日线行情（前复权）
  - get_financial_metrics        : 估值指标（PE/PB/PS/PCF/PEG/总市值）
  - get_market_cap               : 总市值
  - search_line_items            : 三大财务报表明细（占位，待接入）
  - get_insider_trades           : 股东/高管增减持（占位，待接入）
  - get_company_news             : 个股新闻（占位，待接入）
"""

import logging

import pandas as pd

from src.data.cache import get_cache
from src.data.models import (
    CompanyNews,
    CompanyNewsResponse,
    FinancialMetrics,
    FinancialMetricsResponse,
    Price,
    PriceResponse,
    LineItem,
    LineItemResponse,
    InsiderTrade,
    InsiderTradeResponse,
)

from src.data import a_share as _ashare

logger = logging.getLogger(__name__)

# Global cache instance
_cache = get_cache()


def _is_supported(ticker: str) -> bool:
    """仅接受 A 股代码，拒绝其它市场标的。"""
    if not _ashare.is_a_share(ticker):
        logger.warning("InsightCN 仅支持 A 股(6 位代码)，已忽略: %s", ticker)
        return False
    return True


def get_prices(ticker: str, start_date: str, end_date: str) -> list[Price]:
    """A 股日线行情（含内存缓存）。"""
    if not _is_supported(ticker):
        return []
    cache_key = f"{ticker}_{start_date}_{end_date}"
    if cached := _cache.get_prices(cache_key):
        return [Price(**price) for price in cached]

    prices = _ashare.get_prices(ticker, start_date, end_date)
    if prices:
        _cache.set_prices(cache_key, [p.model_dump() for p in prices])
    return prices


def get_financial_metrics(
    ticker: str,
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
) -> list[FinancialMetrics]:
    """A 股估值指标（含内存缓存）。"""
    if not _is_supported(ticker):
        return []
    cache_key = f"{ticker}_{period}_{end_date}_{limit}"
    if cached := _cache.get_financial_metrics(cache_key):
        return [FinancialMetrics(**metric) for metric in cached]

    metrics = _ashare.get_financial_metrics(ticker, end_date, period=period, limit=limit)
    if metrics:
        _cache.set_financial_metrics(cache_key, [m.model_dump() for m in metrics])
    return metrics


def search_line_items(
    ticker: str,
    line_items: list[str],
    end_date: str,
    period: str = "ttm",
    limit: int = 10,
) -> list[LineItem]:
    """A 股财务报表明细（占位，待接入）。"""
    if not _is_supported(ticker):
        return []
    return _ashare.search_line_items(ticker, line_items, end_date, period=period, limit=limit)


def get_insider_trades(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
) -> list[InsiderTrade]:
    """A 股股东/高管增减持（占位，待接入）。"""
    if not _is_supported(ticker):
        return []
    return _ashare.get_insider_trades(ticker, end_date, start_date=start_date, limit=limit)


def get_company_news(
    ticker: str,
    end_date: str,
    start_date: str | None = None,
    limit: int = 1000,
) -> list[CompanyNews]:
    """A 股个股新闻（占位，待接入）。"""
    if not _is_supported(ticker):
        return []
    return _ashare.get_company_news(ticker, end_date, start_date=start_date, limit=limit)


def get_market_cap(
    ticker: str,
    end_date: str,
) -> float | None:
    """A 股总市值。"""
    if not _is_supported(ticker):
        return None
    return _ashare.get_market_cap(ticker, end_date)


def prices_to_df(prices: list[Price]) -> pd.DataFrame:
    """Convert prices to a DataFrame."""
    df = pd.DataFrame([p.model_dump() for p in prices])
    df["Date"] = pd.to_datetime(df["time"])
    df.set_index("Date", inplace=True)
    numeric_cols = ["open", "close", "high", "low", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.sort_index(inplace=True)
    return df


def get_price_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    prices = get_prices(ticker, start_date, end_date)
    return prices_to_df(prices)
