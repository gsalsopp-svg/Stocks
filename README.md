# Value Investing Valuation Tool (Streamlit)

A professional fundamental-analysis tool for long-term value investors. Evaluate any
publicly traded company: enter its raw financials, get valuation ratios, quality and
balance-sheet metrics, five independent fair-value estimates (P/E, FCF multiple,
EV/EBITDA, Graham Formula, 10-year DCF), a 100-point scoring framework, a radar chart,
and an auto-generated Bull Case / Bear Case / Key Risks / Investment Thesis / Final Rating.

This is the Python/Streamlit counterpart to the companion Excel workbook
(`valuation_model.xlsx`) — same methodology, same scoring rules, same special handling
for cash-rich, cyclical and asset-heavy businesses.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project layout

```
app.py                      Streamlit UI — sidebar inputs, tabs for every output section
sample_data.py               GameStop & Breedon Group worked examples + a blank template
modules/
  data_models.py             CompanyFinancials dataclass — every raw input field
  calculations.py             Valuation Ratios / Quality / Balance Sheet / Capital Allocation
  valuation.py                The 5 fair-value methods + 10-year DCF + hidden-asset/cash-rich/
                               asset-heavy special handling
  scoring.py                   100-point Valuation/Quality/Growth/Balance-Sheet scoring framework
  recommendation.py            Auto-generated Bull Case / Bear Case / Key Risks / Thesis / Rating
```

## Using it for a new company

1. In the sidebar, choose **Custom / Blank Template**.
2. Fill in the company's financials (10-K/annual report, investor relations site, or a
   financial data aggregator) in the expandable sidebar sections.
3. Adjust the valuation assumptions (target multiples, growth rates, WACC) to your own
   view of the business.
4. If relevant, fill in the Hidden Asset Value section (land, mineral reserves, real
   estate, excess cash, tax assets, investment holdings, major capex) and flag the
   "Special handling type" as Cash-Rich, Cyclical or Asset-Heavy if applicable.

## Disclaimer

Educational/analytical tool, not investment advice. The GameStop and Breedon Group
sample figures are approximate, illustrative figures as of ~June 2026 — verify against
the latest filings before making any real investment decision.
