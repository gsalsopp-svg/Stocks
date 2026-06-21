"""
app.py
------
Streamlit front-end for the Long-Term Value Investing Valuation Tool.

Run with:  streamlit run app.py
"""
import copy
import dataclasses

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.data_models import CompanyFinancials
from modules.calculations import (
    valuation_ratios, quality_metrics, balance_sheet_strength, capital_allocation,
    enterprise_value,
)
from modules.valuation import (
    all_methods, hidden_asset_value, cash_rich_split, asset_heavy_replacement_value,
    dcf_valuation,
)
from modules.scoring import total_score
from modules.recommendation import build_recommendation
from modules.data_fetcher import fetch_company_from_yahoo, TickerLookupError
from sample_data import PRESETS

st.set_page_config(page_title="Value Investing Valuation Tool", layout="wide", page_icon="📈")

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def pct(x, decimals=1):
    return "n/m" if x is None else f"{x*100:.{decimals}f}%"

def money(x, decimals=0):
    return "n/m" if x is None else f"{x:,.{decimals}f}"

def mult(x, decimals=2):
    return "n/m" if x is None else f"{x:,.{decimals}f}x"

def cur(x, decimals=2, symbol=""):
    return "n/m" if x is None else f"{symbol}{x:,.{decimals}f}"


# ----------------------------------------------------------------------------
# Sidebar — company selection & inputs
# ----------------------------------------------------------------------------
st.sidebar.title("📈 Valuation Tool")
st.sidebar.caption("Long-term value investing — fundamental analysis")

# --- Load from Yahoo Finance via a ticker symbol ---
st.sidebar.subheader("Load from Yahoo Finance")
ticker_text = st.sidebar.text_input(
    "Ticker symbol", value="", placeholder="e.g. GME, BREE.L, SIG.L, CRH, AAPL",
    help="UK-listed shares need the '.L' suffix, e.g. 'BREE.L' for Breedon Group or 'SIG.L' for Signature Aviation.",
)
load_clicked = st.sidebar.button("Load Company", type="primary", use_container_width=True)

st.sidebar.markdown("— or —")
preset_name = st.sidebar.selectbox("Load a sample / preset company", list(PRESETS.keys()), index=0)
st.sidebar.divider()

# --- State management: a ticker load and a preset change are mutually exclusive
# triggers, since Streamlit reruns the whole script on every single widget
# interaction. We track the dropdown's last-seen value separately so that
# clicking "Load Company" never gets silently overwritten by the (unchanged)
# preset selectbox later in this same run, and vice-versa. ---
if "_last_preset_value" not in st.session_state:
    st.session_state["_last_preset_value"] = preset_name
if "company" not in st.session_state:
    st.session_state["company"] = copy.deepcopy(PRESETS[preset_name])

if load_clicked:
    try:
        fetched, fetch_warnings = fetch_company_from_yahoo(ticker_text)
        st.session_state["company"] = fetched
        st.session_state["_last_preset_value"] = preset_name  # don't let the dropdown re-trigger below
        if fetch_warnings:
            st.sidebar.warning(
                f"Loaded {fetched.name} ({fetched.ticker}), but couldn't retrieve: "
                + ", ".join(fetch_warnings) + ". Those fields defaulted to 0 / current-year values — "
                "review them in the sections below."
            )
        else:
            st.sidebar.success(f"Loaded {fetched.name} ({fetched.ticker}) from Yahoo Finance.")
    except TickerLookupError as e:
        st.sidebar.error(str(e))
    except Exception as e:
        st.sidebar.error(f"Unexpected error loading '{ticker_text}': {e}")
elif preset_name != st.session_state["_last_preset_value"]:
    st.session_state["company"] = copy.deepcopy(PRESETS[preset_name])
    st.session_state["_last_preset_value"] = preset_name

c: CompanyFinancials = st.session_state["company"]

with st.sidebar.expander("🏷️ Identity", expanded=True):
    c.name = st.text_input("Company name", c.name)
    c.ticker = st.text_input("Ticker", c.ticker)
    c.currency = st.text_input("Currency", c.currency)
    c.sector_type = st.selectbox("Special handling type", ["Standard", "Cash-Rich", "Cyclical", "Asset-Heavy"],
                                  index=["Standard", "Cash-Rich", "Cyclical", "Asset-Heavy"].index(c.sector_type)
                                  if c.sector_type in ["Standard", "Cash-Rich", "Cyclical", "Asset-Heavy"] else 0)

