"""
modules/calculations.py
------------------------
Pure functions computing Valuation Ratios, Quality Metrics, Balance Sheet
Strength and Capital Allocation metrics from a CompanyFinancials object.
Every function is defensive against divide-by-zero / missing data and
returns None (rendered as "n/m" by the UI) rather than raising.
"""
from .data_models import CompanyFinancials


def _safe_div(a, b):
    try:
        if b in (0, None) or a is None:
            return None
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


def enterprise_value(c: CompanyFinancials) -> float:
    """EV = Market Cap + Total Debt - Cash (the figure used throughout the model)."""
    return c.market_cap + c.total_debt - c.cash


def valuation_ratios(c: CompanyFinancials) -> dict:
    ev = enterprise_value(c)
    return {
        "EV (calculated)": ev,
        "EV (reported input)": c.ev_reported,
        "P/E Ratio": _safe_div(c.share_price, c.eps),
        "Forward P/E": _safe_div(c.share_price, c.forward_eps),
        "Price / Sales": _safe_div(c.market_cap, c.revenue_ttm),
        "Price / Book": _safe_div(c.market_cap, c.book_value),
        "EV / Revenue": _safe_div(ev, c.revenue_ttm),
        "EV / EBITDA": _safe_div(ev, c.ebitda),
        "EV / FCF": _safe_div(ev, c.fcf),
        "PEG Ratio": _safe_div(_safe_div(c.share_price, c.eps), (c.peg_growth * 100) if c.peg_growth else None),
        "FCF Yield": _safe_div(c.fcf, c.market_cap),
        "Earnings Yield": _safe_div(c.eps, c.share_price),
    }


def quality_metrics(c: CompanyFinancials) -> dict:
    invested_capital = c.total_debt + c.book_value - c.cash
    nopat = c.operating_income * (1 - c.assumed_tax_rate)
    return {
        "Gross Margin": _safe_div(c.gross_profit, c.revenue_ttm),
        "Operating Margin": _safe_div(c.operating_income, c.revenue_ttm),
        "Net Margin": _safe_div(c.net_income, c.revenue_ttm),
        "EBITDA Margin": _safe_div(c.ebitda, c.revenue_ttm),
        "Invested Capital": invested_capital,
        "NOPAT": nopat,
        "ROE": _safe_div(c.net_income, c.book_value),
        "ROA": _safe_div(c.net_income, c.total_assets),
        "ROIC": _safe_div(nopat, invested_capital),
        "Revenue Growth": _safe_div(c.revenue_ttm - c.revenue_py, c.revenue_py),
        "Earnings Growth": _safe_div(c.eps - c.eps_py, c.eps_py),
        "FCF Growth": _safe_div(c.fcf - c.fcf_py, c.fcf_py),
    }


def balance_sheet_strength(c: CompanyFinancials) -> dict:
    net_cash = c.cash - c.total_debt
    return {
        "Current Ratio": _safe_div(c.current_assets, c.current_liabilities),
        "Debt / Equity": _safe_div(c.total_debt, c.book_value),
        "Net Cash Position": net_cash,
        "Net Cash / Market Cap": _safe_div(net_cash, c.market_cap),
        "Cash per Share": _safe_div(c.cash, c.shares_out),
        "Net Debt per Share": _safe_div(c.total_debt - c.cash, c.shares_out),
        "Book Value per Share": _safe_div(c.book_value, c.shares_out),
    }


def capital_allocation(c: CompanyFinancials) -> dict:
    buyback_yield = _safe_div(c.buybacks, c.market_cap) or 0
    dividend_yield = _safe_div(c.dividends_paid, c.market_cap) or 0
    share_reduction = _safe_div(c.shares_out_py - c.shares_out, c.shares_out_py)
    shareholder_yield = buyback_yield + dividend_yield
    bonus = max(share_reduction, 0) * 0.4 * 100 if share_reduction else 0
    roc_score = min(10, round(buyback_yield * 100 * 0.6 + dividend_yield * 100 * 0.6 + bonus, 1))
    return {
        "Buyback Yield": buyback_yield,
        "Share Count Reduction %": share_reduction,
        "Dividend Yield": dividend_yield,
        "Total Shareholder Yield": shareholder_yield,
        "Return of Capital Score": roc_score,
    }
