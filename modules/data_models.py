"""
modules/data_models.py
----------------------
Defines the CompanyFinancials dataclass: the single source of truth for every
raw input the valuation tool needs. Mirrors the 'Data' tab of the companion
Excel workbook field-for-field, so the two tools stay logically identical.
"""
from dataclasses import dataclass, field, asdict


@dataclass
class CompanyFinancials:
    # --- Identity ---
    name: str = "New Company"
    ticker: str = ""
    currency: str = "USD"
    sector_type: str = "Standard"  # Standard | Cash-Rich | Cyclical | Asset-Heavy

    # --- Core financials (currency units, millions unless noted) ---
    share_price: float = 0.0
    market_cap: float = 0.0
    revenue_ttm: float = 0.0
    gross_profit: float = 0.0
    operating_income: float = 0.0
    ebitda: float = 0.0
    net_income: float = 0.0
    fcf: float = 0.0
    cash: float = 0.0
    total_debt: float = 0.0
    shares_out: float = 0.0
    eps: float = 0.0
    book_value: float = 0.0          # total shareholders' equity
    sga: float = 0.0
    rnd: float = 0.0
    ev_reported: float = 0.0

    # --- Prior-year comparatives (for growth) ---
    revenue_py: float = 0.0
    net_income_py: float = 0.0
    fcf_py: float = 0.0
    eps_py: float = 0.0
    shares_out_py: float = 0.0

    # --- Capital allocation ---
    dividends_paid: float = 0.0
    buybacks: float = 0.0

    # --- Balance sheet detail ---
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    total_assets: float = 0.0

    # --- Forward estimate ---
    forward_eps: float = 0.0

    # --- Valuation assumptions (editable) ---
    target_pe: float = 15.0
    target_fcf_multiple: float = 15.0
    target_ev_ebitda: float = 10.0
    graham_growth: float = 0.05        # decimal, e.g. 0.05 = 5%
    peg_growth: float = 0.08           # decimal
    dcf_growth_1_5: float = 0.04       # decimal
    dcf_growth_6_10: float = 0.025     # decimal
    dcf_terminal_growth: float = 0.02  # decimal
    dcf_discount_rate: float = 0.09    # decimal (WACC)
    dcf_target_fcf_margin: float = 0.08  # decimal

    # --- Hidden asset value (manual analyst adjustments) ---
    ha_land: float = 0.0
    ha_minerals: float = 0.0
    ha_real_estate: float = 0.0
    ha_excess_cash: float = 0.0
    ha_tax_assets: float = 0.0
    ha_investments: float = 0.0
    ha_capex: float = 0.0
    operating_cash_required: float = 0.0

    # --- Assumed tax rate for ROIC/NOPAT (editable) ---
    assumed_tax_rate: float = 0.21

    def as_dict(self):
        return asdict(self)
