import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest
from analysis import ai_prompt, load_csv, quality_report
from portfolio import analyze_holdings, analyze_history


class AnalysisTests(unittest.TestCase):
    def test_csv_quality_and_prompt(self):
        frame = load_csv(b"category,value\na,1\nb,\na,1\n")
        report = quality_report(frame).set_index("Column")
        self.assertEqual(report.loc["value", "Missing"], 1)
        self.assertIn("stock portfolio analyzer", ai_prompt(frame, "Inspect totals"))

    def test_empty_and_invalid_csv(self):
        for content in [b"", b"a,b\n", b'a,b\n"unterminated,2']:
            with self.assertRaises(ValueError):
                load_csv(content)

    def test_holdings_weighted_lots(self):
        frame = load_csv(b"ticker,shares,average_cost,current_price\naaa,10,100,150\nAAA,20,125,150\n")
        position = analyze_holdings(frame).iloc[0]
        self.assertEqual(position.ticker, "AAA")
        self.assertEqual(position.shares, 30)
        self.assertEqual(position.cost_basis, 3500)
        self.assertEqual(position.market_value, 4500)
        self.assertEqual(position.unrealized_gain, 1000)
        self.assertAlmostEqual(position.average_cost, 3500 / 30)
        self.assertAlmostEqual(position.gain_pct, 1000 / 3500 * 100)

    def test_invalid_holdings(self):
        good = {"ticker": ["AAA"], "shares": [10], "average_cost": [100], "current_price": [150]}
        for column, value in [("shares", -1), ("shares", 0), ("average_cost", "bad"),
                              ("current_price", float("inf")), ("ticker", "")]:
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                analyze_holdings(pd.DataFrame({**good, column: [value]}))
        with self.assertRaises(ValueError):
            analyze_holdings(pd.DataFrame({"ticker": ["AAA"]}))

    def test_conflicting_prices(self):
        frame = load_csv(b"ticker,shares,average_cost,current_price\nAAA,10,100,150\nAAA,20,125,155\n")
        with self.assertRaisesRegex(ValueError, "Conflicting current_price"):
            analyze_holdings(frame)

    def test_zero_cost_and_previous_close(self):
        frame = load_csv(b"ticker,shares,average_cost,current_price,previous_close\nAAA,10,0,150,140\n")
        row = analyze_holdings(frame).iloc[0]
        self.assertTrue(pd.isna(row.gain_pct))
        self.assertEqual(row.daily_gain, 100)

    def test_history_returns_and_drawdown(self):
        frame = load_csv(b"date,ticker,close\n2025-01-03,AAA,90\n2025-01-01,AAA,100\n2025-01-02,AAA,120\n")
        prices, summary = analyze_history(frame)
        row = summary.iloc[0]
        self.assertAlmostEqual(row.price_change_pct, -10)
        self.assertAlmostEqual(row.max_drawdown_pct, -25)
        self.assertAlmostEqual(prices.indexed_price.iloc[-1], 90)
        self.assertAlmostEqual(row.volatility_per_observation_pct, pd.Series([20., -25.]).std())

    def test_history_invalid_and_insufficient_data(self):
        for csv in [b"date,ticker,close\nbad,AAA,100\n", b"date,ticker,close\n2025-01-01,AAA,0\n",
                    b"date,ticker,close\n2025-01-01,AAA,100\n2025-01-01,AAA,101\n"]:
            with self.assertRaises(ValueError):
                analyze_history(load_csv(csv))
        _, summary = analyze_history(load_csv(b"date,ticker,close\n2025-01-01,AAA,100\n"))
        self.assertTrue(pd.isna(summary.price_change_pct.iloc[0]))
        self.assertTrue(pd.isna(summary.volatility_per_observation_pct.iloc[0]))
        self.assertTrue(pd.isna(summary.max_drawdown_pct.iloc[0]))


class StreamlitTests(unittest.TestCase):
    def start(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)

    def test_holdings_startup_and_filter(self):
        app = self.start()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "USD 11,240.00")
        self.assertEqual(len(app.get("plotly_chart")), 3)
        app.multiselect[0].set_value(["AAPL"]).run()
        self.assertEqual(app.metric[0].value, "USD 3,500.00")
        self.assertEqual(len(app.exception), 0)
        app.multiselect[0].set_value([]).run()
        self.assertIn("No stocks selected", app.warning[0].value)
        self.assertEqual(len(app.exception), 0)

    def test_price_history(self):
        app = self.start()
        app.radio[0].set_value("Price history").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, "4")
        self.assertEqual(len(app.get("plotly_chart")), 3)
        app.multiselect[0].set_value(["AAPL"]).run()
        self.assertEqual(app.metric[0].value, "1")
        self.assertEqual(len(app.exception), 0)

    def test_mapping_and_validation(self):
        app = self.start()
        widget = next(w for w in app.selectbox if w.label == "Shares")
        widget.set_value("— Unmapped —").run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Map all required", app.info[0].value)
        widget.set_value("ticker").run()
        self.assertIn("different CSV column", app.error[0].value)

    def test_bad_input_displays_error(self):
        frame = load_csv(b"ticker,shares,average_cost,current_price\nAAA,-5,100,150\n")
        with patch("analysis.load_csv", return_value=frame):
            app = self.start()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("shares must", app.error[0].value)

    def test_single_history_observation(self):
        frame = load_csv(b"date,ticker,close\n2025-01-01,AAA,100\n")
        app = self.start()
        with patch("analysis.load_csv", return_value=frame):
            app.radio[0].set_value("Price history").run()
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
