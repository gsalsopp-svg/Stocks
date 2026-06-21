"""
modules/data_fetcher.py
-------------------------
Fetches company financials from Yahoo Finance (via yfinance) and maps them onto
the EXISTING CompanyFinancials data model. No other module needs to change:
calculations.py, valuation.py, scoring.py and recommendation.py all already
operate purely on a CompanyFinancials instance, regardless of where it came from.

Design notes:
- All currency figures on CompanyFinancials are in millions (matching the
  existing sample_data.py convention); per-share figures (price, EPS, book
  value/share) are NOT divided.
- yfinance's `.info` dict is tried first for each field; if a field is
  missing there, we fall back to the annual income statement / balance sheet
  / cash flow statement (row labels vary by ticker/version, so several
  candidate labels are tried for each line item).
- Anything that still can't be found defaults to 0.0 and is added to a
  `warnings` list returned alongside the company, so the UI can tell the
  user which fields they should sanity-check or fill in manually.
"""
import yfinance as yf

from .data_models import CompanyFinancials


class TickerLookupError(Exception):
    """Raised when a ticker can't be resolved or Yahoo Finance returns no usable price data."""


def _info_value(info: dict, *keys):
    """Return the first non-None value found in `info` for the given keys, else None."""
    for k in keys:
        v = info.get(k)
        if v is not None:
            return v
    return None


def _row_value(df, *row_names, col=0):
    """Pull a single value out of a yfinance financial-statement DataFrame, trying
    several possible row labels (these vary by ticker/version) at the given column
    index (0 = most recent annual period, 1 = the period before). Returns None if
    the statement, row or column isn't available.
    """
    if df is None or df.empty:
        return None
    for name in row_names:
        if name in df.index:
            try:
                val = df.loc[name].iloc[col]
            except (IndexError, KeyError):
                continue
            if val is None:
                continue
            try:
                fv = float(val)
            except (TypeError, ValueError):
                continue
            if fv == fv:  # filters out NaN
                return fv
    return None


