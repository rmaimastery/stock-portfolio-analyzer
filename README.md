# Stock Portfolio Analyzer

A Python Streamlit application that analyzes uploaded stock CSVs with pandas and interactive Plotly charts. Choose **Portfolio holdings** or **Price history** in the sidebar. The sample files contain Apple (AAPL), Tesla (TSLA), Google (GOOGL), and Salesforce (CRM). Both modes include synthetic sample data, downloadable templates, column mapping, ticker filtering, data-quality reports, and CSV exports.

## Run

Requires Python 3.10 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. If the app is already running, refresh the browser after saving the changes.

## Holdings CSV

```csv
ticker,shares,average_cost,current_price,sector,previous_close
AAPL,20,150,175,Technology,173
TSLA,12,220,245,Consumer Discretionary,242
```

Required: `ticker`, `shares`, `average_cost` (purchase cost per share), `current_price`. Optional: `sector`, `previous_close`. Headers such as `Symbol`, `Quantity`, and `Purchase Price` are automatically recognized; map other names in the app.

- Market value = shares × current price.
- Invested cost = shares × average cost.
- Unrealized gain/loss = market value − invested cost.
- Gain vs. cost (%) = unrealized gain/loss ÷ invested cost × 100; undefined at zero cost.
- Allocation (%) = position market value ÷ selected portfolio market value × 100.
- Change vs. previous close = shares × (current price − previous close), when supplied.

Multiple lots of a stock are combined using share-weighted purchase cost. All lots must agree on current price, sector, and previous close (when mapped). Exact duplicate rows count as separate lots. Upload current open holdings, not transaction history or repeated dated snapshots. Shares must be positive, including fractional shares; prices and costs must be finite and non-negative. Invalid input is reported rather than silently dropped. Missing sectors appear as Unknown.

Includes holdings and sector allocation charts, gain/loss ranking, largest-position concentration, and an export of calculated positions. Sidebar filters recompute all metrics for the selected stocks.

## Price-history CSV

```csv
date,ticker,close
2025-01-02,AAPL,150
2025-01-03,AAPL,153
2025-01-06,AAPL,149
```

Required: `date`, `ticker`, `close`. Use YYYY-MM-DD dates and one positive, finite closing price per ticker per date. Duplicate ticker/date records are rejected. Upload multiple symbols in one file, or use a single symbol.

Displays closing prices, price growth indexed to 100, drawdowns, first-to-last price change, and observed volatility. Filter by ticker and date range. Calculations restart at the first observation in the selected range; symbols can have different coverage periods.

Volatility is the sample standard deviation of consecutive percentage price changes, per observation, without annualization. Maximum drawdown is the largest fall from a closing-price peak within the selected range. One observation cannot establish a return or maximum drawdown; at least two price changes are needed for sample volatility. Unadjusted closes can reflect stock splits and exclude dividends. Prefer consistently adjusted prices for historical comparisons where appropriate.

History mode analyzes individual stocks. It does not infer portfolio performance from price history alone, since holdings changes and cash flows are not supplied.

## Data and scope

The app uses prices from your CSV; it does not fetch live quotes. The supplied samples are synthetic demonstrations, not actual historical quotes. All monetary data in a file must use one currency. The display-currency selector labels amounts without performing conversion.

Snapshot gains exclude dividends, fees, taxes, and realized gains on sold positions. They are not annualized or time-weighted investment returns. The app supports long stock positions, not short positions, options, or multi-currency portfolios. Concentration statistics describe the supplied holdings rather than recommending trades.

Uploaded CSVs are processed in server memory and are not saved by this app. On a remote deployment, uploads go to that host. The upload limit is 25 MB.

## AI-assisted development

The AI workflow tab generates a local schema-based prompt for a coding assistant; it does not call an AI service. Example task: add a monthly aggregation selector for price charts. Give the assistant the prompt and relevant code, review its changes, and verify known calculations before accepting them. No raw position rows are included in the prompt, but column names and summary counts are included.

## Validation

```sh
python -m unittest discover -s tests -v
```

Tests cover weighted lots, gain/loss calculations, bad numbers, conflicting quotes, zero cost, historical price changes, drawdown, insufficient history, startup, both modes, column mapping, and empty ticker filters.

- `app.py`: Upload, mapping, filters, charts, insights, exports.
- `portfolio.py`: Validated financial calculations.
- `analysis.py`: CSV parsing, data quality, AI prompts.
- `data/sample_portfolio.csv` and `data/sample_prices.csv`: Synthetic templates.

References: [Streamlit API](https://docs.streamlit.io/develop/api-reference), [SEC guide to brokerage statements](https://www.investor.gov/better-understanding-your-brokerage-account-statement), and [asset allocation](https://www.investor.gov/introduction-investing/getting-started/asset-allocation).
