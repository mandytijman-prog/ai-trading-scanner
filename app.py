import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

st.set_page_config(page_title="AI Trading Signal Scanner", page_icon="📡", layout="wide")

st.title("📡 AI Trading Signal Scanner")
st.caption("Gratis prototype • XAUUSD & XAGUSD • signalen-only • geen automatische orders")

st.warning(
    "Educatieve prototypeversie. Dit is geen financieel advies en signalen zijn geen voorspellingen. "
    "Controleer koersen bij je broker. Yahoo Finance-data kan vertraagd, onvolledig of tijdelijk niet beschikbaar zijn."
)

SYMBOLS = {
    "XAUUSD (goud)": {"primary": "XAUUSD=X", "fallback": "GC=F", "label": "Gold"},
    "XAGUSD (zilver)": {"primary": "XAGUSD=X", "fallback": "SI=F", "label": "Silver"},
}

@st.cache_data(ttl=300, show_spinner=False)
def load_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)
    needed = ["Open", "High", "Low", "Close"]
    if not all(c in df.columns for c in needed):
        return pd.DataFrame()
    return df.dropna(subset=needed).copy()

def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def enrich(df):
    d = df.copy()
    close = d["Close"]
    d["EMA9"] = close.ewm(span=9, adjust=False).mean()
    d["EMA21"] = close.ewm(span=21, adjust=False).mean()
    d["RSI14"] = rsi(close)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    d["MACD"] = ema12 - ema26
    d["MACD_signal"] = d["MACD"].ewm(span=9, adjust=False).mean()
    prev_close = close.shift(1)
    tr = pd.concat([
        d["High"] - d["Low"],
        (d["High"] - prev_close).abs(),
        (d["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    d["ATR14"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    return d.dropna()

def analyse(d):
    if len(d) < 30:
        return {"signal": "INSUFFICIENT DATA", "score": 0, "reasons": ["Niet genoeg candles voor betrouwbare indicatorberekening."]}
    last = d.iloc[-1]
    checks = {
        "EMA-trend": last["EMA9"] > last["EMA21"],
        "Prijs boven EMA21": last["Close"] > last["EMA21"],
        "RSI-momentum": 50 < last["RSI14"] < 70,
        "MACD-momentum": last["MACD"] > last["MACD_signal"],
    }
    sell_checks = {
        "EMA-trend": last["EMA9"] < last["EMA21"],
        "Prijs onder EMA21": last["Close"] < last["EMA21"],
        "RSI-momentum": 30 < last["RSI14"] < 50,
        "MACD-momentum": last["MACD"] < last["MACD_signal"],
    }
    buy_score = sum(bool(v) for v in checks.values())
    sell_score = sum(bool(v) for v in sell_checks.values())
    if buy_score == 4:
        signal, score, reasons = "BUY SETUP", buy_score, [f"✓ {k}" for k in checks]
        direction = 1
    elif sell_score == 4:
        signal, score, reasons = "SELL SETUP", sell_score, [f"✓ {k}" for k in sell_checks]
        direction = -1
    else:
        signal, score, reasons = "NO TRADE", max(buy_score, sell_score), []
        direction = 0
        for k, v in checks.items():
            reasons.append(("✓ " if v else "— ") + "Bullish: " + k)
        for k, v in sell_checks.items():
            reasons.append(("✓ " if v else "— ") + "Bearish: " + k)
    entry = float(last["Close"])
    atr = float(last["ATR14"])
    if direction:
        stop = entry - direction * 1.5 * atr
        target = entry + direction * 3.0 * atr
    else:
        stop = target = None
    return {
        "signal": signal, "score": score, "reasons": reasons,
        "entry": entry, "stop": stop, "target": target,
        "rsi": float(last["RSI14"]), "ema9": float(last["EMA9"]),
        "ema21": float(last["EMA21"]), "macd": float(last["MACD"]),
        "atr": atr, "timestamp": d.index[-1]
    }

with st.sidebar:
    st.header("Instellingen")
    market = st.selectbox("Markt", list(SYMBOLS.keys()))
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "1d"], index=1)
    st.caption("15m: korte termijn • 1h: intraday • 1d: swingcontext")
    refresh = st.button("🔄 Vernieuw data", use_container_width=True)
    if refresh:
        st.cache_data.clear()
    st.divider()
    st.caption("Data: Yahoo Finance via yfinance. Futures-symbolen worden als fallback gebruikt.")

cfg = SYMBOLS[market]
period_map = {"15m": ("60d", "15m"), "1h": ("730d", "1h"), "1d": ("5y", "1d")}
period, interval = period_map[timeframe]

with st.spinner(f"Koersdata ophalen voor {market}..."):
    raw = load_data(cfg["primary"], period, interval)
    used_symbol = cfg["primary"]
    if raw.empty:
        raw = load_data(cfg["fallback"], period, interval)
        used_symbol = cfg["fallback"]

if raw.empty:
    st.error("Geen koersdata ontvangen. Probeer later opnieuw of controleer je internetverbinding.")
    st.info(f"Geprobeerd: {cfg['primary']} en {cfg['fallback']}.")
    st.stop()

data = enrich(raw)
if data.empty:
    st.error("Er is onvoldoende historische data om indicatoren te berekenen.")
    st.stop()

result = analyse(data)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Laatste koers", f"{result.get('entry', float(data['Close'].iloc[-1])):,.3f}")
c2.metric("RSI (14)", f"{result['rsi']:.1f}")
c3.metric("EMA 9 / 21", "Bullish" if result["ema9"] > result["ema21"] else "Bearish")
c4.metric("Setup-score", f"{result['score']}/4")

st.subheader(f"{market} — {timeframe}")
if result["signal"] == "BUY SETUP":
    st.success("🟢 BUY SETUP — alle vier technische voorwaarden zijn bevestigd.")
elif result["signal"] == "SELL SETUP":
    st.error("🔴 SELL SETUP — alle vier technische voorwaarden zijn bevestigd.")
else:
    st.info("⚪ NO TRADE — de voorwaarden zijn niet allemaal tegelijk bevestigd.")

left, right = st.columns([1, 1])
with left:
    st.markdown("#### Analyse")
    for reason in result["reasons"]:
        st.write(reason)
    st.caption(f"Laatste candle: {result['timestamp']} • Dataticker: {used_symbol}")
with right:
    st.markdown("#### Voorwaardelijke trade-niveaus")
    if result["signal"] in ("BUY SETUP", "SELL SETUP"):
        st.metric("Referentie-entry", f"{result['entry']:,.3f}")
        st.metric("Indicatieve stop-loss (1,5 × ATR)", f"{result['stop']:,.3f}")
        st.metric("Indicatieve take-profit (3 × ATR)", f"{result['target']:,.3f}")
        st.caption("Indicatieve niveaus op basis van de laatst gesloten/beschikbare candle; spreads, slippage en brokerprijzen kunnen afwijken.")
    else:
        st.write("Geen entry, stop-loss of take-profit zolang er geen volledige setup is.")

st.markdown("#### Koersgrafiek en gemiddelden")
chart = data[["Close", "EMA9", "EMA21"]].tail(180).rename(
    columns={"Close": "Prijs", "EMA9": "EMA 9", "EMA21": "EMA 21"}
)
st.line_chart(chart, use_container_width=True)

with st.expander("Indicatorwaarden en recente candles"):
    st.dataframe(data[["Open", "High", "Low", "Close", "EMA9", "EMA21", "RSI14", "MACD", "MACD_signal", "ATR14"]].tail(20), use_container_width=True)

with st.expander("Hoe werkt deze eerste versie?"):
    st.markdown("""
    **BUY SETUP** vereist tegelijkertijd:
    - EMA 9 boven EMA 21
    - Slotkoers boven EMA 21
    - RSI tussen 50 en 70
    - MACD boven de signaallijn

    **SELL SETUP** gebruikt de omgekeerde voorwaarden (RSI tussen 30 en 50).
    Anders is het resultaat **NO TRADE**.

    De score is het aantal overeenkomende voorwaarden, geen winstkans of betrouwbaarheidspercentage.
    De app gebruikt nog geen nieuwsanalyse, orderboekdata, sentimentdata of machine learning.
    """)

st.caption(f"Prototype • Laatst vernieuwd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Geen orders worden geplaatst.")