with st.sidebar.expander("💰 Core Financials", expanded=False):
    c.share_price = st.number_input("Share Price", value=float(c.share_price), step=0.01, format="%.2f")
    c.market_cap = st.number_input("Market Cap (millions)", value=float(c.market_cap), step=1.0)
    c.revenue_ttm = st.number_input("Revenue TTM (millions)", value=float(c.revenue_ttm), step=1.0)
    c.gross_profit = st.number_input("Gross Profit (millions)", value=float(c.gross_profit), step=1.0)
    c.operating_income = st.number_input("Operating Income (millions)", value=float(c.operating_income), step=1.0)
    c.ebitda = st.number_input("EBITDA (millions)", value=float(c.ebitda), step=1.0)
    c.net_income = st.number_input("Net Income (millions)", value=float(c.net_income), step=1.0)
    c.fcf = st.number_input("Free Cash Flow (millions)", value=float(c.fcf), step=1.0)
    c.cash = st.number_input("Cash & Equivalents (millions)", value=float(c.cash), step=1.0)
    c.total_debt = st.number_input("Total Debt (millions)", value=float(c.total_debt), step=1.0)
    c.shares_out = st.number_input("Shares Outstanding (millions)", value=float(c.shares_out), step=1.0)
    c.eps = st.number_input("EPS (TTM, diluted)", value=float(c.eps), step=0.01, format="%.2f")
    c.book_value = st.number_input("Book Value / Total Equity (millions)", value=float(c.book_value), step=1.0)
    c.sga = st.number_input("SG&A (millions)", value=float(c.sga), step=1.0)
    c.rnd = st.number_input("R&D (millions)", value=float(c.rnd), step=1.0)
    c.ev_reported = st.number_input("Enterprise Value (reported, millions)", value=float(c.ev_reported), step=1.0)
    c.forward_eps = st.number_input("Forward EPS (next-FY est.)", value=float(c.forward_eps), step=0.01, format="%.2f")

with st.sidebar.expander("📊 Prior Year & Capital Allocation", expanded=False):
    c.revenue_py = st.number_input("Revenue (Prior Year)", value=float(c.revenue_py), step=1.0)
    c.net_income_py = st.number_input("Net Income (Prior Year)", value=float(c.net_income_py), step=1.0)
    c.fcf_py = st.number_input("FCF (Prior Year)", value=float(c.fcf_py), step=1.0)
    c.eps_py = st.number_input("EPS (Prior Year)", value=float(c.eps_py), step=0.01, format="%.2f")
    c.shares_out_py = st.number_input("Shares Outstanding (Prior Year)", value=float(c.shares_out_py), step=1.0)
    c.dividends_paid = st.number_input("Dividends Paid TTM (millions)", value=float(c.dividends_paid), step=1.0)
    c.buybacks = st.number_input("Buybacks TTM (millions)", value=float(c.buybacks), step=1.0)

with st.sidebar.expander("🏦 Balance Sheet Detail", expanded=False):
    c.current_assets = st.number_input("Current Assets (millions)", value=float(c.current_assets), step=1.0)
    c.current_liabilities = st.number_input("Current Liabilities (millions)", value=float(c.current_liabilities), step=1.0)
    c.total_assets = st.number_input("Total Assets (millions)", value=float(c.total_assets), step=1.0)
    c.assumed_tax_rate = st.slider("Assumed tax rate (for ROIC/NOPAT)", 0.0, 0.4, float(c.assumed_tax_rate), 0.01)

with st.sidebar.expander("🎯 Valuation Assumptions", expanded=False):
    c.target_pe = st.number_input("Target P/E", value=float(c.target_pe), step=0.5)
    c.target_fcf_multiple = st.number_input("Target FCF Multiple", value=float(c.target_fcf_multiple), step=0.5)
    c.target_ev_ebitda = st.number_input("Target EV/EBITDA Multiple", value=float(c.target_ev_ebitda), step=0.5)
    c.graham_growth = st.slider("Graham Growth Rate", 0.0, 0.30, float(c.graham_growth), 0.005, format="%.3f")
    c.peg_growth = st.slider("PEG Growth Rate (EPS CAGR)", 0.0, 0.40, float(c.peg_growth), 0.005, format="%.3f")

