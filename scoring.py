"""
modules/scoring.py
-------------------
The 100-point value-investing scoring framework: 25 points each for
Valuation, Quality, Growth and Balance Sheet Strength.
"""
from .data_models import CompanyFinancials
from .calculations import valuation_ratios, quality_metrics, balance_sheet_strength
from .industry_profiles import get_override


def _tier(value, breakpoints, reverse=False, default=0.0, none_score=0.0):
    """breakpoints: list of (threshold, score), evaluated in order.
    reverse=False -> higher value is better, breakpoints sorted descending by threshold,
                      first breakpoint where value >= threshold wins.
    reverse=True  -> lower value is better, breakpoints sorted ascending by threshold,
                      first breakpoint where value <= threshold wins.
    """
    if value is None:
        return none_score
    if reverse:
        for threshold, score in breakpoints:
            if value <= threshold:
                return score
    else:
        for threshold, score in breakpoints:
            if value >= threshold:
                return score
    return default


def valuation_score(c: CompanyFinancials) -> dict:
    r = valuation_ratios(c)
    industry = getattr(c, "industry", "Other")
    pe_tiers = get_override(industry, "pe_tiers", [(10, 7), (15, 5.5), (20, 4), (25, 2.5), (35, 1)])
    ev_ebitda_tiers = get_override(industry, "ev_ebitda_tiers", [(6, 6), (9, 4.5), (12, 3), (16, 1.5)])
    ps_tiers = get_override(industry, "ps_tiers", [(1, 6), (2, 4.5), (3, 3), (5, 1.5)])
    fcf_yield_tiers = get_override(industry, "fcf_yield_tiers", [(0.08, 6), (0.05, 4.5), (0.03, 3), (0.01, 1.5)])
    pe_score = _tier(r["P/E Ratio"], pe_tiers, reverse=True, none_score=2)
    ev_ebitda_score = _tier(r["EV / EBITDA"], ev_ebitda_tiers, reverse=True, none_score=1.5)
    ps_score = _tier(r["Price / Sales"], ps_tiers, reverse=True, none_score=1.5)
    fcf_yield_score = _tier(r["FCF Yield"], fcf_yield_tiers, reverse=False, none_score=0)
    total = pe_score + ev_ebitda_score + ps_score + fcf_yield_score
    return {"P/E": pe_score, "EV/EBITDA": ev_ebitda_score, "Price/Sales": ps_score,
            "FCF Yield": fcf_yield_score, "total": total}


def quality_score(c: CompanyFinancials) -> dict:
    q = quality_metrics(c)
    gm = _tier(q["Gross Margin"], [(0.5, 5), (0.35, 4), (0.2, 3), (0.1, 1.5)], none_score=0.5, default=0.5)
    om = _tier(q["Operating Margin"], [(0.15, 5), (0.1, 4), (0.05, 3), (0.02, 1.5)], none_score=0.5, default=0.5)
    nm = _tier(q["Net Margin"], [(0.15, 5), (0.1, 4), (0.05, 3), (0.02, 1.5)], none_score=0.5, default=0.5)
    roe = _tier(q["ROE"], [(0.2, 5), (0.15, 4), (0.1, 3), (0.05, 1.5)], none_score=0.5, default=0.5)
    roic = _tier(q["ROIC"], [(0.15, 5), (0.1, 4), (0.07, 3), (0.04, 1.5)], none_score=0.5, default=0.5)
    total = gm + om + nm + roe + roic
    return {"Gross Margin": gm, "Operating Margin": om, "Net Margin": nm,
            "ROE": roe, "ROIC": roic, "total": total}


def growth_score(c: CompanyFinancials) -> dict:
    q = quality_metrics(c)
    rev = _tier(q["Revenue Growth"], [(0.15, 9), (0.08, 7), (0.04, 5), (0, 3)], none_score=0, default=0)
    eps = _tier(q["Earnings Growth"], [(0.15, 9), (0.08, 7), (0.04, 5), (0, 3)], none_score=0, default=0)
    fcf = _tier(q["FCF Growth"], [(0.15, 7), (0.08, 5.5), (0.04, 4), (0, 2)], none_score=0, default=0)
    total = rev + eps + fcf
    return {"Revenue Growth": rev, "EPS Growth": eps, "FCF Growth": fcf, "total": total}


def balance_sheet_score(c: CompanyFinancials) -> dict:
    b = balance_sheet_strength(c)
    industry = getattr(c, "industry", "Other")
    net_cash_tiers = get_override(industry, "net_cash_tiers", [(0.1, 10), (0, 7), (-0.2, 4), (-0.5, 2)])
    de_tiers = get_override(industry, "de_tiers", [(0.3, 8), (0.6, 6), (1.0, 4), (2.0, 2)])
    cr_tiers = get_override(industry, "current_ratio_tiers", [(2.0, 7), (1.5, 5.5), (1.2, 4), (1.0, 2)])
    net_cash_score = _tier(b["Net Cash / Market Cap"], net_cash_tiers, none_score=0, default=0)
    de_score = _tier(b["Debt / Equity"], de_tiers, reverse=True, none_score=0, default=0)
    cr_score = _tier(b["Current Ratio"], cr_tiers, none_score=0, default=0)
    total = net_cash_score + de_score + cr_score
    return {"Net Cash %": net_cash_score, "Debt/Equity": de_score, "Current Ratio": cr_score, "total": total}


def total_score(c: CompanyFinancials) -> dict:
    v = valuation_score(c)
    q = quality_score(c)
    g = growth_score(c)
    b = balance_sheet_score(c)
    total = v["total"] + q["total"] + g["total"] + b["total"]
    if total >= 90:
        rating = "Exceptional"
    elif total >= 80:
        rating = "Excellent"
    elif total >= 70:
        rating = "Good"
    elif total >= 60:
        rating = "Average"
    else:
        rating = "High Risk"
    return {
        "valuation": v, "quality": q, "growth": g, "balance_sheet": b,
        "total": total, "rating": rating,
    }
