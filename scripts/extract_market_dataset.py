"""
Extract monthly market snapshots from portbench.csv for the website Dataset Explorer.
Outputs: static/data/market_dataset.json
"""
import json, os, sys, math, re
import pandas as pd
import numpy as np

CSV_PATH = r"d:\GitHub\portbench\datasets\processed\portbench.csv"
OUT_PATH = r"d:\GitHub\portbench.github.io\static\data\market_dataset.json"

TICKERS = {
    "Equities":    ["SPY", "QQQ", "XLE", "XLF", "IWM"],
    "Bonds":       ["TLT", "IEF", "LQD", "HYG", "SHY"],
    "Commodities": ["GLD", "SLV", "USO", "DBC", "PDBC"],
    "Crypto":      ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD"],
    "Real Estate": ["VNQ", "IYR", "XLRE", "ITB", "MORT"],
    "Cash":        ["BIL", "SGOV", "SHV", "ICSH", "CSHI"],
}

ASSET_CLASS_PREFIX = {
    "SPY":"equities","QQQ":"equities","XLE":"equities","XLF":"equities","IWM":"equities",
    "TLT":"bonds","IEF":"bonds","LQD":"bonds","HYG":"bonds","SHY":"bonds",
    "GLD":"commodities","SLV":"commodities","USO":"commodities","DBC":"commodities","PDBC":"commodities",
    "BTC-USD":"cryptocurrency","ETH-USD":"cryptocurrency","SOL-USD":"cryptocurrency",
    "XRP-USD":"cryptocurrency","ADA-USD":"cryptocurrency",
    "VNQ":"real_estate","IYR":"real_estate","XLRE":"real_estate","ITB":"real_estate","MORT":"real_estate",
    "BIL":"cash","SGOV":"cash","SHV":"cash","ICSH":"cash","CSHI":"cash",
}

MACRO_COLS = {
    "fed_funds_rate": "cash_fred_FEDFUNDS",
    "vix":            "equities_^VIX_close",
    "unemployment":   "cash_fred_UNRATE",
    "t10y2y_spread":  "bonds_fred_T10Y2Y",
    "breakeven_10y":  "bonds_fred_T10YIE",
    "hy_oas":         "bonds_fred_BAMLH0A0HYM2",
    "ted_spread":     "bonds_fred_TEDRATE",
    "mortgage_30y":   "bonds_fred_MORTGAGE30US",
    "cpi_yoy":        "cash_fred_CPIAUCSL",
    "ig_oas":         "bonds_fred_BAMLC0A0CM",
    "sofr":           "cash_fred_SOFR",
}

def get_col(df, ticker, field):
    prefix = ASSET_CLASS_PREFIX.get(ticker, "equities")
    col = "%s_%s_%s" % (prefix, ticker.replace("-", "_"), field)
    return col if col in df.columns else None

def annualized_vol(series, trading_days=252):
    r = series.pct_change().dropna()
    if len(r) < 5:
        return None
    return float(r.std() * np.sqrt(trading_days))

def classify_regime(ret_60d):
    if ret_60d is None:
        return "sideways"
    if ret_60d > 0.05:
        return "bull"
    if ret_60d < -0.05:
        return "bear"
    return "sideways"

def extract_news_snippets(raw_json_str, source_label):
    """Parse the newstext JSON and return a list of {source, text} dicts.
    text_field can be: (A) a JSON array of headlines, (B) a plain long article string."""
    snippets = []
    try:
        items = json.loads(raw_json_str)
    except Exception:
        return snippets
    if not isinstance(items, list):
        items = [items]
    for item in items:
        if not isinstance(item, dict):
            continue
        text_field = item.get("text", "")
        if not text_field:
            continue
        headlines = []
        if isinstance(text_field, list):
            headlines = [str(h) for h in text_field]
        elif isinstance(text_field, str) and text_field.strip().startswith("["):
            try:
                parsed = json.loads(text_field.strip())
                if isinstance(parsed, list):
                    headlines = [str(h) for h in parsed]
                else:
                    headlines = [str(text_field)]
            except (json.JSONDecodeError, ValueError):
                headlines = [str(text_field)]
        else:
            headlines = [str(text_field)]
        for h in headlines:
            h = h.strip()
            if h and len(h) > 20:
                snippets.append({"source": source_label, "text": h[:200]})
    return snippets


print("Loading CSV...")
df = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True, low_memory=False)
df.index = pd.to_datetime(df.index)
df = df.sort_index()
print("Loaded %d rows, %d columns. Date range: %s to %s" % (
    len(df), len(df.columns), df.index[0].date(), df.index[-1].date()))

# Pick monthly first trading days
months = pd.date_range("2015-01-01", "2025-12-31", freq="MS")
selected_dates = []
for m in months:
    candidates = df.index[(df.index >= m) & (df.index < m + pd.offsets.MonthEnd(1))]
    if len(candidates) > 0:
        selected_dates.append(candidates[0])

print("Selected %d monthly dates" % len(selected_dates))

# Pre-build macro series (FRED data is monthly, forward-fill up to 31 days)
macro_series = {}
for key, col in MACRO_COLS.items():
    if col in df.columns:
        macro_series[key] = df[col].ffill(limit=31)
    else:
        print("  WARNING: macro col not found: %s" % col)
        macro_series[key] = pd.Series(dtype=float, index=df.index)