def fetch_company_from_yahoo(ticker_symbol: str):
    """Fetch a company's financials from Yahoo Finance.

    Returns: (CompanyFinancials, warnings: list[str])
    Raises: TickerLookupError if the ticker can't be resolved at all.
    """
    ticker_symbol = (ticker_symbol or "").strip().upper()
    if not ticker_symbol:
        raise TickerLookupError("Please enter a ticker symbol.")

    warnings = []

    try:
        tk = yf.Ticker(ticker_symbol)
        info = tk.info or {}
    except Exception as e:
        raise TickerLookupError(f"Yahoo Finance lookup failed for '{ticker_symbol}': {e}")

    price = _info_value(info, "currentPrice", "regularMarketPrice", "previousClose")
    if price is None or not (info.get("symbol") or info.get("shortName") or info.get("longName")):
        raise TickerLookupError(
            f"'{ticker_symbol}' could not be found on Yahoo Finance. Check the symbol "
            f"(e.g. UK-listed shares need a suffix, such as 'BREE.L' for Breedon Group "
            f"or 'SIG.L' for Signature Aviation)."
        )

    # --- Annual financial statements (used as fallbacks + prior-year comparatives) ---
    income_stmt = balance_sheet = cashflow = None
    try:
        income_stmt = tk.income_stmt
    except Exception:
        warnings.append("income statement unavailable")
    try:
        balance_sheet = tk.balance_sheet
    except Exception:
        warnings.append("balance sheet unavailable")
    try:
        cashflow = tk.cashflow
    except Exception:
        warnings.append("cash flow statement unavailable")

    def m(value):
        """Convert an absolute currency value to millions; pass through None."""
        return None if value is None else value / 1e6

    # --- Shares & market cap ---
    shares_out = m(_info_value(info, "sharesOutstanding"))
    if shares_out is None:
        shares_out = m(_row_value(balance_sheet, "Share Issued", "Ordinary Shares Number"))
    if shares_out is None:
        shares_out = 0.0
        warnings.append("shares outstanding")

    market_cap = m(_info_value(info, "marketCap"))
    if market_cap is None and price and shares_out:
        market_cap = price * shares_out
    if market_cap is None:
        market_cap = 0.0
        warnings.append("market cap")

    # --- Income statement items ---
    revenue_ttm = m(_info_value(info, "totalRevenue"))
    if revenue_ttm is None:
        revenue_ttm = m(_row_value(income_stmt, "Total Revenue"))
    if revenue_ttm is None:
        revenue_ttm = 0.0
        warnings.append("revenue")

    gross_profit = m(_info_value(info, "grossProfits"))
    if gross_profit is None:
        gross_profit = m(_row_value(income_stmt, "Gross Profit"))
    if gross_profit is None:
        gross_profit = 0.0
        warnings.append("gross profit")

    operating_income = m(_row_value(income_stmt, "Operating Income"))
    if operating_income is None:
        op_margin = _info_value(info, "operatingMargins")
        operating_income = revenue_ttm * op_margin if op_margin is not None else None
    if operating_income is None:
        operating_income = 0.0
        warnings.append("operating income")

    ebitda = m(_info_value(info, "ebitda"))
    if ebitda is None:
        ebitda = m(_row_value(income_stmt, "EBITDA"))
    if ebitda is None:
        ebitda = 0.0
        warnings.append("EBITDA")

    net_income = m(_info_value(info, "netIncomeToCommon"))
    if net_income is None:
        net_income = m(_row_value(income_stmt, "Net Income"))
    if net_income is None:
        net_income = 0.0
        warnings.append("net income")

    sga = m(_row_value(income_stmt, "Selling General And Administration",
                        "Selling General And Administrative")) or 0.0
    rnd = m(_row_value(income_stmt, "Research And Development")) or 0.0

    # --- Cash flow ---
    fcf = m(_info_value(info, "freeCashflow"))
    if fcf is None:
        ocf = _row_value(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex = _row_value(cashflow, "Capital Expenditure")  # usually reported negative
        fcf = m(ocf + capex) if (ocf is not None and capex is not None) else None
    if fcf is None:
        fcf = 0.0
        warnings.append("free cash flow")

    dividends_paid = abs(_row_value(cashflow, "Cash Dividends Paid", "Common Stock Dividend Paid") or 0.0)
    dividends_paid = m(dividends_paid) or 0.0
    buybacks = abs(_row_value(cashflow, "Repurchase Of Capital Stock") or 0.0)
    buybacks = m(buybacks) or 0.0

    # --- Balance sheet ---
    cash = m(_info_value(info, "totalCash"))
    if cash is None:
        cash = m(_row_value(balance_sheet, "Cash And Cash Equivalents",
                             "Cash Cash Equivalents And Short Term Investments"))
    cash = cash or 0.0

    total_debt = m(_info_value(info, "totalDebt"))
    if total_debt is None:
        total_debt = m(_row_value(balance_sheet, "Total Debt"))
    total_debt = total_debt or 0.0

    book_value_per_share = _info_value(info, "bookValue")
    book_value = (book_value_per_share * shares_out) if book_value_per_share else None
    if not book_value:
        book_value = m(_row_value(balance_sheet, "Stockholders Equity", "Common Stock Equity",
                                   "Total Equity Gross Minority Interest"))
    if not book_value:
        book_value = 0.0
        warnings.append("book value / shareholders' equity")

    current_assets = m(_row_value(balance_sheet, "Current Assets")) or 0.0
    current_liabilities = m(_row_value(balance_sheet, "Current Liabilities")) or 0.0
    total_assets = m(_row_value(balance_sheet, "Total Assets"))
    if total_assets is None:
        total_assets = 0.0
        warnings.append("total assets")

    # --- Per-share items (NOT divided by 1e6) ---
    eps = _info_value(info, "trailingEps") or 0.0
    forward_eps = _info_value(info, "forwardEps")
    if forward_eps is None:
        forward_eps = eps

    # --- Enterprise value ---
    ev_reported = m(_info_value(info, "enterpriseValue"))
    if ev_reported is None:
        ev_reported = market_cap + total_debt - cash

    # --- Prior-year comparatives (column 1 = the period before the most recent) ---
    revenue_py = m(_row_value(income_stmt, "Total Revenue", col=1))
    net_income_py = m(_row_value(income_stmt, "Net Income", col=1))
    eps_py = _row_value(income_stmt, "Diluted EPS", "Basic EPS", col=1)
    ocf_py = _row_value(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities", col=1)
    capex_py = _row_value(cashflow, "Capital Expenditure", col=1)
    fcf_py = m(ocf_py + capex_py) if (ocf_py is not None and capex_py is not None) else None
    shares_out_py = m(_row_value(balance_sheet, "Share Issued", "Ordinary Shares Number", col=1))

    if revenue_py is None or net_income_py is None or fcf_py is None or eps_py is None:
        warnings.append("prior-year comparatives incomplete (growth metrics may read as 0% — "
                         "fill in manually on the sidebar if needed)")
    revenue_py = revenue_py if revenue_py is not None else revenue_ttm
    net_income_py = net_income_py if net_income_py is not None else net_income
    fcf_py = fcf_py if fcf_py is not None else fcf
    eps_py = eps_py if eps_py is not None else eps
    shares_out_py = shares_out_py if shares_out_py is not None else shares_out

    company = CompanyFinancials(
        name=info.get("shortName") or info.get("longName") or ticker_symbol,
        ticker=ticker_symbol,
        currency=info.get("currency", "USD"),
        sector_type="Standard",
        share_price=float(price),
        market_cap=market_cap,
        revenue_ttm=revenue_ttm,
        gross_profit=gross_profit,
        operating_income=operating_income,
        ebitda=ebitda,
        net_income=net_income,
        fcf=fcf,
        cash=cash,
        total_debt=total_debt,
        shares_out=shares_out,
        eps=eps,
        book_value=book_value,
        sga=sga,
        rnd=rnd,
        ev_reported=ev_reported,
        revenue_py=revenue_py,
        net_income_py=net_income_py,
        fcf_py=fcf_py,
        eps_py=eps_py,
        shares_out_py=shares_out_py,
        dividends_paid=dividends_paid,
        buybacks=buybacks,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        total_assets=total_assets,
        forward_eps=forward_eps,
        # Valuation assumptions, DCF assumptions and Hidden Asset Value fields are
        # intentionally left at their CompanyFinancials defaults: these are analyst
        # judgement calls, not data Yahoo Finance can supply, and remain editable
        # in the sidebar exactly as they were before this feature was added.
    )
    return company, warnings
