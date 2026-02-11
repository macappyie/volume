import streamlit as st
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import time

# ================= PAGE =================
st.set_page_config(page_title="Volume Seven Dashboard", layout="wide")
st.title("📊 Volume Seven Dashboard")

API_KEY = "awh2j04pcd83zfvq"

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ================= LOAD INSTRUMENTS =================
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[(df.exchange == "NSE") & (df.instrument_type == "EQ")]
symbol_token = dict(zip(df.tradingsymbol, df.instrument_token))

with open("watchlist.txt") as f:
    WATCHLIST = [x.strip() for x in f if x.strip()]

# ================= HELPERS =================
def fmt_vol(v):
    if v >= 1e7: return f"{v/1e7:.2f} Cr"
    if v >= 1e5: return f"{v/1e5:.2f} L"
    if v >= 1e3: return f"{v/1e3:.1f} K"
    return str(int(v))

# ================= DATA LOAD =================
@st.cache_data(ttl=60)
def load_data():
    rows = []
    today = datetime.now().date()

    tokens = [symbol_token[s] for s in WATCHLIST if s in symbol_token]

    if not tokens:
        return pd.DataFrame()

    quotes = kite.quote(tokens)

    for sym in WATCHLIST:
        try:
            token = symbol_token[sym]
            q = quotes[str(token)]

            ltp = float(q["last_price"])
            prev = float(q["ohlc"]["close"])
            pct = round(((ltp - prev) / prev) * 100, 2)
            total_vol = q.get("volume", 0)

            candles = kite.historical_data(token, today, today, "5minute")
            if not candles:
                continue

            c915 = candles[0]

            daily = kite.historical_data(
                token,
                today - timedelta(days=15),
                today - timedelta(days=1),
                "day"
            )

            avg_raw = (
                sum(c["volume"] for c in daily[-7:]) / 7
                if len(daily) >= 7 else 0
            )

            rows.append({
                "Symbol": sym,
                "LTP": round(ltp, 2),
                "Change %": pct,
                "Avg Vol": fmt_vol(avg_raw),
                "9:15 Vol": fmt_vol(c915["volume"]),
                "Today Vol X": round(total_vol / avg_raw, 2) if avg_raw else 0,
                "Total Vol": fmt_vol(total_vol)
            })

        except:
            continue

    dfm = pd.DataFrame(rows)

    if not dfm.empty:
        dfm["Change %"] = pd.to_numeric(dfm["Change %"], errors="coerce")
        dfm["Today Vol X"] = pd.to_numeric(dfm["Today Vol X"], errors="coerce")

    return dfm


# ================= LOAD DATA =================
dfm = load_data()

if dfm.empty:
    st.warning("No data loaded from Kite API")
    st.stop()

# ================= DISPLAY =================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🟢 Top 20 Gainers")
    gainers = (
        dfm[dfm["Change %"] > 0]
        .sort_values(by="Change %", ascending=False)
        .head(20)
    )
    st.dataframe(gainers, use_container_width=True)

with col2:
    st.subheader("🔴 Top 20 Losers")
    losers = (
        dfm[dfm["Change %"] < 0]
        .sort_values(by="Change %", ascending=True)
        .head(20)
    )
    st.dataframe(losers, use_container_width=True)

st.caption("🔁 Auto refresh every 60 seconds")

