"""Validated portfolio snapshot and price-history calculations."""
import numpy as np
import pandas as pd


def validate(frame, fields):
    missing = set(fields) - set(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    if frame.empty:
        raise ValueError("No data rows to analyze.")
    frame = frame.copy()
    if frame.ticker.isna().any() or frame.ticker.astype(str).str.strip().eq("").any():
        raise ValueError("Every row needs a ticker symbol.")
    frame["ticker"] = frame.ticker.astype(str).str.strip().str.upper()
    return frame


def numbers(frame, rules):
    for column, strictly_positive in rules.items():
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        valid = np.isfinite(frame[column]) & (frame[column] > 0 if strictly_positive else frame[column] >= 0)
        if not valid.all():
            rows = (np.flatnonzero(~valid) + 2).tolist()[:8]
            raise ValueError(f"{column} must contain finite {'positive' if strictly_positive else 'non-negative'} numbers. Check CSV row(s): {rows}.")


def analyze_holdings(frame):
    frame = validate(frame, ["ticker", "shares", "average_cost", "current_price"])
    rules = {"shares": True, "average_cost": False, "current_price": False}
    if "previous_close" in frame:
        rules["previous_close"] = False
    numbers(frame, rules)
    frame["sector"] = frame.get("sector", pd.Series("Unknown", index=frame.index)).fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    for ticker, group in frame.groupby("ticker"):
        for column in ["current_price", "sector"] + (["previous_close"] if "previous_close" in frame else []):
            if group[column].nunique() > 1:
                raise ValueError(f"Conflicting {column} values for {ticker}. Each stock must have one price and sector across its lots.")
    frame["cost_basis"] = frame.shares * frame.average_cost
    frame["market_value"] = frame.shares * frame.current_price
    aggregation = {"shares": "sum", "cost_basis": "sum", "market_value": "sum", "current_price": "first", "sector": "first"}
    if "previous_close" in frame:
        frame["daily_gain"] = frame.shares * (frame.current_price - frame.previous_close)
        aggregation["daily_gain"] = "sum"
    result = frame.groupby("ticker", as_index=False).agg(aggregation)
    if not np.isfinite(result.select_dtypes(include="number")).all().all():
        raise ValueError("Position values overflowed. Check shares and prices for unusually large values.")
    result["average_cost"] = result.cost_basis / result.shares
    result["unrealized_gain"] = result.market_value - result.cost_basis
    result["gain_pct"] = result.unrealized_gain / result.cost_basis.replace(0, np.nan) * 100
    return result


def analyze_history(frame):
    frame = validate(frame, ["date", "ticker", "close"])
    numbers(frame, {"close": True})
    frame["date"] = pd.to_datetime(frame.date, errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    if frame.date.isna().any():
        raise ValueError("Every history row needs a valid date, preferably YYYY-MM-DD.")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("Price history must contain one closing price per ticker per date. Remove duplicate dates.")
    frame = frame.sort_values(["ticker", "date"]).copy()
    groups = frame.groupby("ticker").close
    frame["price_change_pct"] = groups.pct_change(fill_method=None) * 100
    frame["indexed_price"] = frame.close / groups.transform("first") * 100
    frame["drawdown_pct"] = (frame.close / groups.cummax() - 1) * 100
    rows = []
    for ticker, group in frame.groupby("ticker"):
        rows.append({"ticker": ticker, "observations": len(group), "first_close": group.close.iloc[0],
                     "last_close": group.close.iloc[-1],
                     "price_change_pct": (group.close.iloc[-1] / group.close.iloc[0] - 1) * 100 if len(group) > 1 else np.nan,
                     "volatility_per_observation_pct": group.price_change_pct.std(),
                     "max_drawdown_pct": group.drawdown_pct.min() if len(group) > 1 else np.nan})
    return frame, pd.DataFrame(rows)
