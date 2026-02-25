import requests
import pandas as pd
import time
import os
from telegram import Bot

# ==========================
# SETTINGS
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TIMEFRAMES = ["1", "5", "15", "60"]  # minutes
RSI_PERIOD = 14
RSI_BULL = 50
RSI_BEAR = 50

bot = Bot(token=BOT_TOKEN)

# Store last signal to avoid duplicates
LAST_SIGNAL = {}

# ==========================
# FUNCTIONS
# ==========================
def get_klines(symbol, interval, category="spot"):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "limit": 60
    }
    data = requests.get(url, params=params).json()["result"]["list"]
    df = pd.DataFrame(data)
    df = df.iloc[::-1]
    df["close"] = df[4].astype(float)
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_cross(df):
    df["SMA5"] = df["close"].rolling(5).mean()
    df["SMA50"] = df["close"].rolling(50).mean()
    df["RSI"] = compute_rsi(df["close"], RSI_PERIOD)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Bullish
    if prev["SMA5"] < prev["SMA50"] and last["SMA5"] > last["SMA50"] and last["RSI"] > RSI_BULL:
        return "bullish", last["SMA5"], last["SMA50"], last["RSI"]

    # Bearish
    if prev["SMA5"] > prev["SMA50"] and last["SMA5"] < last["SMA50"] and last["RSI"] < RSI_BEAR:
        return "bearish", last["SMA5"], last["SMA50"], last["RSI"]

    return None, None, None, None

# ==========================
# MAIN LOOP
# ==========================
print("Professional Multi-Timeframe Bot Started...")

while True:
    try:
        for symbol in SYMBOLS:
            for market in ["spot", "linear"]:
                for tf in TIMEFRAMES:
                    df = get_klines(symbol, tf, market)
                    signal, sma5, sma50, rsi = check_cross(df)
                    key = f"{symbol}-{market}-{tf}"

                    if signal and LAST_SIGNAL.get(key) != signal:
                        msg = f"{'🚀 BULLISH' if signal=='bullish' else '🔻 BEARISH'} CROSS\n"
                        msg += f"Symbol: {symbol}\nMarket: {market.upper()}\nTimeframe: {tf}m\n"
                        msg += f"SMA5: {sma5:.2f}\nSMA50: {sma50:.2f}\nRSI: {rsi:.2f}"
                        bot.send_message(chat_id=CHAT_ID, text=msg)
                        LAST_SIGNAL[key] = signal

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
