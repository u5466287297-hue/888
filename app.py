from flask import Flask, render_template, jsonify, request, session
import yfinance as yf
import pandas as pd
import ta
import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Списък с примерни Forex двойки (потребителят може да търси всяка)
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

# История на сигналите по актив
signal_history = {}

def get_data(pair):
    df = yf.download(pair, period="1d", interval=TIMEFRAME)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_indicators(df):
    indicators = {}
    indicators["ema8"] = ta.trend.EMAIndicator(df["Close"], 8).ema_indicator().iloc[-1]
    indicators["ema21"] = ta.trend.EMAIndicator(df["Close"], 21).ema_indicator().iloc[-1]
    indicators["macd"] = ta.trend.MACD(df["Close"]).macd().iloc[-1]
    indicators["rsi"] = ta.momentum.RSIIndicator(df["Close"], 14).rsi().iloc[-1]
    indicators["adx"] = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], 14).adx().iloc[-1]
    indicators["price"] = df["Close"].iloc[-1]
    return indicators

def gainsalgo_conditions(df, ind):
    close = df["Close"]
    open_ = df["Open"]

    bullish_engulfing = close.iloc[-2] < open_.iloc[-2] and close.iloc[-1] > open_.iloc[-1] and close.iloc[-1] > open_.iloc[-2]
    bearish_engulfing = close.iloc[-2] > open_.iloc[-2] and close.iloc[-1] < open_.iloc[-1] and close.iloc[-1] < open_.iloc[-2]

    decrease_over_5 = close.iloc[-1] < close.iloc[-5]
    increase_over_5 = close.iloc[-1] > close.iloc[-5]

    rsi_below_50 = ind["rsi"] < 50
    rsi_above_50 = ind["rsi"] > 50

    bull = bullish_engulfing and rsi_below_50 and decrease_over_5
    bear = bearish_engulfing and rsi_above_50 and increase_over_5

    return bull, bear

def generate_signal(df, ind, pair):
    bull, bear = gainsalgo_conditions(df, ind)

    if (ind["ema8"] > ind["ema21"]
        and ind["macd"] > 0
        and ind["rsi"] > 50
        and ind["adx"] > 15
        and bull):
        signal = "BUY → 5m UP"
    elif (ind["ema8"] < ind["ema21"]
          and ind["macd"] < 0
          and ind["rsi"] < 50
          and ind["adx"] > 15
          and bear):
        signal = "SELL → 5m DOWN"
    else:
        signal = "NO SIGNAL"

    # запис в историята
    if pair not in signal_history:
        signal_history[pair] = []
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    signal_history[pair].append({"time": timestamp, "signal": signal})
    if len(signal_history[pair]) > 10:  # пазим само последните 10 сигнала
        signal_history[pair] = signal_history[pair][-10:]

    return signal

@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pair_key = request.form.get("pair")
        if pair_key in PAIRS:
            session["current_pair"] = PAIRS[pair_key]
    current_pair = session.get("current_pair", "EURUSD=X")
    df = get_data(current_pair)
    if df is None:
        return "No data available"
    ind = calculate_indicators(df)
    signal = generate_signal(df, ind, current_pair)
    history = signal_history.get(current_pair, [])
    return render_template("index.html", indicators=ind, signal=signal, pair=current_pair, pairs=PAIRS, history=history)

@app.route('/api/data')
def api_data():
    current_pair = session.get("current_pair", "EURUSD=X")
    df = get_data(current_pair)
    if df is None:
        return jsonify({"error": "No data"})
    ind = calculate_indicators(df)
    signal = generate_signal(df, ind, current_pair)
    history = signal_history.get(current_pair, [])
    return jsonify({"indicators": ind, "signal": signal, "pair": current_pair, "time": datetime.datetime.now().strftime("%H:%M:%S"), "history": history})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
