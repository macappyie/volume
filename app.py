from flask import Flask, render_template
import pandas as pd
from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import time, json, os

app = Flask(__name__)

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

# ================= INDEX =================
@app.route("/")
def index():

    rows = []
    today = datetime.now().date()

    tokens = [symbol_token[s] for s in WATCHLIST if s in symbol_token]
    quotes = kite.quote(tokens)

    for sym in WATCHLIST:
        try:
            token = symbol_token[sym]
            q = quotes[str(token)]

            ltp = q["last_price"]
            prev = q["ohlc"]["close"]
            pct = round(((ltp-prev)/prev)*100,2)
            total_vol = q.get("volume",0)

            candles = kite.historical_data(token, today, today, "5minute")
            if not candles:
                continue
            c915 = candles[0]

            daily = kite.historical_data(
                token, today-timedelta(days=15), today-timedelta(days=1), "day"
            )
            avg_raw = sum(c["volume"] for c in daily[-7:]) / 7 if len(daily)>=7 else 0

            rows.append({
                "symbol": sym,
                "ltp": round(ltp,2),
                "change": pct,
                "avg_vol": fmt_vol(avg_raw),
                "vol_915": fmt_vol(c915["volume"]),
                "ty_vol": f"{round(total_vol/avg_raw,2)}x" if avg_raw else "",
                "ty_vol_num": round(total_vol/avg_raw,2) if avg_raw else 0,
                "total_vol": fmt_vol(total_vol)
            })

            time.sleep(0.15)
        except:
            continue

    dfm = pd.DataFrame(rows)

    if datetime.now().time() >= datetime.strptime("09:20","%H:%M").time():
        if not os.path.exists(RANK_FILE):
            tmp = dfm.sort_values("change",ascending=False)
            ranks = {r.symbol:i+1 for i,r in enumerate(tmp.itertuples())}
            with open(RANK_FILE,"w") as f:
                json.dump(ranks,f)

    ranks = {}
    if os.path.exists(RANK_FILE):
        with open(RANK_FILE) as f:
            ranks = json.load(f)

    dfm["rank"] = dfm["symbol"].map(ranks)

    gainers = (
        dfm[dfm["change"] > 0]
        .sort_values("change", ascending=False)
    )

    losers = (
        dfm[dfm["change"] < 0]
        .sort_values("change", ascending=True)
    )

    return render_template(
        "index.html",
        gainers=gainers.to_dict("records"),
        losers=losers.to_dict("records")
    )

# ❌ Flask server removed for Streamlit Cloud
if __name__ == "__main__":
    pass

