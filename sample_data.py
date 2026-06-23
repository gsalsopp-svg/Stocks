"""
sample_data.py
---------------
Worked-example presets for GameStop Corp. (GME) and Breedon Group plc (BREE.L),
mirroring the 'Data' tab of the companion Excel workbook. Figures are
approximate, illustrative TTM/FY figures compiled from public filings and
financial-data aggregators as of ~June 2026 — see Documentation for caveats.
"""
from modules.data_models import CompanyFinancials

GAMESTOP = CompanyFinancials(
    name="GameStop Corp.", ticker="GME", currency="USD", sector_type="Cash-Rich", industry="Retail",
    share_price=21.25, market_cap=9520, revenue_ttm=3630, gross_profit=1196,
    operating_income=286, ebitda=340, net_income=763, fcf=597, cash=9000,
    total_debt=4200, shares_out=448, eps=1.70, book_value=6048, sga=910, rnd=0,
    ev_reported=4720,
    revenue_py=3823, net_income_py=131, fcf_py=130, eps_py=0.30, shares_out_py=460,
    dividends_paid=0, buybacks=250,
    current_assets=9400, current_liabilities=900, total_assets=11500,
    forward_eps=0.95,
    target_pe=20, target_fcf_multiple=20, target_ev_ebitda=12,
    graham_growth=0.08, peg_growth=0.10,
    dcf_growth_1_5=0.05, dcf_growth_6_10=0.03, dcf_terminal_growth=0.025,
    dcf_discount_rate=0.09, dcf_target_fcf_margin=0.10,
    ha_land=0, ha_minerals=0, ha_real_estate=0, ha_excess_cash=8500,
    ha_tax_assets=700, ha_investments=370, ha_capex=0, operating_cash_required=300,
)

BREEDON = CompanyFinancials(
    name="Breedon Group plc", ticker="BREE.L", currency="GBP", sector_type="Asset-Heavy", industry="Materials",
    share_price=3.35, market_cap=1161, revenue_ttm=1714, gross_profit=600,
    operating_income=170, ebitda=279, net_income=82, fcf=133, cash=25,
    total_debt=605, shares_out=347, eps=0.242, book_value=1043, sga=230, rnd=5,
    ev_reported=1741,
    revenue_py=1576, net_income_py=90, fcf_py=114, eps_py=0.281, shares_out_py=343,
    dividends_paid=52, buybacks=10,
    current_assets=690, current_liabilities=470, total_assets=2600,
    forward_eps=0.27,
    target_pe=14, target_fcf_multiple=14, target_ev_ebitda=7.5,
    graham_growth=0.06, peg_growth=0.07,
    dcf_growth_1_5=0.04, dcf_growth_6_10=0.025, dcf_terminal_growth=0.02,
    dcf_discount_rate=0.085, dcf_target_fcf_margin=0.075,
    ha_land=150, ha_minerals=400, ha_real_estate=50, ha_excess_cash=0,
    ha_tax_assets=20, ha_investments=0, ha_capex=80, operating_cash_required=25,
)

BLANK = CompanyFinancials(name="New Company", ticker="", currency="USD", sector_type="Standard")

PRESETS = {
    "GameStop Corp. (GME)": GAMESTOP,
    "Breedon Group plc (BREE.L)": BREEDON,
    "Custom / Blank Template": BLANK,
}
