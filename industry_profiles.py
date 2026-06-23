"""
modules/industry_profiles.py
------------------------------
Defines the fixed list of selectable industries, a best-effort mapping from
Yahoo Finance's own sector/industry strings onto that list (used to
auto-populate the Industry dropdown when a ticker is loaded), and a set of
per-industry overrides that nudge a handful of valuation assumptions and
scoring thresholds — e.g. utilities and renewables are allowed materially
higher leverage before the Balance Sheet score penalises them, since that's
normal for regulated/project-financed businesses; investment/financial
companies are flagged so Price/Book is treated as the primary lens rather
than EV/EBITDA, which doesn't mean much for a bank.

Anything not covered by an override simply falls back to the existing
generic tiers already in modules/scoring.py — "Other" (and any
unrecognised industry) behaves exactly as the app did before this feature.
"""

INDUSTRIES = [
    "Other",
    "Technology",
    "Healthcare",
    "Retail",
    "Consumer Staples",
    "Industrials",
    "Materials",
    "Energy",
    "Utilities",
    "Renewables / Clean Energy",
    "Real Estate (REIT)",
    "Investment / Financials",
    "Telecom",
]

# Best-effort map from Yahoo Finance's `info['sector']` (GICS-style, fixed set
# of strings) onto our list. `info['industry']` (a finer-grained string) is
# checked afterwards for a few keyword overrides (e.g. renewables).
YAHOO_SECTOR_MAP = {
    "Technology": "Technology",
    "Healthcare": "Healthcare",
    "Financial Services": "Investment / Financials",
    "Consumer Cyclical": "Retail",
    "Industrials": "Industrials",
    "Communication Services": "Telecom",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Basic Materials": "Materials",
    "Real Estate": "Real Estate (REIT)",
    "Utilities": "Utilities",
}

_RENEWABLE_KEYWORDS = ("renewable", "solar", "wind", "clean energy", "green energy")


def map_yahoo_sector_to_industry(sector: str, industry_detail: str = "") -> str:
    """Best-effort mapping from Yahoo's sector/industry strings to our fixed list.
    Falls back to 'Other' if nothing matches — deliberately the lightest-touch
    default, since a wrong specific guess is worse than a neutral one.
    """
    detail = (industry_detail or "").lower()
    if any(kw in detail for kw in _RENEWABLE_KEYWORDS):
        return "Renewables / Clean Energy"
    return YAHOO_SECTOR_MAP.get(sector or "", "Other")


# Per-industry overrides. Every key is optional — only the metrics that
# genuinely behave differently for that industry are overridden; everything
# else falls back to the generic tiers already in scoring.py.
#
#   de_tiers / current_ratio_tiers / net_cash_tiers: same (threshold, points)
#     tier format already used in scoring.py.
#   pe_tiers / ev_ebitda_tiers / ps_tiers / fcf_yield_tiers: same idea, for
#     the Valuation score.
#   discount_rate_adj: added to the DCF discount rate the fetcher anchors by default.
#   growth_haircut: multiplier applied to the fetcher's default DCF growth assumptions.
#   pb_focus: informational flag surfaced in the UI — for these industries,
#     Price/Book is generally more meaningful than EV/EBITDA.
INDUSTRY_OVERRIDES = {
    "Utilities": {
        "de_tiers": [(1.0, 8), (1.5, 6), (2.5, 4), (4.0, 2)],
        "current_ratio_tiers": [(1.0, 7), (0.8, 5.5), (0.6, 4), (0.4, 2)],
        "discount_rate_adj": -0.01,
        "growth_haircut": 0.5,
    },
    "Renewables / Clean Energy": {
        "de_tiers": [(1.2, 8), (2.0, 6), (3.0, 4), (4.5, 2)],
        "current_ratio_tiers": [(1.2, 7), (1.0, 5.5), (0.8, 4), (0.5, 2)],
        "discount_rate_adj": 0.005,
    },
    "Retail": {
        "ps_tiers": [(0.5, 6), (1.0, 4.5), (2.0, 3), (3.5, 1.5)],
        "current_ratio_tiers": [(1.5, 7), (1.2, 5.5), (1.0, 4), (0.8, 2)],
    },
    "Investment / Financials": {
        "de_tiers": [(2.0, 8), (4.0, 6), (6.0, 4), (10.0, 2)],
        "pb_focus": True,
    },
    "Technology": {
        "pe_tiers": [(20, 7), (30, 5.5), (40, 4), (60, 2.5)],
        "ps_tiers": [(3, 6), (6, 4.5), (10, 3), (15, 1.5)],
    },
    "Materials": {
        "de_tiers": [(0.5, 8), (1.0, 6), (1.5, 4), (2.5, 2)],
    },
    "Real Estate (REIT)": {
        "de_tiers": [(1.5, 8), (2.5, 6), (4.0, 4), (6.0, 2)],
        "pb_focus": True,
    },
    "Energy": {
        "de_tiers": [(0.6, 8), (1.2, 6), (2.0, 4), (3.0, 2)],
    },
    "Telecom": {
        "de_tiers": [(1.0, 8), (2.0, 6), (3.0, 4), (4.5, 2)],
    },
    # Healthcare, Industrials, Consumer Staples, Other: no override —
    # use the generic tiers already in scoring.py.
}


def get_override(industry: str, key: str, default=None):
    return INDUSTRY_OVERRIDES.get(industry, {}).get(key, default)
