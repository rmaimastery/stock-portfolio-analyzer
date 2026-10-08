"""Run with: streamlit run app.py."""
from pathlib import Path
import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import load_csv, quality_report, ai_prompt
from portfolio import analyze_holdings, analyze_history

ROOT = Path(__file__).parent
st.set_page_config(page_title="Stock Portfolio Analyzer", page_icon="📈", layout="wide")
st.title("Stock Portfolio Analyzer")
st.caption("Upload your stocks · Understand your holdings · Explore price history")

with st.sidebar:
    st.header("Stock data")
    mode = st.radio("Dataset type", ["Portfolio holdings", "Price history"])
    uploaded = st.file_uploader("Upload stock CSV", type=["csv"])
    currency = st.selectbox("Display currency", ["USD", "INR", "EUR", "GBP", "Other"])
    st.caption("Use one currency per file. This label does not convert currencies.")
    with st.expander("CSV options"):
        sep = st.selectbox("Delimiter", [",", ";", "\t", "|"])
        encoding = st.selectbox("Encoding", ["utf-8", "utf-8-sig", "latin-1"])

is_holdings = mode == "Portfolio holdings"
sample_path = ROOT / "data" / ("sample_portfolio.csv" if is_holdings else "sample_prices.csv")
content = uploaded.getvalue() if uploaded else sample_path.read_bytes()
key = hashlib.sha256(content + mode.encode() + sep.encode() + encoding.encode()).hexdigest()[:12]
with st.sidebar:
    st.download_button("Download sample CSV", sample_path.read_bytes(), sample_path.name, "text/csv")
    st.caption("No upload? The synthetic sample is shown automatically.")
try:
    raw = load_csv(content, sep, encoding)
except (ValueError, UnicodeError, pd.errors.ParserError) as error:
    st.error(f"Could not read the CSV: {error}")
    st.info("Check the header, data rows, delimiter, and encoding.")
    st.stop()

st.caption(f"Source: {uploaded.name if uploaded else 'Synthetic demonstration data — not live market prices'}")
fields = ["ticker", "shares", "average_cost", "current_price"] if is_holdings else ["date", "ticker", "close"]
aliases = {"ticker": ["ticker", "symbol", "stock"], "shares": ["shares", "quantity", "qty"],
           "average_cost": ["average_cost", "avg_cost", "purchase_price", "buy_price"],
           "current_price": ["current_price", "market_price", "price", "close"],
           "date": ["date", "timestamp"], "close": ["close", "adj_close", "adjusted_close", "price"],
           "sector": ["sector"], "previous_close": ["previous_close", "prev_close"]}
headers = {str(c).strip().lower().replace(" ", "_"): c for c in raw.columns}
mapping = {}
with st.expander("Map your CSV columns", expanded=uploaded is not None):
    st.caption("Average cost is purchase cost per share. Holdings rows represent open positions or separate lots, not dated snapshots or trades.")
    optional = ["sector", "previous_close"] if is_holdings else []
    cols = st.columns(3)
    for index, field in enumerate(fields + optional):
        options = ["— Unmapped —"] + list(raw.columns)
        default = next((headers[a] for a in aliases[field] if a in headers), options[0])
        with cols[index % 3]:
            selected = st.selectbox(field.replace("_", " ").title() + (" (optional)" if field in optional else ""),
                                    options, index=options.index(default), key=f"{key}_{field}")
            if selected != options[0]:
                mapping[field] = selected
if any(field not in mapping for field in fields):
    st.info("Map all required columns above to analyze this CSV.")
    st.dataframe(raw.head(20), width="stretch", hide_index=True)
    st.stop()
if len(set(mapping.values())) != len(mapping):
    st.error("Each field must use a different CSV column.")
    st.stop()
mapped = pd.DataFrame({field: raw[column] for field, column in mapping.items()})
try:
    if is_holdings:
        all_positions = analyze_holdings(mapped)
    else:
        prices, all_summary = analyze_history(mapped)
except ValueError as error:
    st.error(str(error))
    st.stop()

tickers = sorted(all_positions.ticker.tolist() if is_holdings else all_summary.ticker.tolist())
with st.sidebar:
    selected_tickers = st.multiselect("Stocks in view", tickers, default=tickers, key=f"tickers_{key}")
if not selected_tickers:
    st.warning("No stocks selected. Select at least one ticker in the sidebar.")
    st.stop()


def money(value):
    return f"{currency} {value:,.2f}"


def chart(figure):
    figure.update_layout(template="plotly_white", height=430, margin=dict(l=20, r=20, t=35, b=20))
    st.plotly_chart(figure, width="stretch")


