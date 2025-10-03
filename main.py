from flask import Flask, render_template, request
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

app = Flask(__name__)

# Trang chủ với form chọn coin
@app.route("/")
def home():
    return render_template("index.html")

# Route phân tích coin
@app.route("/analyze", methods=["GET"])
def analyze():
    try:
        coin_id = request.args.get("coin", "bitcoin")  # mặc định là bitcoin
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30"
        response = requests.get(url).json()

        if not response.get("prices"):
            return f"❌ Không có dữ liệu cho {coin_id}"

        # Tạo DataFrame
        df = pd.DataFrame(response["prices"], columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df.merge(pd.DataFrame(response["total_volumes"], columns=["time", "volume"]), on="time", how="left")
        df = df.merge(pd.DataFrame(response["market_caps"], columns=["time", "market_cap"]), on="time", how="left")

        # Tính toán cơ bản
        df["price_change"] = df["price"].pct_change().fillna(0)
        df["inflow"] = np.where(df["price_change"] > 0, df["price"] * df["price_change"], 0)
        df["outflow"] = np.where(df["price_change"] < 0, df["price"] * abs(df["price_change"]), 0)
        df["volume_percent_mc"] = (df["volume"] / df["market_cap"]).fillna(0) * 100

        # RSI
        delta = df["price"].diff().fillna(0)
        gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14, min_periods=1).mean()
        rs = gain / loss.replace(0, np.finfo(float).eps)
        df["RSI"] = 100 - (100 / (1 + rs)).fillna(50)

        # MACD
        exp1 = df["price"].ewm(span=12, min_periods=1).mean()
        exp2 = df["price"].ewm(span=26, min_periods=1).mean()
        macd = exp1 - exp2
        df["MACD"] = macd.fillna(0)
        df["MACD_signal"] = macd.ewm(span=9, min_periods=1).mean().fillna(0)
        df["signal"] = np.where((df["RSI"] < 30) & (df["MACD"] > df["MACD_signal"]), "Buy",
                               np.where((df["RSI"] > 70) & (df["MACD"] < df["MACD_signal"]), "Sell", "Hold"))

        # Volume ratio 7/30
        vol_7d = df["volume"].tail(7).mean() if len(df) >= 7 else df["volume"].mean()
        vol_30d = df["volume"].mean()
        vol_ratio = vol_7d / vol_30d if vol_30d > 0 else 0

        # Biểu đồ
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time"], y=df["price"], name="Price", line=dict(color="lime")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["market_cap"], name="Market Cap", line=dict(color="orange")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI", line=dict(color="magenta")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD", line=dict(color="blue")))
        fig.add_trace(go.Scatter(x=df["time"], y=df["MACD_signal"], name="MACD Signal", line=dict(color="red")))
        fig.update_layout(title=f"{coin_id.capitalize()} Analysis", xaxis_title="Date", yaxis_title="Value",
                          height=600, template="plotly_dark")

        plot_div = fig.to_html(full_html=False)

        # Lấy dữ liệu cuối
        latest = df.iloc[-1].fillna(0)
        return render_template("index.html",
                               coin=coin_id,
                               price=f"${latest['price']:,.2f}",
                               market_cap=f"${latest['market_cap']:,.0f}",
                               vol_percent=f"{latest['volume_percent_mc']:.2f}%",
                               inflow=f"${df['inflow'].sum():,.0f}",
                               outflow=f"${df['outflow'].sum():,.0f}",
                               vol_ratio=f"{vol_ratio:.2f}",
                               signal=latest['signal'],
                               plot=plot_div,
                               time=datetime.now().strftime("%Y-%m-%d %H:%M"))
    except Exception as e:
        return f"⚠️ Server Error: {str(e)}"

@app.route("/hello")
def hello():
    return "Hello from Flask on Render!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
