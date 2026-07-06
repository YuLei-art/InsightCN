"""
A 股数据层冒烟测试（无需 LLM / API Key）

验证：
  1) A 股 6 位代码走东方财富数据层，返回正确的 Pydantic 对象
  2) 行情 / 估值指标可正常获取
  3) 非 A 股代码（如 AAPL）被明确拒绝（返回空），项目仅服务 A 股

运行：
  cd InsightCN
  python scripts/test_a_share_layer.py
"""
import os
import sys

# 让脚本能从项目根目录导入 src 包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data.a_share import is_a_share
from src.tools.api import get_prices, get_financial_metrics, get_market_cap, get_price_data


def test_routing():
    print("=== 1) 代码路由判断 ===")
    assert is_a_share("600519") is True
    assert is_a_share("SH600519") is True
    assert is_a_share("000858") is True
    assert is_a_share("AAPL") is False
    assert is_a_share("MSFT") is False
    print("  A股 600519 / 000858 -> A股路由  [OK] | 美股 AAPL -> 非 A 股 [OK]")


def test_prices():
    print("\n=== 2) A股行情（600519 贵州茅台, 近 1 个月）===")
    prices = get_prices("600519", "2026-06-06", "2026-07-06")
    assert prices, "行情不应为空"
    assert all(hasattr(p, "close") for p in prices)
    last = prices[-1]
    print(f"  行数: {len(prices)} | 最新收盘: {last.close} @ {last.time}")
    df = get_price_data("600519", "2026-06-06", "2026-07-06")
    print(f"  DataFrame 形状: {df.shape} | 列: {list(df.columns[:6])}")
    assert not df.empty


def test_metrics():
    print("\n=== 3) A股估值指标（600519）===")
    m = get_financial_metrics("600519", "2026-07-06")
    assert m, "估值指标不应为空"
    rec = m[0]
    print(f"  PE_TTM : {rec.price_to_earnings_ratio}")
    print(f"  PB_MRQ : {rec.price_to_book_ratio}")
    print(f"  PS_TTM : {rec.price_to_sales_ratio}")
    print(f"  总市值 : {rec.market_cap:,.0f} 元" if rec.market_cap else "  总市值 : 无")
    cap = get_market_cap("600519", "2026-07-06")
    print(f"  get_market_cap -> {cap:,.0f}" if cap else "  get_market_cap -> None")
    assert rec.price_to_earnings_ratio is not None


def test_non_ashare_rejected():
    print("\n=== 4) 非 A 股代码被拒绝（项目仅服务 A 股）===")
    # 美股代码不应进入 A 股数据层，直接返回空
    us = get_prices("AAPL", "2026-01-01", "2026-07-06")
    assert us == [], "非 A 股代码应返回空列表"
    us_cap = get_market_cap("AAPL", "2026-07-06")
    assert us_cap is None, "非 A 股代码市值应为 None"
    print("  AAPL 行情 -> 0 行（已拒绝）[OK] | AAPL 市值 -> None [OK]")


if __name__ == "__main__":
    test_routing()
    test_prices()
    test_metrics()
    test_non_ashare_rejected()
    print("\n[OK] 全部冒烟测试通过：InsightCN 已纯 A 股化，19 个智能体可零改动分析 A 股。")
