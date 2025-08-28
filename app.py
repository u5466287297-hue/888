from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import ta

app = Flask(__name__)

PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDCAD": "USDCAD=X"
}

TIMEFRAME = "1m"

def get_data(pair, period="1d"):
    df = yf.download(pair, period=period, interval=TIMEFRAME)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def check_signal(df, mode="strict"):
    ema8 = ta.trend.EMAIndicator(df["Close"], 8).ema_indicator()
    ema21 = ta.trend.EMAIndicator(df["Close"], 21).ema_indicator()
    macd = ta.trend.MACD(df["Close"]).macd()
    rsi = ta.momentum.RSIIndicator(df["Close"], 14).rsi()
    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], 14).adx()

    ema_cross_buy = ema8.iloc[-1] > ema21.iloc[-1]
    ema_cross_sell = ema8.iloc[-1] < ema21.iloc[-1]

    if mode == "strict":
        if ema_cross_buy and macd.iloc[-1] > 0 and rsi.iloc[-1] > 50 and adx.iloc[-1] > 15:
            return "BUY"
        elif ema_cross_sell and macd.iloc[-1] < 0 and rsi.iloc[-1] < 50 and adx.iloc[-1] > 15:
            return "SELL"
    else:  # normal mode (по-чести)
        if ema_cross_buy and macd.iloc[-1] > -0.1 and rsi.iloc[-1] > 45 and adx.iloc[-1] > 10:
            return "BUY"
        elif ema_cross_sell and macd.iloc[-1] < 0.1 and rsi.iloc[-1] < 55 and adx.iloc[-1] > 10:
            return "SELL"
    return "HOLD"

@app.route('/')
def index():
    mode = request.args.get("mode", "strict")
    pair = request.args.get("pair", "EURUSD")
    df = get_data(PAIRS[pair])
    if df is None:
        signal = "No Data"
        price = 0
    else:
        signal = check_signal(df, mode)
        price = df["Close"].iloc[-1]
    return render_template("index.html", pairs=PAIRS, active_pair=pair, signal=signal, price=price, mode=mode)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