with st.sidebar.expander("📉 DCF Assumptions", expanded=False):
    c.dcf_growth_1_5 = st.slider("Revenue Growth Yrs 1-5", -0.10, 0.40, float(c.dcf_growth_1_5), 0.005, format="%.3f")
    c.dcf_growth_6_10 = st.slider("Revenue Growth Yrs 6-10", -0.10, 0.30, float(c.dcf_growth_6_10), 0.005, format="%.3f")
    c.dcf_terminal_growth = st.slider("Terminal Growth Rate", 0.0, 0.05, float(c.dcf_terminal_growth), 0.0025, format="%.4f")
    c.dcf_discount_rate = st.slider("Discount Rate (WACC)", 0.03, 0.20, float(c.dcf_discount_rate), 0.0025, format="%.4f")
    c.dcf_target_fcf_margin = st.slider("Target/Steady-State FCF Margin", -0.10, 0.40, float(c.dcf_target_fcf_margin), 0.005, format="%.3f")

with st.sidebar.expander("💎 Hidden Asset Value (manual)", expanded=False):
    c.ha_land = st.number_input("Undeveloped Land Value", value=float(c.ha_land), step=1.0)
    c.ha_minerals = st.number_input("Mineral / Quarry Reserves Value", value=float(c.ha_minerals), step=1.0)
    c.ha_real_estate = st.number_input("Strategic Real Estate Value", value=float(c.ha_real_estate), step=1.0)
    c.ha_excess_cash = st.number_input("Excess Cash Beyond Operating Needs", value=float(c.ha_excess_cash), step=1.0)
    c.ha_tax_assets = st.number_input("Tax Assets (NOLs, credits)", value=float(c.ha_tax_assets), step=1.0)
    c.ha_investments = st.number_input("Investment Holdings / Securities", value=float(c.ha_investments), step=1.0)
    c.ha_capex = st.number_input("Major Capex Projects Not Yet Reflected", value=float(c.ha_capex), step=1.0)
    c.operating_cash_required = st.number_input("Operating Cash Required", value=float(c.operating_cash_required), step=1.0)

# ----------------------------------------------------------------------------
# Compute everything
# ----------------------------------------------------------------------------
rec = build_recommendation(c)
ratios = rec["ratios"]
quality = rec["quality"]
bs = rec["balance_sheet"]
ca = rec["capital_allocation"]
methods = rec["methods"]
ha = rec["hidden_assets"]
scores = rec["scores"]

# ----------------------------------------------------------------------------
# Header & Summary
# ----------------------------------------------------------------------------
st.title(f"{c.name} ({c.ticker})" if c.ticker else c.name)
st.caption(f"Currency: {c.currency}  |  Special handling: {c.sector_type}  |  All amounts in millions unless per-share")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Current Price", cur(c.share_price))
col2.metric("Reported Fair Value", cur(rec["fair_value_reported"]), f"{rec['upside_reported']*100:+.1f}%")
col3.metric("Adjusted Fair Value", cur(rec["fair_value_adjusted"]), f"{rec['upside_adjusted']*100:+.1f}%")
col4.metric("Value Score", f"{scores['total']:.1f}/100", scores["rating"])
col5.metric("Final Rating", rec["final_rating"])

st.divider()

tabs = st.tabs([
    "📊 Dashboard", "📐 Ratios", "🏆 Quality", "🏦 Balance Sheet", "💸 Capital Allocation",
    "🧮 Valuation Engine", "📉 DCF Detail", "💎 Hidden Assets", "🎯 Scoring", "📚 Documentation",
])

