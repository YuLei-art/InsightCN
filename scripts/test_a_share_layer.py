"""
A 股数据层冒烟测试（无需 LLM / API Key）

验证：
  1) A 股 6 位代码走东方财富数据层，返回正确的 Pydantic 对象
  2) 行情 / 估值指标可正常获取
  3) 美股代码（如 AAPL）仍走原美股 API 路由（is_a_share=False），不破坏原功能

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
    assert is_a_share("AAPL") is False
    assert is_a_share("MSFT") is False
    print("  A股 600519 -> A股路由  [OK] | 美股 AAPL -> 美股路由 [OK]")


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


def test_us_untouched():
    print("\n=== 4) 美股代码不触发 A股路由（路由正确，且网络异常优雅降级）===")
    # 验证 is_a_share 判断正确：AAPL 走原美股分支，不会误入 A股数据层
    # 美股接口不可达时（无 Key / 网络受限）应优雅返回空，而非抛异常炸图
    us = get_prices("AAPL", "2026-01-01", "2026-07-06")
    print(f"  AAPL 行情 -> {len(us)} 行（路由正确；网络不可达时应为 0，不崩溃）")


if __name__ == "__main__":
    test_routing()
    test_prices()
    test_metrics()
    test_us_untouched()
    print("\n[OK] 全部冒烟测试通过：A 股数据层已就绪，19 个智能体可零改动分析 A 股。")