# Pre-build close series for correlation
close_cols = {}
for cls, tickers in TICKERS.items():
    for t in tickers:
        col = get_col(df, t, "close")
        if col:
            close_cols[t] = df[col].astype(float)

result = {"dates": [], "snapshots": {}}

for date in selected_dates:
    date_str = date.strftime("%Y-%m-%d")
    snap = {"date": date_str, "macro": {}, "assets": {}, "correlation": {}, "news": []}

    # Macro
    for key, series in macro_series.items():
        try:
            val = series.loc[:date].dropna().iloc[-1]
            snap["macro"][key] = round(float(val), 4) if not np.isnan(val) else None
        except Exception:
            snap["macro"][key] = None

    # Per-asset
    for cls, tickers in TICKERS.items():
        snap["assets"][cls] = []
        for t in tickers:
            close_col = get_col(df, t, "close")
            if not close_col:
                continue
            close_series = df[close_col].astype(float).loc[:date].dropna()
            if len(close_series) == 0:
                continue
            close_price = float(close_series.iloc[-1])
            ret_20d = ret_60d = None
            if len(close_series) >= 21:
                ret_20d = round(float((close_series.iloc[-1] / close_series.iloc[-21]) - 1), 4)
            if len(close_series) >= 61:
                ret_60d = round(float((close_series.iloc[-1] / close_series.iloc[-61]) - 1), 4)
            vol = annualized_vol(close_series.iloc[-61:] if len(close_series) >= 61 else close_series)
            regime = classify_regime(ret_60d)
            snap["assets"][cls].append({
                "ticker": t, "close": round(close_price, 2),
                "ret_20d": ret_20d, "ret_60d": ret_60d,
                "vol": round(vol, 4) if vol else None, "regime": regime,
            })

    # Inter-class correlation (41-day window of daily returns)
    classes = list(TICKERS.keys())
    class_returns = {}
    for cls, tickers in TICKERS.items():
        cls_ret_list = []
        for t in tickers:
            col = get_col(df, t, "close")
            if col:
                s = df[col].astype(float).loc[:date].dropna().iloc[-42:]
                if len(s) > 5:
                    cls_ret_list.append(s.pct_change().dropna())
        if cls_ret_list:
            combined = pd.concat(cls_ret_list, axis=1).mean(axis=1)
            class_returns[cls] = combined

    corr_matrix = {}
    for c1 in classes:
        corr_matrix[c1] = {}
        for c2 in classes:
            if c1 == c2:
                tickers_c = [t for t in TICKERS[c1] if get_col(df, t, "close")]
                intra_rets = []
                for t in tickers_c:
                    col = get_col(df, t, "close")
                    s = df[col].astype(float).loc[:date].dropna().iloc[-42:]
                    if len(s) > 5:
                        intra_rets.append(s.pct_change().dropna())
                if len(intra_rets) >= 2:
                    mat = pd.concat(intra_rets, axis=1).dropna()
                    if len(mat) > 5 and mat.shape[1] >= 2:
                        c = mat.corr().values
                        upper = c[np.triu_indices(len(c), k=1)]
                        corr_matrix[c1][c2] = round(float(np.mean(upper)), 3)
                    else:
                        corr_matrix[c1][c2] = None
                else:
                    corr_matrix[c1][c2] = None
            else:
                if c1 in class_returns and c2 in class_returns:
                    s1 = class_returns[c1]
                    s2 = class_returns[c2]
                    aligned = pd.concat([s1, s2], axis=1).dropna()
                    if len(aligned) >= 10:
                        corr_matrix[c1][c2] = round(float(aligned.iloc[:,0].corr(aligned.iloc[:,1])), 3)
                    else:
                        corr_matrix[c1][c2] = None
                else:
                    corr_matrix[c1][c2] = None

    snap["correlation"] = corr_matrix

    # News text: extract up to 6 snippets from text_json columns
    # Look in a -2/+5 day window around the snapshot date (handles holidays/weekends)
    window_start = date - pd.Timedelta(days=2)
    window_end   = date + pd.Timedelta(days=5)
    seen = set()
    for text_col in ["equities_text_json", "cryptocurrency_text_json"]:
        if text_col not in df.columns:
            continue
        text_series = df[text_col].loc[window_start:window_end].dropna()
        if len(text_series) == 0:
            text_series = df[text_col].loc[:date].dropna()
        if len(text_series) == 0:
            continue
        raw = text_series.iloc[0]
        source = "Equities" if "equities" in text_col else "Crypto"
        for snippet in extract_news_snippets(str(raw), source):
            key = snippet["text"][:80]
            if key not in seen:
                seen.add(key)
                snap["news"].append(snippet)
                if len(snap["news"]) >= 6:
                    break
        if len(snap["news"]) >= 6:
            break

    result["dates"].append(date_str)
    result["snapshots"][date_str] = snap

    if len(result["dates"]) % 20 == 0:
        print("  Processed %d dates..." % len(result["dates"]))


# Sanitize NaN/inf before JSON serialization
def sanitize(obj):
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj

result = sanitize(result)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, separators=(",", ":"), allow_nan=False)

size_kb = os.path.getsize(OUT_PATH) / 1024
print("\nSaved %d snapshots to %s (%d KB)" % (len(result["dates"]), OUT_PATH, size_kb))