# ---------------- Dashboard ----------------
with tabs[0]:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Valuation Summary — All Methods")
        df_methods = pd.DataFrame({
            "Method": list(methods["methods"].keys()),
            "Fair Value": [cur(v) for v in methods["methods"].values()],
            "vs Price": [pct((v / c.share_price - 1) if c.share_price else None) for v in methods["methods"].values()],
        })
        st.dataframe(df_methods, hide_index=True, use_container_width=True)
        st.metric("Average Fair Value (5 methods)", cur(rec["fair_value_reported"]))

    with right:
        st.subheader("Score Radar")
        categories = ["Valuation", "Quality", "Growth", "Financial Strength", "Capital Allocation"]
        values = [
            scores["valuation"]["total"] * 4,
            scores["quality"]["total"] * 4,
            scores["growth"]["total"] * 4,
            scores["balance_sheet"]["total"] * 4,
            min(ca["Return of Capital Score"] * 10, 100),
        ]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]],
                                       fill='toself', name=c.name))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                           showlegend=False, height=380, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🟢 Bull Case")
    for point in rec["bull_case"]:
        st.markdown(f"- {point}")
    st.subheader("🔴 Bear Case")
    for point in rec["bear_case"]:
        st.markdown(f"- {point}")
    st.subheader("⚠️ Key Risks")
    for point in rec["key_risks"]:
        st.markdown(f"- {point}")
    st.subheader("📝 Investment Thesis")
    st.info(rec["thesis"])
    st.subheader("🏁 Final Rating")
    rating_colors = {"Strong Buy": "🟢", "Buy": "🟢", "Hold": "🟡", "Sell": "🟠", "Strong Sell": "🔴"}
    st.markdown(f"## {rating_colors.get(rec['final_rating'], '')} {rec['final_rating']}")

    if c.sector_type == "Cash-Rich":
        st.divider()
        st.subheader("💰 Cash-Rich Company Split")
        split = cash_rich_split(c)
        cols = st.columns(4)
        cols[0].metric("Enterprise Value", money(split["enterprise_value"]))
        cols[1].metric("Operating Business Value", money(split["operating_business_value"]))
        cols[2].metric("Net Cash Value", money(split["net_cash_value"]))
        cols[3].metric("Investment Portfolio Value", money(split["investment_portfolio_value"]))
        if split["operating_business_value"] < split["enterprise_value"] * 0.3:
            st.warning("Operating Business Value is a small share of Enterprise Value — the market may be "
                       "paying largely for the balance sheet rather than the operating business. Check "
                       "whether that operating business still deserves a standalone multiple.")

    if c.sector_type == "Asset-Heavy":
        st.divider()
        st.subheader("🏗️ Asset-Heavy / Cyclical Business Context")
        rep = asset_heavy_replacement_value(c)
        cols = st.columns(4)
        cols[0].metric("Book Value / Share", cur(rep["book_value_per_share"]))
        cols[1].metric("Hidden Asset Value / Share", cur(rep["adjustment_per_share"]))
        cols[2].metric("Replacement-Adjusted BVPS", cur(rep["adjusted_book_value_per_share"]))
        cols[3].metric("Price / Adjusted Book", mult(rep["price_to_adjusted_book"]))
        st.caption("A Price/Adjusted-Book ratio well below the standard Price/Book (Ratios tab) signals the "
                   "market may not be giving full credit for reserves, land or capex already in the ground.")

# ---------------- Ratios ----------------
with tabs[1]:
    st.subheader("Valuation Ratios")
    rows = [
        ("Enterprise Value (calculated)", money(enterprise_value(c))),
        ("Enterprise Value (reported input)", money(c.ev_reported)),
        ("P/E Ratio", mult(ratios["P/E Ratio"])),
        ("Forward P/E", mult(ratios["Forward P/E"])),
        ("Price / Sales", mult(ratios["Price / Sales"])),
        ("Price / Book", mult(ratios["Price / Book"])),
        ("EV / Revenue", mult(ratios["EV / Revenue"])),
        ("EV / EBITDA", mult(ratios["EV / EBITDA"])),
        ("EV / FCF", mult(ratios["EV / FCF"])),
        ("PEG Ratio", mult(ratios["PEG Ratio"])),
        ("FCF Yield", pct(ratios["FCF Yield"])),
        ("Earnings Yield", pct(ratios["Earnings Yield"])),
    ]
    st.table(pd.DataFrame(rows, columns=["Metric", "Value"]).set_index("Metric"))

# ---------------- Quality ----------------
with tabs[2]:
    st.subheader("Quality Metrics")
    st.markdown("**Margins**")
    m1 = pd.DataFrame([
        ("Gross Margin", pct(quality["Gross Margin"])),
        ("Operating Margin", pct(quality["Operating Margin"])),
        ("Net Margin", pct(quality["Net Margin"])),
        ("EBITDA Margin", pct(quality["EBITDA Margin"])),
    ], columns=["Metric", "Value"]).set_index("Metric")
    st.table(m1)
    st.markdown("**Returns on Capital**")
    m2 = pd.DataFrame([
        ("Return on Equity (ROE)", pct(quality["ROE"])),
        ("Return on Assets (ROA)", pct(quality["ROA"])),
        ("Return on Invested Capital (ROIC)", pct(quality["ROIC"])),
    ], columns=["Metric", "Value"]).set_index("Metric")
    st.table(m2)
    st.markdown("**Growth (YoY)**")
    m3 = pd.DataFrame([
        ("Revenue Growth", pct(quality["Revenue Growth"])),
        ("Earnings (EPS) Growth", pct(quality["Earnings Growth"])),
        ("FCF Growth", pct(quality["FCF Growth"])),
    ], columns=["Metric", "Value"]).set_index("Metric")
    st.table(m3)

