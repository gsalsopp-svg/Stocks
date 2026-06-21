"""
modules/recommendation.py
---------------------------
Auto-generates Bull Case / Bear Case / Key Risks / Investment Thesis / Final
Rating from the computed metrics, scores and valuation outputs.
"""
from .data_models import CompanyFinancials
from .calculations import valuation_ratios, quality_metrics, balance_sheet_strength, capital_allocation
from .valuation import all_methods, hidden_asset_value
from .scoring import total_score


def final_rating(score: float, upside: float) -> str:
    if score >= 80 and upside >= 0.20:
        return "Strong Buy"
    if score >= 70 and upside >= 0.10:
        return "Buy"
    if score >= 55 and upside >= -0.10:
        return "Hold"
    if score >= 45:
        return "Sell"
    return "Strong Sell"


def bull_case(c: CompanyFinancials, ratios, quality, bs, ca, methods, ha, upside_reported) -> list:
    points = []
    if (bs["Net Cash / Market Cap"] or 0) >= 0.10:
        points.append(f"Fortress balance sheet: net cash equals {bs['Net Cash / Market Cap']*100:.1f}% "
                       f"of market cap, providing downside protection and optionality.")
    if (ratios["FCF Yield"] or 0) >= 0.05:
        points.append(f"FCF yield of {ratios['FCF Yield']*100:.1f}% comfortably exceeds typical "
                       f"long-term bond yields.")
    if (quality["Revenue Growth"] or 0) >= 0.04:
        points.append(f"Revenue growing at {quality['Revenue Growth']*100:.1f}% YoY, expanding the "
                       f"long-term opportunity.")
    if (quality["ROIC"] or 0) >= 0.08:
        points.append(f"ROIC of {quality['ROIC']*100:.1f}% indicates the business compounds capital efficiently.")
    if upside_reported >= 0.15:
        points.append(f"Trading at a {upside_reported*100:.1f}% discount to the average of five "
                       f"independent fair-value methods.")
    if ha["total"] > 0:
        points.append(f"Hidden/under-appreciated assets (land, reserves, investments, tax assets) "
                       f"add an estimated {ha['per_share']:.2f} per share not fully reflected in reported fair value.")
    if ca["Return of Capital Score"] >= 5:
        points.append(f"Management actively returns capital via buybacks and/or dividends "
                       f"(Return of Capital score {ca['Return of Capital Score']:.1f}/10).")
    return points


def bear_case(c: CompanyFinancials, ratios, quality, bs) -> list:
    points = []
    if ratios["P/E Ratio"] and ratios["P/E Ratio"] > 25:
        points.append(f"P/E of {ratios['P/E Ratio']:.1f}x is elevated versus historical value-investing norms.")
    if (bs["Net Cash / Market Cap"] or 0) < 0:
        points.append(f"Net debt position ({bs['Net Cash / Market Cap']*100:.1f}% of market cap) "
                       f"reduces balance-sheet flexibility.")
    if (quality["Revenue Growth"] or 0) < 0:
        points.append(f"Revenue declined {-quality['Revenue Growth']*100:.1f}% YoY — confirm this is "
                       f"not a structural, permanent decline.")
    if (quality["Net Margin"] or 0) < 0.05:
        points.append(f"Net margin of {(quality['Net Margin'] or 0)*100:.1f}% is thin, leaving little "
                       f"room for cost or pricing shocks.")
    if bs["Debt / Equity"] and bs["Debt / Equity"] > 1:
        points.append(f"Debt/Equity of {bs['Debt / Equity']:.2f}x is high; refinancing or rate risk "
                       f"should be reviewed.")
    if c.net_income > c.fcf * 1.5 and c.fcf > 0:
        points.append("Net income running well ahead of free cash flow — check for non-cash or "
                       "one-off items inflating reported earnings.")
    return points


def key_risks(c: CompanyFinancials) -> list:
    points = [
        "Valuation inputs and assumptions (target multiples, growth rates, WACC) are analyst "
        "judgement calls — stress-test them before relying on the output.",
        "Hidden Asset Value figures are manual estimates and should be backed by independent "
        "appraisal, reserve reports or comparable transactions.",
    ]
    if c.sector_type != "Standard":
        points.append(f"This company has been flagged as {c.sector_type} — apply the relevant "
                       f"special-handling section (cash-rich split / cyclical normalisation / "
                       f"asset-heavy replacement value) rather than relying on headline multiples alone.")
    if c.rnd == 0:
        points.append("Limited disclosed R&D; confirm whether intangible/competitive moats are "
                       "being correctly captured in margins and growth assumptions.")
    points.append("All figures are illustrative as of the data entry date and should be refreshed "
                   "against the latest filings before any real investment decision.")
    return points


def investment_thesis(c: CompanyFinancials, score: float, rating: str,
                       fv_reported: float, fv_adjusted: float,
                       upside_reported: float, upside_adjusted: float) -> str:
    return (
        f"At a price of {c.share_price:.2f}, {c.name} scores {score:.1f}/100 ({rating}) on the "
        f"value-investing framework, with an average reported fair value of {fv_reported:.2f} "
        f"({upside_reported*100:.1f}% vs. current price) and an adjusted fair value (including hidden "
        f"assets) of {fv_adjusted:.2f} ({upside_adjusted*100:.1f}%). The case rests on weighing the "
        f"Bull Case and Bear Case against your own required margin of safety — this model favours "
        f"buying with a meaningful discount to fair value, a durable competitive position (Quality "
        f"score), and a balance sheet (Financial Strength score) that can survive a downturn."
    )


def build_recommendation(c: CompanyFinancials) -> dict:
    ratios = valuation_ratios(c)
    quality = quality_metrics(c)
    bs = balance_sheet_strength(c)
    ca = capital_allocation(c)
    methods = all_methods(c)
    ha = hidden_asset_value(c)
    scores = total_score(c)

    fv_reported = methods["average_fair_value"]
    fv_adjusted = fv_reported + ha["per_share"]
    upside_reported = (fv_reported / c.share_price - 1) if c.share_price else 0
    upside_adjusted = (fv_adjusted / c.share_price - 1) if c.share_price else 0

    rating = final_rating(scores["total"], upside_reported)

    return {
        "scores": scores,
        "ratios": ratios,
        "quality": quality,
        "balance_sheet": bs,
        "capital_allocation": ca,
        "methods": methods,
        "hidden_assets": ha,
        "fair_value_reported": fv_reported,
        "fair_value_adjusted": fv_adjusted,
        "upside_reported": upside_reported,
        "upside_adjusted": upside_adjusted,
        "final_rating": rating,
        "bull_case": bull_case(c, ratios, quality, bs, ca, methods, ha, upside_reported),
        "bear_case": bear_case(c, ratios, quality, bs),
        "key_risks": key_risks(c),
        "thesis": investment_thesis(c, scores["total"], scores["rating"], fv_reported,
                                     fv_adjusted, upside_reported, upside_adjusted),
    }
