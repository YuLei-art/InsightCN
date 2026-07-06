# InsightCN —— 支持 A 股的 AI 投研多智能体

把 **ai-hedge-fund（③ 多智能体架构）** 与 **东方财富 A 股数据（① 数据底座）** 组合，
做一个**支持 A 股**的 AI 投研多智能体。本仓库基于 [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)（MIT）修改而来。

> 原项目只支持美股（FINANCIAL_DATASETS_API）。我们**零改动复用其 19 个分析智能体**，
> 仅把数据层替换为东方财富 A 股接口，A 股代码（6 位）即插即用。

## 架构
- **编排**：`src/main.py` + `src/graph/state.py` 用 LangGraph 风格把多个 agent 串成投研流水线。
- **19 个智能体**（`src/agents/`）：
  - 投资大师人格：巴菲特 / 芒格 / 林奇 / 格雷厄姆 / 阿克曼 / 伯里 / 帕布莱 / 伍德 / 达摩达兰 / 德鲁肯米勒 / 塔勒布 / 金君瓦拉 / 费雪
  - 分析模块：基本面 / 技术面 / 成长 / 情绪 / 新闻情绪 / 估值 / 风险 / 组合经理
- **数据层**（`src/tools/api.py` + `src/data/a_share.py`）：所有 agent 通过统一函数取数，
  返回与 `src/data/models.py` 一致的 Pydantic 对象 —— **换数据源，agent 一行不用改**。

## A 股数据层状态（`src/data/a_share.py`）
| 能力 | 接口函数 | 状态 | 数据源 |
|---|---|---|---|
| 日线行情 | `get_prices` / `get_price_data` | ✅ 已实装 | 东方财富 kline（前复权） |
| 估值指标 | `get_financial_metrics` | ✅ 已实装 | 东方财富价值分析（PE/PB/PS/PCF/PEG/总市值） |
| 总市值 | `get_market_cap` | ✅ 已实装 | 价值分析 |
| 财报明细 | `search_line_items` | 🚧 占位（返回空） | 待接入三大报表 |
| 股东增减持 | `get_insider_trades` | 🚧 占位（返回空） | 待接入 |
| 个股新闻 | `get_company_news` | 🚧 占位（返回空） | 待接入 |

**路由机制**：`api.py` 检测代码 —— 6 位数字（如 `600519`，兼容 `SH600519`）走东方财富；
其余（如 `AAPL`）仍走原美股 API，原功能零回归。

## 快速开始

### 0. 环境
- Python 3.10+（本机用 WorkBuddy managed 3.13 venv：`~/.workbuddy/binaries/python/envs/a-share-research`）
- 依赖安装：
```bash
python -m pip install -r requirements.txt
```

### 1. 数据层冒烟测试（无需 API Key，验证 A 股取数）
```bash
python scripts/test_a_share_layer.py
```
预期输出：茅台近 1 月行情（20 行）、PE_TTM≈18.24 / PB≈5.57 / 总市值≈1.5 万亿，路由判断正确。

### 2. A 阶段：白酒三件套取数（行情 + 资金流落盘 CSV）
```bash
python scripts/fetch_baijiu.py
```
输出在 `data/`：茅台/五粮液/泸州老窖各 242 行历史行情 + 30 行资金流。

### 3. 完整多智能体投研（需 LLM Key）
复制 `.env.example` 为 `.env`，填入至少一个 LLM Key：
```bash
cp .env.example .env   # 编辑填入 OPENAI_API_KEY 或 DEEPSEEK_API_KEY
```
运行（A 股标的用 6 位代码）：
```bash
python -m src.main --tickers 600519 000858 000568 \
    --start-date 2025-07-06 --end-date 2026-07-06 \
    --model gpt-4.1
```
- 默认模型 `gpt-4.1`（需 `OPENAI_API_KEY`）。
- 国内可用 DeepSeek：填 `DEEPSEEK_API_KEY`，模型名用 `deepseek-chat`（详见 `src/llm/models.py`）。
- 美股标的（如 `AAPL`）同样可跑，自动走原 API。

## 目录结构
```
InsightCN/
├── README.md
├── NOTICE.md          # 派生署名与 MIT 许可证说明
├── LICENSE            # MIT（来自上游）
├── requirements.txt
├── .env.example
├── scripts/
│   ├── fetch_baijiu.py        # A 阶段：白酒三件套取数（东方财富直连）
│   └── test_a_share_layer.py  # 数据层冒烟测试（无需 Key）
├── src/                       # 来自上游 ai-hedge-fund（多智能体引擎）
│   ├── agents/                # 19 个分析智能体
│   ├── data/
│   │   ├── models.py          # Pydantic 数据模型（agent 契约）
│   │   ├── a_share.py         # ★ A 股数据层（新增）
│   │   └── cache.py
│   ├── tools/api.py           # ★ 已加 A 股路由
│   ├── graph/  llm/  utils/  cli/  backtesting/
│   └── main.py                # 入口
└── data/                      # 生成的 CSV（已 gitignore）
```

## 许可证与署名
- 原项目：[virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) —— MIT License
- 本派生项目同样以 **MIT** 发布，保留原 LICENSE 与版权声明，详见 `NOTICE.md`。
- 修改内容：A 股数据层接入（`src/data/a_share.py`）、`api.py` 路由、中文研报输出与 A 股语境提示词（规划中）。

## 路线图 / 已知限制
- [x] A 股行情 + 估值指标接入，19 个 agent 可分析 A 股
- [x] 项目推上 GitHub（YuLei-art/InsightCN）
- [ ] 接入 A 股财报明细（利润表/资产负债表/现金流量表）→ 强化基本面/估值/成长 agent
- [ ] 接入 A 股个股新闻 / 股东增减持
- [ ] 中文研报输出模板
- [ ] 可选：接入用户通达信数据
