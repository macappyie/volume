import streamlit as st
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import time, json, os

# ================= PAGE =================
st.set_page_config(page_title="Volume Seven Dashboard", layout="wide")
st.title("📊 Volume Seven Dashboard")

# ================= CONFIG =================
API_KEY = "awh2j04pcd83zfvq"

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

RANK_FILE = "open_rank.json"

# ================= LOAD INSTRUMENTS =================
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[(df.exchange=="NSE") & (df.instrument_type=="EQ")]
symbol_token = dict(zip(df.tradingsymbol, df.instrument_token))

with open("watchlist.txt") as f:
    WATCHLIST = [x.strip() for x in f if x.strip()]

# ================= HELPERS =================
def fmt_vol(v):
    if v >= 1e7: return f"{v/1e7:.2f} Cr"
    if v >= 1e5: return f"{v/1e5:.2f} L"
    if v >= 1e3: return f"{v/1e3:.1f} K"
    return str(int(v))

# ---------- Daily Snapshot Rank Logic ----------
def is_new_trading_day():
    if not os.path.exists(RANK_FILE):
        return True
    last = datetime.fromtimestamp(os.path.getmtime(RANK_FILE)).date()
    return last != datetime.now().date()

def load_ranks():
    if os.path.exists(RANK_FILE):
        with open(RANK_FILE) as f:
            return json.load(f)
    return {"gainers":{}, "losers":{}}

def save_ranks(r):
    with open(RANK_FILE,"w") as f:
        json.dump(r,f)

def apply_open_rank(df):

    if is_new_trading_day():
        ranks = {"gainers":{}, "losers":{}}
    else:
        ranks = load_ranks()

    gainers = df[df["Change %"]>0].sort_values("Change %",ascending=False)
    losers  = df[df["Change %"]<0].sort_values("Change %")

    for i,row in enumerate(gainers.itertuples(),1):
        if row.Symbol not in ranks["gainers"]:
            ranks["gainers"][row.Symbol]=i

    for i,row in enumerate(losers.itertuples(),1):
        if row.Symbol not in ranks["losers"]:
            ranks["losers"][row.Symbol]=i

    save_ranks(ranks)

    df["Rank"] = df.apply(
        lambda x: ranks["gainers"].get(x["Symbol"])
        if x["Change %"]>0
        else ranks["losers"].get(x["Symbol"]),
        axis=1
    )

    return df

# ================= DATA =================
@st.cache_data(ttl=60)
def load_data():
    rows=[]
    today=datetime.now().date()

    tokens=[symbol_token[s] for s in WATCHLIST if s in symbol_token]
    quotes=kite.quote(tokens)

    for sym in WATCHLIST:
        try:
            token=symbol_token[sym]
            q=quotes[str(token)]

            ltp=q["last_price"]
            prev=q["ohlc"]["close"]
            pct=round(((ltp-prev)/prev)*100,2)
            total_vol=q.get("volume",0)

            daily=kite.historical_data(
                token,today-timedelta(days=15),
                today-timedelta(days=1),"day"
            )
            avg_raw=sum(c["volume"] for c in daily[-7:])/7 if len(daily)>=7 else 0

            rows.append({
                "Stock":sym,
                "LTP":round(ltp,2),
                "% Chg":pct,
                "7D Avg Vol":fmt_vol(avg_raw),
                "TY Vol":round(total_vol/avg_raw,2) if avg_raw else 0,
                "Total Vol":fmt_vol(total_vol)
            })
            time.sleep(0.05)
        except:
            pass

    return pd.DataFrame(rows)

# ================= MAIN =================
dfm=load_data()
dfm=apply_open_rank(dfm)
dfm=dfm.head(30)

col1,col2=st.columns(2)

with col1:
    st.subheader("🟢 Top Gainers")
    st.dataframe(
        dfm[dfm["% Chg"]>0].sort_values("Rank"),
        use_container_width=True
    )

with col2:
    st.subheader("🔴 Top Losers")
    st.dataframe(
        dfm[dfm["% Chg"]<0].sort_values("Rank"),
        use_container_width=True
    )

st.caption("Auto refresh every 60 seconds")
st.button("🔄 Refresh")

