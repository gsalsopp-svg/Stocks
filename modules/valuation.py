"""
modules/valuation.py
---------------------
The five fair-value methods plus a full 10-year, two-stage DCF.
"""
from .data_models import CompanyFinancials
from .calculations import _safe_div, enterprise_value


def fv_pe_multiple(c: CompanyFinancials) -> float:
    """Method 1: Fair Value = EPS x Target P/E"""
    return c.eps * c.target_pe


def fv_fcf_multiple(c: CompanyFinancials) -> float:
    """Method 2: Fair Value = FCF per Share x Target FCF Multiple"""
    fcf_per_share = _safe_div(c.fcf, c.shares_out) or 0
    return fcf_per_share * c.target_fcf_multiple


def fv_ev_ebitda(c: CompanyFinancials) -> dict:
    """Method 3: EV/EBITDA -> implied EV -> implied equity value -> fair value/share"""
    implied_ev = c.ebitda * c.target_ev_ebitda
    implied_equity = implied_ev - c.total_debt + c.cash
    fair_value = _safe_div(implied_equity, c.shares_out) or 0
    return {"implied_ev": implied_ev, "implied_equity": implied_equity, "fair_value": fair_value}


def fv_graham(c: CompanyFinancials) -> float:
    """Method 4: Graham Formula — Intrinsic Value = EPS x (8.5 + 2 x Growth Rate)
    Growth rate is expressed as a whole number (e.g. 8 for 8%), per Graham's original convention.
    """
    growth_whole_number = c.graham_growth * 100
    return c.eps * (8.5 + 2 * growth_whole_number)


def dcf_valuation(c: CompanyFinancials, years: int = 10) -> dict:
    """Method 5: Two-stage 10-year DCF with Gordon Growth terminal value.

    - Years 1-5 grow revenue at dcf_growth_1_5
    - Years 6-10 grow revenue at dcf_growth_6_10
    - FCF margin ramps linearly from current FCF margin to dcf_target_fcf_margin
    - Terminal value = Year10 FCF x (1+terminal growth) / (WACC - terminal growth)
    - All cash flows discounted at dcf_discount_rate
    """
    current_margin = _safe_div(c.fcf, c.revenue_ttm) or 0
    wacc = c.dcf_discount_rate
    rows = []
    revenue = c.revenue_ttm
    pv_sum = 0.0
    for yr in range(1, years + 1):
        growth = c.dcf_growth_1_5 if yr <= 5 else c.dcf_growth_6_10
        revenue = revenue * (1 + growth)
        margin = current_margin + (c.dcf_target_fcf_margin - current_margin) * (yr / years)
        fcf_yr = revenue * margin
        discount_factor = 1 / ((1 + wacc) ** yr)
        pv = fcf_yr * discount_factor
        pv_sum += pv
        rows.append({
            "year": yr, "revenue": revenue, "growth": growth, "fcf_margin": margin,
            "fcf": fcf_yr, "discount_factor": discount_factor, "pv": pv,
        })

    last_fcf = rows[-1]["fcf"]
    last_discount_factor = rows[-1]["discount_factor"]
    if wacc <= c.dcf_terminal_growth:
        terminal_value = 0.0  # guard against an invalid/negative-denominator assumption
    else:
        terminal_value = last_fcf * (1 + c.dcf_terminal_growth) / (wacc - c.dcf_terminal_growth)
    pv_terminal = terminal_value * last_discount_factor

    ev_dcf = pv_sum + pv_terminal
    equity_value = ev_dcf - c.total_debt + c.cash
    fair_value = _safe_div(equity_value, c.shares_out) or 0

    return {
        "rows": rows,
        "sum_pv_explicit": pv_sum,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal,
        "enterprise_value": ev_dcf,
        "equity_value": equity_value,
        "fair_value": fair_value,
    }


def all_methods(c: CompanyFinancials) -> dict:
    """Run all five methods and return a single summary dict, used by the UI and scoring."""
    pe = fv_pe_multiple(c)
    fcf_m = fv_fcf_multiple(c)
    ev_ebitda = fv_ev_ebitda(c)
    graham = fv_graham(c)
    dcf = dcf_valuation(c)

    methods = {
        "1. P/E Multiple": pe,
        "2. FCF Multiple": fcf_m,
        "3. EV/EBITDA": ev_ebitda["fair_value"],
        "4. Graham Formula": graham,
        "5. DCF (10-Year)": dcf["fair_value"],
    }
    valid_values = [v for v in methods.values() if v and v > 0]
    average_fv = sum(valid_values) / len(valid_values) if valid_values else 0.0

    return {
        "methods": methods,
        "ev_ebitda_detail": ev_ebitda,
        "dcf_detail": dcf,
        "average_fair_value": average_fv,
    }


def hidden_asset_value(c: CompanyFinancials) -> dict:
    total = (c.ha_land + c.ha_minerals + c.ha_real_estate + c.ha_excess_cash
             + c.ha_tax_assets + c.ha_investments + c.ha_capex)
    per_share = _safe_div(total, c.shares_out) or 0
    return {"total": total, "per_share": per_share}


def cash_rich_split(c: CompanyFinancials) -> dict:
    """Splits Enterprise Value into Operating Business Value / Net Cash / Investment Portfolio.
    Useful for cash-rich names (Berkshire, GameStop, Alphabet) so the operating
    business isn't valued at an inflated multiple that's really paying for the balance sheet.
    """
    ev = enterprise_value(c)
    net_cash = max(c.cash - c.total_debt, 0)
    investments = c.ha_investments
    operating_business_value = ev - investments - net_cash
    return {
        "enterprise_value": ev,
        "net_cash_value": net_cash,
        "investment_portfolio_value": investments,
        "operating_business_value": operating_business_value,
        "operating_business_value_per_share": _safe_div(operating_business_value, c.shares_out) or 0,
    }


def asset_heavy_replacement_value(c: CompanyFinancials) -> dict:
    """Replacement-value-adjusted book value for asset-heavy/cyclical businesses
    (e.g. quarry/mineral reserves, land, major capex not yet earning a return).
    """
    book_value_per_share = _safe_div(c.book_value, c.shares_out) or 0
    adjustment = c.ha_land + c.ha_minerals + c.ha_real_estate + c.ha_capex
    adjustment_per_share = _safe_div(adjustment, c.shares_out) or 0
    adjusted_bvps = book_value_per_share + adjustment_per_share
    price_to_adjusted_book = _safe_div(c.share_price, adjusted_bvps)
    return {
        "book_value_per_share": book_value_per_share,
        "adjustment_per_share": adjustment_per_share,
        "adjusted_book_value_per_share": adjusted_bvps,
        "price_to_adjusted_book": price_to_adjusted_book,
    }
