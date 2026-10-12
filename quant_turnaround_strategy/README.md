# Quantitative Turnaround Strategy System (2001 – Present)
### 퀀트 턴어라운드 전략 시스템 (2001년~현재)

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit%201.35%2B-FF4B4B.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/charts-Plotly%205.20%2B-3F4F75.svg)](https://plotly.com/)
[![Verification Gates](https://img.shields.io/badge/verification-5%2F5%20Gates%20Passed-00C853.svg)](verify_system.py)
[![Tests](https://img.shields.io/badge/tests-255%2F255%20Passed-00C853.svg)](tests/)

---

## 1. System Overview (시스템 개요)

The **Quantitative Turnaround Strategy System** is a production-grade, lookahead-bias-free algorithmic trading and asset allocation platform. It backtests, optimizes, and deploys an investment strategy combining core ETF anchors (**QQQ** and **SOXX**) with opportunistic individual 52-week-low turnaround stocks from **July 10, 2001** (SOXX launch inception) to the present.

본 시스템은 2001년 7월 10일(SOXX 상장일)부터 현재까지 나스닥 100(QQQ)과 필라델피아 반도체 지수(SOXX)를 코어 앵커로 편입하고, 52주 신저가 종목 중 펀더멘털 턴어라운드 유망 종목을 선별·편입하는 퀀트 트레이딩 및 동적 자산배분 플랫폼입니다.

### Core Mathematical & Economic Principles (핵심 원칙)

```
+---------------------------------------------------------------------------------------------------+
|                        QUANTITATIVE TURNAROUND STRATEGY SYSTEM ARCHITECTURE                       |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ Data Pipeline ] ---> [ Strategy & Backtest Engine ] ---> [ Enhanced Strategy / Regime Filter ] |
|  - QQQ & SOXX from 2001    - Base: QQQ + SOXX + Turnaround   - Trend SMA + Vol-Target + Momentum  |
|  - USDKRW=X FX Feed        - Weekly Rebalancing (0-3 stocks) - Dual-Currency (USD / KRW)          |
|  - 52w-Low Screener        - Real Friction & 22% Tax Engine  - Calmar / Annual MDD Optimization   |
|  - SEC Filing Lag Audit    - Risk Manager (Stop/Take-Profit)                                      |
|            |                                |                                   |                 |
|            +--------------------------------+-----------------------------------+                 |
|                                             |                                                     |
|                                             v                                                     |
|                   +---------------------------------------------------+                           |
|                   |  STREAMLIT INTERACTIVE DASHBOARD (app.py)         |                           |
|                   |  -----------------------------------------------  |                           |
|                   |  - Tab 1: Cumulative Performance & Underwater DD  |                           |
|                   |  - Tab 2: Calendar Year Breakdown (2001-2026)     |                           |
|                   |  - Tab 3: Dynamic Asset Allocation & Heatmaps     |                           |
|                   |  - Tab 4: Trade Log & Turnaround Selection Journal|                           |
|                   |  - Tab 5: Live Simulation Lab & Parameter Tuning  |                           |
|                   +---------------------------------------------------+                           |
|                                             |                                                     |
|            +--------------------------------+--------------------------------+                    |
|            v                                                                 v                    |
|  +-------------------------------------+                  +------------------------------------+  |
|  | AUTOMATED VERIFICATION SCRIPT       |                  | 4-TIER E2E TEST SUITE              |  |
|  | verify_system.py (5 Core Gates)     |                  | (pytest tests/)                    |  |
|  | 1. Data Bounds (2001-07-10 to now)  |                  | - Tier 1: Feature Coverage         |  |
|  | 2. Zero Lookahead Bias Audit        |                  | - Tier 2: Boundary & Corner Cases  |  |
|  | 3. Calendar Annual MDD & Calmar Math|                  | - Tier 3: Parameter Combinations   |  |
|  | 4. Strategy Superiority Proof       |                  | - Tier 4: Historical Stress Regimes|  |
|  | 5. Streamlit AST Syntax Validation  |                  +------------------------------------+  |
|  +-------------------------------------+                                                          |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Quantitative Formulations (수학적 모델링)

### 2.1 Calendar Year Maximum Drawdown (연간 MDD)
Traditional overall MDD carries previous peak watermarks across calendar years, obscuring single-year drawdowns. This system evaluates independent calendar year intra-year MDD for each year $Y \in [2001, 2026]$:

$$\text{MDD}_Y = \min_{t \in Y} \left( \frac{V_t - \max_{s \le t, s \in Y} V_s}{\max_{s \le t, s \in Y} V_s} \right)$$

### 2.2 Calmar / MAR Ratio (칼마 비율)
Objective function optimizing compound return relative to worst single-year maximum drawdown:

$$\text{Calmar Ratio} = \frac{\text{CAGR}}{\max_{Y} |\text{Annual MDD}_Y|}$$

### 2.3 Real-World Execution Frictions & Korean Taxation (실거래 비용 및 세금 모델)
1. **Transaction Costs**:
   - Commissions: $5.0 \text{ bps}$ ($0.05\%$)
   - ETF Slippage: $2.0 \text{ bps}$ ($0.02\%$)
   - Stock Slippage: $10.0 \text{ bps}$ ($0.10\%$)
2. **Korean Overseas Capital Gains Tax (해외주식 양도소득세)**:
   - Annual basic deduction: $2,500,000 \text{ KRW}$ (250만 원 기본공제)
   - Flat tax rate: $22\%$ on net realized gains exceeding deduction, settled at calendar year-end:

$$\text{Taxable Base}_Y = \max(0, \text{Net Realized Gains KRW}_Y - 2,500,000)$$
$$\text{Tax Paid KRW}_Y = \text{Taxable Base}_Y \times 0.22$$

### 2.4 Enhanced Alternative Strategy: AR-DM (적응형 국면 전환 듀얼 모멘텀)
- **Macro Trend Filter**: 200-day SMA on QQQ. If $P_t \le \text{SMA}_{200}$, portfolio reallocates up to $85\%$ to cash defense, completely halting new turnaround entries.
- **Dual-Momentum Relative Strength Tilt**: Rotates between QQQ and SOXX based on 63-day and 126-day price momentum, tilting up to $55\%$ weight into the outperforming ETF.
- **Asymmetric Profit Ratchet**:
  - Initial entry: Hard stop at $-10\%$.
  - Break-even ratchet: At $+20\%$ gain, stop moved to cost basis ($0\%$ downside risk).
  - Trailing ratchet: At $+40\%$ gain, locks in profits via an $8\%$ trailing stop from peak.

---

## 3. Streamlit Interactive Dashboard Tabs (대시보드 5대 탭)

| Tab | Name | Key Functionalities |
|:---:|:---|:---|
| **Tab 1** | **📈 Cumulative Performance & Overview** | Interactive Plotly cumulative NAV curve (USD/KRW, Gross/Net Tax), linked underwater drawdown subplot, shaded crisis periods, KPI metric cards (CAGR, Max MDD, Calmar, Sharpe, Win Rate). |
| **Tab 2** | **📅 Calendar Year Breakdown (2001-2026)** | 26-year performance table, annual returns, intra-year drawdowns, Return/MDD ratios, and crisis highlights (2002 Dot-com bust, 2008 Lehman GFC, 2022 Tech Bear). |
| **Tab 3** | **📊 Dynamic Asset Allocation & Heatmaps** | 100% stacked area charts of portfolio weights over time (QQQ, SOXX, Stocks, Cash), regime time distribution, 2D monthly returns heatmap. |
| **Tab 4** | **📜 Trade Log & Turnaround Decisions** | Filterable trade history, transaction costs & friction summaries, annual Korean tax records, and point-in-time SEC filing turnaround case studies. |
| **Tab 5** | **🧪 Live Simulation Lab & Tuning** | Real-time parameter tuning sidebar (weights, stop-loss, profit-target, holding weeks, regime SMA window), instant backtest execution button, and KPI delta comparison cards. |

---

## 4. Quick Start & Execution (실행 방법)

### 4.1 Launch Interactive Web Dashboard
- **Windows Batch**: Double-click `run_app.bat`
- **PowerShell**: Run `./run_app.ps1`
- **CLI**:
  ```bash
  python -m streamlit run app.py
  ```
  Dashboard opens automatically at `http://localhost:8501`.

### 4.2 Run Programmatic Automated Verification
Execute the 5-Gate master verification script:
```bash
python verify_system.py --verbose
```
Expected output:
```
========================================================================================
  QUANTITATIVE TURNAROUND STRATEGY SYSTEM: MASTER PROGRAMMATIC VERIFICATION
----------------------------------------------------------------------------------------
Gate 1   | Data Date Bounds & Ingestion Completeness    | [PASS]
Gate 2   | Zero Lookahead Bias Audit                    | [PASS]
Gate 3   | Calendar Annual MDD & Calmar Math            | [PASS]
Gate 4   | Strategy Superiority Proof                   | [PASS]
Gate 5   | Streamlit Application Code & Syntax Validation | [PASS]
----------------------------------------------------------------------------------------
  [SUCCESS] ALL GATES PASSED (5/5)
========================================================================================
```

### 4.3 Run Test Suite
```bash
python -m pytest tests/ -v
```
All 255 tests across Tier 1 (Feature Coverage), Tier 2 (Boundary Cases), Tier 3 (Combinations), and Tier 4 (Historical Stress Regimes) pass with 100% success rate.

---

## 5. Repository File Structure (디렉터리 구조)

```
quant_turnaround_strategy/
├── app.py                              # Streamlit Web Dashboard entrypoint
├── verify_system.py                    # 5-Gate Master Programmatic Verification CLI
├── run_app.bat                         # Windows one-click batch launcher
├── run_app.ps1                         # PowerShell environment launcher
├── requirements.txt                    # Production pinned dependencies
├── .gitignore                          # Clean production Git ignore rules
├── README.md                           # Bilingual documentation & architecture guide
├── PROJECT.md                          # Full architectural blueprint & interface contracts
├── config/                             # Strategy hyperparameters & data paths
├── data/
│   ├── cache/                          # Offline parquet price caches (etf_prices, fx_rates)
│   └── seed/                           # Seed historical fundamentals & universe constituents
├── src/
│   ├── data/                           # Lookahead-free ingestion & PIT universe
│   ├── engine/                         # Multi-asset backtester, tax engine & metrics
│   ├── models/                         # Dataclasses & schema definitions
│   ├── screening/                      # 52w rolling low & turnaround proxy scoring
│   ├── strategies/                     # Base Strategy & Enhanced Strategy (AR-DM)
│   └── ui/                             # Modular Streamlit UI tabs, components, and charts
└── tests/                              # Comprehensive 4-Tier E2E test suite (255 tests)
```

---

## 6. License & Institutional Compliance

Built for institutional algorithmic quantitative research. Backtest guarantees strict zero lookahead bias, point-in-time financial publication lag compliance, and realistic real-world execution friction modeling.