if is_holdings:
    positions = all_positions[all_positions.ticker.isin(selected_tickers)].copy()
    value, cost = positions.market_value.sum(), positions.cost_basis.sum()
    gain = value - cost
    positions["weight_pct"] = positions.market_value / value * 100 if value > 0 else 0.0
    a, b, c, d = st.columns(4)
    a.metric("Portfolio value", money(value))
    b.metric("Invested cost", money(cost))
    c.metric("Unrealized gain / loss", money(gain), f"{gain / cost * 100:+.2f}%" if cost > 0 else "N/A: zero cost")
    d.metric("Stocks held", len(positions))
    st.caption("Metrics reflect selected stocks and uploaded prices. Gain percentages compare price value with purchase cost; they exclude dividends, fees, taxes, and sold positions.")
    overview, allocation, insights, data, ai = st.tabs(["Holdings", "Allocation", "Portfolio insights", "Uploaded data", "AI workflow"])
    with overview:
        st.subheader("Your positions")
        st.dataframe(positions, width="stretch", hide_index=True)
        st.download_button("Download portfolio analysis", positions.to_csv(index=False).encode(), "portfolio_analysis.csv", "text/csv")
        chart(px.bar(positions.sort_values("unrealized_gain"), x="ticker", y="unrealized_gain",
                     color="unrealized_gain", color_continuous_scale="RdYlGn", title="Unrealized gain / loss by stock"))
        if "daily_gain" in positions:
            st.metric("Change vs. previous close", money(positions.daily_gain.sum()))
            st.caption("Shares × (current price − previous close), using the prices supplied in your file.")
    with allocation:
        if value > 0:
            left, right = st.columns(2)
            with left:
                chart(px.pie(positions, names="ticker", values="market_value", hole=.55, title="Stock allocation"))
            with right:
                sectors = positions.groupby("sector", as_index=False).market_value.sum()
                chart(px.bar(sectors, x="sector", y="market_value", title="Sector allocation"))
        else:
            st.info("Allocation charts need a positive total market value.")
    with insights:
        st.subheader("Portfolio snapshot")
        largest = positions.loc[positions.market_value.idxmax()]
        st.write(f"Largest position: **{largest.ticker}**, accounting for **{largest.weight_pct:.1f}%** of selected portfolio value.")
        st.write(f"**{int((positions.unrealized_gain > 0).sum())}** stocks above purchase cost · **{int((positions.unrealized_gain < 0).sum())}** below cost · **{int((positions.unrealized_gain == 0).sum())}** unchanged.")
        ranked = positions.dropna(subset=["gain_pct"])
        if not ranked.empty:
            best = ranked.loc[ranked.gain_pct.idxmax()]
            worst = ranked.loc[ranked.gain_pct.idxmin()]
            st.write(f"Highest gain vs. cost: **{best.ticker} ({best.gain_pct:+.2f}%)**. Lowest: **{worst.ticker} ({worst.gain_pct:+.2f}%)**.")
        st.caption("This snapshot measures concentration and unrealized gains. Upload price history to examine observed volatility and drawdowns.")
    prompt_frame = positions
else:
    view = prices[prices.ticker.isin(selected_tickers)].copy()
    with st.sidebar:
        dates = st.date_input("History date range", (view.date.min().date(), view.date.max().date()),
                              min_value=view.date.min().date(), max_value=view.date.max().date(), key=f"dates_{key}")
    if len(dates) != 2:
        st.info("Select both a start and end date.")
        st.stop()
    view = view[view.date.dt.date.between(*dates)]
    if view.empty:
        st.warning("No prices in this date range.")
        st.stop()
    view, summary = analyze_history(view)
    a, b, c = st.columns(3)
    a.metric("Stocks in range", summary.ticker.nunique())
    b.metric("Price observations", len(view))
    c.metric("Date range", f"{view.date.min():%b %d, %Y} – {view.date.max():%b %d, %Y}")
    overview, insights, data, ai = st.tabs(["Price charts", "History statistics", "Uploaded data", "AI workflow"])
    with overview:
        chart(px.line(view, x="date", y="close", color="ticker", title=f"Closing prices ({currency})"))
        chart(px.line(view, x="date", y="indexed_price", color="ticker", title="Price growth · First observation = 100"))
        chart(px.line(view, x="date", y="drawdown_pct", color="ticker", title="Drawdown from observed price peak (%)"))
    with insights:
        st.subheader("Statistics for the selected period")
        st.dataframe(summary, width="stretch", hide_index=True)
        st.caption("Price change uses first and last observed closes. Volatility is sample standard deviation of successive price changes, expressed as a percentage per observation; it is not annualized. Maximum drawdown is the largest decline from an observed closing-price peak. One observation cannot establish a return; volatility requires at least two price changes.")
        st.caption("Unadjusted prices can reflect splits and exclude dividends. Observations may be irregularly spaced. This is individual stock price analysis; portfolio returns require holdings and cash-flow history.")
        st.download_button("Download history statistics", summary.to_csv(index=False).encode(), "stock_history_analysis.csv", "text/csv")
    prompt_frame = summary

with data:
    st.subheader("Original CSV")
    st.dataframe(raw, width="stretch", hide_index=True)
    st.dataframe(quality_report(raw), width="stretch", hide_index=True)
    if is_holdings:
        st.caption("Exact duplicate holdings rows are counted as separate lots. Verify that your file contains only current open holdings.")
with ai:
    st.subheader("Extend your analyzer with AI")
    goal = st.text_area("Analysis goal", "Add a comparison of stock allocation and observed price changes.")
    st.code(ai_prompt(prompt_frame, goal), language="text")
    st.caption("Prompts are created locally and contain schema and counts, not raw positions. No AI service is called. Review generated code and verify calculations against your CSV.")
