"""
白酒三件套 A 股取数（原生 requests 直连东方财富）
================================================
说明：
  - 本 WorkBuddy 沙箱中，AkShare 的 requests 调用因缺少浏览器头被东方财富中断；
    故这里用等价的原生 requests 直连 eastmoney（数据完全一致，且更可控）。
  - 在你自己机器上，可直接改用已装好的 AkShare（见文件末尾 fetch_hist_akshare 备选函数）。
  - 这一步也正是 B 阶段「自己掌控数据层、替换美股 API」的预演。

运行：
    python scripts/fetch_baijiu.py
输出：
    data/ 目录下生成 CSV，控制台打印摘要
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://quote.eastmoney.com/",
}

# 标的：(代码, 市场)  市场 sh=沪 / sz=深
STOCKS = {
    "贵州茅台": ("600519", "sh"),
    "五粮液": ("000858", "sz"),
    "泸州老窖": ("000568", "sz"),
}

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(OUT_DIR, exist_ok=True)


def secid(market: str, code: str) -> str:
    """东方财富 secid：沪市 1.代码，深市 0.代码"""
    return ("1." if market == "sh" else "0.") + code


def fetch_hist(code: str, market: str, name: str) -> pd.DataFrame:
    """近一年日线（前复权），来自 push2his kline 接口"""
    end = datetime.today().strftime("%Y%m%d")
    beg = (datetime.today() - timedelta(days=365)).strftime("%Y%m%d")
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",   # 101=日线
        "fqt": "1",     # 1=前复权
        "secid": secid(market, code),
        "beg": beg,
        "end": end,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    klines = r.json()["data"]["klines"]
    cols = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额",
            "振幅", "涨跌幅", "涨跌额", "换手率"]
    df = pd.DataFrame([k.split(",") for k in klines], columns=cols)
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_csv(os.path.join(OUT_DIR, f"{name}_{code}_hist_1y.csv"),
              index=False, encoding="utf-8-sig")
    return df


def fetch_spot(hists: dict) -> pd.DataFrame:
    """快照：取每只股票最近一个交易日的收盘价/涨跌幅/成交额

    说明：东方财富 push2 stock/get 实时接口的价格字段返回的是「实际值×100」
    的整数编码，易踩坑；而 kline 历史接口的数值已是正确小数。
    为数据准确，这里直接从已拉取的历史数据取最新一行（收盘后等价实时）。
    """
    rows = []
    for name, (code, _market) in STOCKS.items():
        last = hists[name].iloc[-1]
        rows.append({
            "代码": code,
            "名称": name,
            "最新价": last["收盘"],
            "涨跌幅%": last["涨跌幅"],
            "成交额": last["成交额"],
        })
    spot_df = pd.DataFrame(rows)
    spot_df.to_csv(os.path.join(OUT_DIR, "baijiu_spot.csv"),
                   index=False, encoding="utf-8-sig")
    return spot_df


def fetch_fund_flow(code: str, market: str, name: str) -> pd.DataFrame:
    """近 30 日个股资金流（主力/超大单/大单/中单/小单净流入）

    注：东方财富 fflow 接口返回列数随 fields2 变化（13 或 15 列），
    故采用动态列名，已知语义列再重命名，避免硬编码长度不匹配。
    """
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        "lmt": "30",
        "klt": "101",
        "secid": secid(market, code),
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = r.json().get("data")
    if not data:
        return pd.DataFrame()
    rows = [k.split(",") for k in data["klines"]]
    n = len(rows[0]) if rows else 0
    df = pd.DataFrame(rows, columns=[f"col{i}" for i in range(n)])
    rename = {
        "col0": "日期", "col1": "主力净流入净额", "col2": "主力净流入净占比",
        "col3": "超大单净流入净额", "col4": "超大单净流入净占比",
        "col5": "大单净流入净额", "col6": "大单净流入净占比",
        "col7": "中单净流入净额", "col8": "中单净流入净占比",
        "col9": "小单净流入净额", "col10": "小单净流入净占比",
        "col11": "收盘价", "col12": "涨跌幅",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for c in df.columns:
        if c != "日期":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.to_csv(os.path.join(OUT_DIR, f"{name}_{code}_fundflow_30d.csv"),
              index=False, encoding="utf-8-sig")
    return df


def main():
    print("=== A 股取数验证（原生 requests 直连东方财富）===")
    hists = {}
    for name, (code, market) in STOCKS.items():
        print(f"\n--- {name} ({code}) ---")
        hist = fetch_hist(code, market, name)
        hists[name] = hist
        print(f"  历史行情: {len(hist)} 行 | 最新收盘 {hist['收盘'].iloc[-1]} ({hist['日期'].iloc[-1]})")
        ff = fetch_fund_flow(code, market, name)
        print(f"  资金流  : {len(ff)} 行")

    spot = fetch_spot(hists)
    print("\n=== 最近交易日快照（白酒三件套）===")
    print(spot.to_string(index=False))
    print(f"\n数据已保存到: {OUT_DIR}")


# ---------------------------------------------------------------------------
# 本机备选：用 AkShare（沙箱因 requests 栈问题失败，你本机网络无此限制）
# ---------------------------------------------------------------------------
def fetch_hist_akshare(code: str, name: str) -> pd.DataFrame:
    import akshare as ak
    end = datetime.today()
    beg = end - timedelta(days=365)
    df = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=beg.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        adjust="qfq",
    )
    df.to_csv(os.path.join(OUT_DIR, f"{name}_{code}_hist_1y_akshare.csv"),
              index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    main()