# ---------------- Balance Sheet ----------------
with tabs[3]:
    st.subheader("Balance Sheet Strength")
    rows = [
        ("Current Ratio", mult(bs["Current Ratio"])),
        ("Debt / Equity", mult(bs["Debt / Equity"])),
        ("Net Cash Position", money(bs["Net Cash Position"])),
        ("Net Cash / Market Cap", pct(bs["Net Cash / Market Cap"])),
        ("Cash per Share", cur(bs["Cash per Share"])),
        ("Net Debt per Share", cur(bs["Net Debt per Share"])),
        ("Book Value per Share", cur(bs["Book Value per Share"])),
    ]
    st.table(pd.DataFrame(rows, columns=["Metric", "Value"]).set_index("Metric"))

# ---------------- Capital Allocation ----------------
with tabs[4]:
    st.subheader("Capital Allocation")
    rows = [
        ("Buyback Yield", pct(ca["Buyback Yield"])),
        ("Share Count Reduction %", pct(ca["Share Count Reduction %"])),
        ("Dividend Yield", pct(ca["Dividend Yield"])),
        ("Total Shareholder Yield", pct(ca["Total Shareholder Yield"])),
        ("Return of Capital Score (0-10)", f"{ca['Return of Capital Score']:.1f}"),
    ]
    st.table(pd.DataFrame(rows, columns=["Metric", "Value"]).set_index("Metric"))

# ---------------- Valuation Engine ----------------
with tabs[5]:
    st.subheader("Valuation Engine — Five Fair Value Methods")
    c1, c2, c3 = st.columns(3)
    c1.metric("1. P/E Multiple", cur(methods["methods"]["1. P/E Multiple"]))
    c2.metric("2. FCF Multiple", cur(methods["methods"]["2. FCF Multiple"]))
    c3.metric("3. EV/EBITDA", cur(methods["methods"]["3. EV/EBITDA"]))
    c4, c5 = st.columns(2)
    c4.metric("4. Graham Formula", cur(methods["methods"]["4. Graham Formula"]))
    c5.metric("5. DCF (10-Year)", cur(methods["methods"]["5. DCF (10-Year)"]))
    st.divider()
    st.metric("Average Fair Value (all 5 methods)", cur(methods["average_fair_value"]),
              f"{(methods['average_fair_value']/c.share_price-1)*100:+.1f}% vs price" if c.share_price else None)
    st.caption("Method detail — EV/EBITDA: Implied EV = "
               f"{money(methods['ev_ebitda_detail']['implied_ev'])}, Implied Equity Value = "
               f"{money(methods['ev_ebitda_detail']['implied_equity'])}.")

