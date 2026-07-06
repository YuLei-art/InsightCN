# A 股 AI 投研多智能体（进行中）

把 **AkShare（① 数据底座）** 与 **ai-hedge-fund（③ 多智能体架构）** 组合，
做一个**支持 A 股**的 AI 投研多智能体。

## 阶段进度
- [x] **A 阶段**：数据层跑通（白酒三件套：茅台 / 五粮液 / 泸州老窖）
      - 实际用原生 `requests` 直连东方财富（AkShare 在沙箱中因 requests 栈与代理不兼容被中断，
        等价实现；你本机可直接用 AkShare，见 `scripts/fetch_baijiu.py` 的 `fetch_hist_akshare`）
- [ ] **B 阶段**：fork `ai-hedge-fund`，用本数据层替换其美股 `FINANCIAL_DATASETS_API`，搭 A 股 AI 投研原型

## 环境
- Python 3.13（WorkBuddy managed runtime）
- 独立 venv：`~/.workbuddy/binaries/python/envs/a-share-research`
- 依赖：`akshare`、`pandas`（见 `requirements.txt`）

## 快速开始（A 阶段）
```bash
# 激活 venv（Windows / git-bash）
~/.workbuddy/binaries/python/envs/a-share-research/Scripts/python.exe -m pip install -r requirements.txt

# 跑通白酒三件套取数
~/.workbuddy/binaries/python/envs/a-share-research/Scripts/python.exe scripts/fetch_baijiu.py
```
输出 CSV 在 `data/` 目录。

## 目录结构
```
a-share-ai-research/
├── requirements.txt
├── .gitignore
├── scripts/
│   └── fetch_baijiu.py      # A 阶段：AkShare 取数验证
├── data/                    # 生成的 CSV（已 gitignore）
└── README.md
```

## 下一步（B 阶段规划）
1. Fork `virattt/ai-hedge-fund`（MIT）
2. 把其 `FINANCIAL_DATASETS_API` 美股数据层替换为 AkShare
3. 接入白酒三件套 + 用户通达信数据
4. 中文研报输出，推回 `YuLei-art` 自己的仓库