# ---------------- DCF Detail ----------------
with tabs[6]:
    st.subheader("10-Year Discounted Cash Flow")
    dcf = methods["dcf_detail"]
    df_dcf = pd.DataFrame(dcf["rows"])
    df_dcf["growth"] = df_dcf["growth"].map(lambda x: f"{x*100:.1f}%")
    df_dcf["fcf_margin"] = df_dcf["fcf_margin"].map(lambda x: f"{x*100:.1f}%")
    df_dcf["revenue"] = df_dcf["revenue"].map(lambda x: f"{x:,.0f}")
    df_dcf["fcf"] = df_dcf["fcf"].map(lambda x: f"{x:,.0f}")
    df_dcf["discount_factor"] = df_dcf["discount_factor"].map(lambda x: f"{x:.3f}")
    df_dcf["pv"] = df_dcf["pv"].map(lambda x: f"{x:,.0f}")
    df_dcf.columns = ["Year", "Revenue", "Growth %", "FCF Margin %", "Free Cash Flow", "Discount Factor", "PV of FCF"]
    st.dataframe(df_dcf, hide_index=True, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Sum of PV of Explicit FCFs", money(dcf["sum_pv_explicit"]))
    c2.metric("PV of Terminal Value", money(dcf["pv_terminal_value"]))
    c3.metric("Enterprise Value (DCF)", money(dcf["enterprise_value"]))
    c4, c5 = st.columns(2)
    c4.metric("Equity Value (DCF)", money(dcf["equity_value"]))
    c5.metric("Fair Value per Share (DCF)", cur(dcf["fair_value"]))

# ---------------- Hidden Assets ----------------
with tabs[7]:
    st.subheader("Hidden Asset Value & Special Situations")
    rows = [
        ("Undeveloped Land Value", money(c.ha_land)),
        ("Mineral / Quarry Reserves Value", money(c.ha_minerals)),
        ("Strategic Real Estate Value", money(c.ha_real_estate)),
        ("Excess Cash Beyond Operating Needs", money(c.ha_excess_cash)),
        ("Tax Assets (NOLs, credits)", money(c.ha_tax_assets)),
        ("Investment Holdings / Securities", money(c.ha_investments)),
        ("Major Capex Projects Not Yet Reflected", money(c.ha_capex)),
        ("TOTAL HIDDEN ASSET VALUE", money(ha["total"])),
        ("Hidden Asset Value per Share", cur(ha["per_share"])),
    ]
    st.table(pd.DataFrame(rows, columns=["Item", "Value"]).set_index("Item"))

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Reported Fair Value / Share", cur(rec["fair_value_reported"]))
    c2.metric("Adjusted Fair Value / Share", cur(rec["fair_value_adjusted"]),
              f"{rec['upside_adjusted']*100:+.1f}% vs price")

    st.divider()
    st.markdown("**Cash-Rich Company Split**")
    split = cash_rich_split(c)
    st.json({k: round(v, 2) for k, v in split.items()})

    st.divider()
    st.markdown("**Asset-Heavy / Cyclical Replacement Value**")
    rep = asset_heavy_replacement_value(c)
    st.json({k: (round(v, 2) if v is not None else None) for k, v in rep.items()})

# ---------------- Scoring ----------------
with tabs[8]:
    st.subheader("100-Point Value Investing Score")
    for label, sub in [("A. Valuation (25 pts)", scores["valuation"]),
                        ("B. Quality (25 pts)", scores["quality"]),
                        ("C. Growth (25 pts)", scores["growth"]),
                        ("D. Balance Sheet Strength (25 pts)", scores["balance_sheet"])]:
        st.markdown(f"**{label} — {sub['total']:.1f} / 25**")
        items = {k: v for k, v in sub.items() if k != "total"}
        st.table(pd.DataFrame(list(items.items()), columns=["Metric", "Points"]).set_index("Metric"))
    st.divider()
    st.metric("TOTAL SCORE", f"{scores['total']:.1f} / 100", scores["rating"])
    st.caption("90-100 Exceptional | 80-89 Excellent | 70-79 Good | 60-69 Average | below 60 High Risk")

# ---------------- Documentation ----------------
with tabs[9]:
    st.subheader("Methodology & Assumptions")
    st.markdown("""
**Valuation methods**
1. **P/E Multiple** — Fair Value = EPS × Target P/E.
2. **FCF Multiple** — Fair Value = (FCF / Shares) × Target FCF Multiple.
3. **EV/EBITDA** — Implied EV = EBITDA × Target Multiple → Implied Equity = EV − Debt + Cash → ÷ Shares.
4. **Graham Formula** — Intrinsic Value = EPS × (8.5 + 2 × Growth Rate), per Benjamin Graham's classic formula.
5. **DCF (10-Year)** — Two-stage growth (Yrs 1-5, Yrs 6-10), FCF margin ramps to a steady-state target,
   Gordon Growth terminal value, discounted at the WACC.

**Scoring (100 points)** — 25 each for Valuation, Quality, Growth, Balance Sheet Strength, using tiered
thresholds (see `modules/scoring.py` for exact breakpoints).

**Hidden Asset Value** — manual analyst adjustments (land, mineral/quarry reserves, real estate, excess
cash, tax assets, investment holdings, major capex) added to the Reported Fair Value to produce an
Adjusted Fair Value.

**Special handling**
- *Cash-Rich* (Berkshire, GameStop, Alphabet): Enterprise Value is split into Operating Business Value,
  Net Cash Value and Investment Portfolio Value.
- *Cyclical*: normalise growth/margin assumptions across a full cycle rather than a single peak/trough year.
- *Asset-Heavy* (e.g. Breedon Group): replacement-value-adjusted book value captures reserves/land/capex
  not yet earning a return.

**Disclaimer** — This tool is educational/analytical, not investment advice. Sample figures for GameStop
and Breedon Group are approximate and illustrative; verify against the latest filings before any real
investment decision.
""")
