import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="AI Trading Scanner", page_icon="📈", layout="wide")

st.title("📈 AI Trading Scanner")
st.caption("Automatische signalenscanner voor goud en zilver — geen automatische orders.")

# Automatic refresh. Streamlit Cloud may sleep while the app is inactive.
refresh_seconds = st.sidebar.selectbox("Automatisch verversen", [30, 60, 120, 300], index=1)
st_autorefresh(interval=refresh_seconds * 1000, key="market_refresh")

symbol_map = {
    "Goud (XAUUSD)": [("XAUUSD=X", "Yahoo spot"), ("GC=F", "Gold futures-proxy")],
    "Zilver (XAGUSD)": [("XAGUSD=X", "Yahoo spot"), ("SI=F", "Silver futures-proxy")],
}
asset = st.sidebar.selectbox("Markt", list(symbol_map.keys()))
timeframe = st.sidebar.selectbox("Analyse-timeframe", ["15m", "1h", "1d"], index=0)
show_debug = st.sidebar.checkbox("Toon technische details", value=False)

TIMEFRAME_SETTINGS = {
    "15m": {"period": "7d", "interval": "15m"},
    "1h": {"period": "60d", "interval": "1h"},
    "1d": {"period": "2y", "interval": "1d"},
}

@st.cache_data(ttl=45, show_spinner=False)
def get_market_data(ticker, period, interval):
    raw = yf.download(
        ticker, period=period, interval=interval,
        auto_adjust=True, progress=False, threads=False
    )
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=lambda x: str(x).title())
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in raw.columns for c in required):
        return pd.DataFrame()
    raw = raw[required].dropna()
    return raw

def add_indicators(df):
    d = df.copy()
    d["EMA9"] = d["Close"].ewm(span=9, adjust=False).mean()
    d["EMA21"] = d["Close"].ewm(span=21, adjust=False).mean()
    delta = d["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["RSI"] = 100 - (100 / (1 + rs))
    fast = d["Close"].ewm(span=12, adjust=False).mean()
    slow = d["Close"].ewm(span=26, adjust=False).mean()
    d["MACD"] = fast - slow
    d["MACD_Signal"] = d["MACD"].ewm(span=9, adjust=False).mean()
    prev_close = d["Close"].shift(1)
    tr = pd.concat([
        d["High"] - d["Low"],
        (d["High"] - prev_close).abs(),
        (d["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    d["ATR"] = tr.ewm(alpha=1/14, adjust=False).mean()
    return d.dropna()

def get_direction(df):
    if len(df) < 30:
        return "ONBEKEND"
    last = df.iloc[-1]
    if last["EMA9"] > last["EMA21"] and last["Close"] > last["EMA21"]:
        return "STIJGEND"
    if last["EMA9"] < last["EMA21"] and last["Close"] < last["EMA21"]:
        return "DALEND"
    return "ZIJWAARTS"

def analyze(df, higher_df):
    last = df.iloc[-1]
    previous = df.iloc[-2]
    htf = get_direction(higher_df)
    score_buy = 0
    score_sell = 0
    reasons_buy, reasons_sell = [], []

    if last["EMA9"] > last["EMA21"]:
        score_buy += 2; reasons_buy.append("EMA 9 boven EMA 21")
    elif last["EMA9"] < last["EMA21"]:
        score_sell += 2; reasons_sell.append("EMA 9 onder EMA 21")

    if last["RSI"] >= 52 and last["RSI"] < 70:
        score_buy += 1; reasons_buy.append("RSI ondersteunt opwaarts momentum")
    elif last["RSI"] <= 48 and last["RSI"] > 30:
        score_sell += 1; reasons_sell.append("RSI ondersteunt neerwaarts momentum")

    if last["MACD"] > last["MACD_Signal"]:
        score_buy += 1; reasons_buy.append("MACD boven signaallijn")
    elif last["MACD"] < last["MACD_Signal"]:
        score_sell += 1; reasons_sell.append("MACD onder signaallijn")

    if last["Close"] > last["EMA21"]:
        score_buy += 1; reasons_buy.append("Koers boven EMA 21")
    elif last["Close"] < last["EMA21"]:
        score_sell += 1; reasons_sell.append("Koers onder EMA 21")

    # Higher timeframe is a filter, not a prediction.
    if htf == "STIJGEND":
        score_buy += 1; reasons_buy.append("Hoger timeframe stijgend")
    elif htf == "DALEND":
        score_sell += 1; reasons_sell.append("Hoger timeframe dalend")

    # Avoid chasing extreme RSI.
    if last["RSI"] >= 70:
        score_buy -= 1
    if last["RSI"] <= 30:
        score_sell -= 1

    if score_buy >= 4 and score_buy >= score_sell + 2:
        signal = "BUY SETUP"
        reasons = reasons_buy
        direction = 1
    elif score_sell >= 4 and score_sell >= score_buy + 2:
        signal = "SELL SETUP"
        reasons = reasons_sell
        direction = -1
    else:
        signal = "AFWACHTEN"
        reasons = ["Geen duidelijke combinatie van bevestigingen."]
        direction = 0

    # A possible exit warning is a weakening / opposite momentum hint, not an instruction.
    exit_warning = False
    if direction == 1 and (last["EMA9"] < previous["EMA9"] or last["MACD"] < last["MACD_Signal"]):
        exit_warning = True
    if direction == -1 and (last["EMA9"] > previous["EMA9"] or last["MACD"] > last["MACD_Signal"]):
        exit_warning = True

    price = float(last["Close"])
    atr = float(last["ATR"])
    sl = price - direction * 1.5 * atr if direction else np.nan
    tp = price + direction * 2.0 * atr if direction else np.nan
    strength = max(score_buy, score_sell)
    confidence = min(95, max(0, int(strength / 6 * 100)))

    return {
        "signal": signal, "price": price, "sl": sl, "tp": tp,
        "rsi": float(last["RSI"]), "atr": atr, "htf": htf,
        "score_buy": score_buy, "score_sell": score_sell,
        "confidence": confidence, "reasons": reasons,
        "exit_warning": exit_warning, "timestamp": df.index[-1]
    }

def fmt_price(value):
    return "—" if pd.isna(value) else f"{value:,.3f}"

settings = TIMEFRAME_SETTINGS[timeframe]
data = pd.DataFrame()
used_ticker, source_note = None, None
with st.spinner("Marktgegevens ophalen..."):
    for ticker, note in symbol_map[asset]:
        data = get_market_data(ticker, settings["period"], settings["interval"])
        if not data.empty and len(data) >= 35:
            used_ticker, source_note = ticker, note
            break

if data.empty or len(data) < 35:
    st.error("Er zijn onvoldoende koersgegevens beschikbaar. Probeer later opnieuw of kies een ander timeframe.")
    st.info("Yahoo Finance kan tijdelijk geen data leveren. De scanner gebruikt geen brokerkoersen.")
    st.stop()

# A separate higher timeframe provides a broad trend filter.
higher_interval = "1h" if timeframe == "15m" else "1d"
higher_period = "60d" if higher_interval == "1h" else "2y"
higher = get_market_data(used_ticker, higher_period, higher_interval)
if higher.empty or len(higher) < 30:
    higher = data
data_i = add_indicators(data)
higher_i = add_indicators(higher)
if len(data_i) < 2 or len(higher_i) < 2:
    st.error("Niet genoeg gegevens om indicatoren te berekenen.")
    st.stop()

result = analyze(data_i, higher_i)
now = datetime.now(timezone.utc)
st.caption(f"Laatste controle: {now.astimezone().strftime('%d-%m-%Y %H:%M:%S')} · Databron: {source_note} ({used_ticker}) · Laatste candle: {result['timestamp']}")

# Track changes in the signal between refreshes.
if "last_signal_by_asset" not in st.session_state:
    st.session_state.last_signal_by_asset = {}
if "signal_events" not in st.session_state:
    st.session_state.signal_events = []

previous_signal = st.session_state.last_signal_by_asset.get(asset)
if previous_signal != result["signal"]:
    if previous_signal is not None:
        st.session_state.signal_events.insert(0, {
            "time": now.astimezone().strftime("%H:%M:%S"),
            "asset": asset,
            "change": f"{previous_signal} → {result['signal']}"
        })
    st.session_state.last_signal_by_asset[asset] = result["signal"]

signal_colors = {
    "BUY SETUP": "🟢",
    "SELL SETUP": "🔴",
    "AFWACHTEN": "🟡"
}
st.subheader(f"{signal_colors[result['signal']]} {result['signal']}")
if result["exit_warning"]:
    st.warning("EXIT-WAARSCHUWING: momentum verzwakt of beweegt tegen het huidige setup in. Controleer je positie en eigen handelsplan. Dit is geen automatische sluitopdracht.")
elif result["signal"] == "AFWACHTEN":
    st.info("Geen sterke setup. Niet forceren; wacht op meer bevestiging.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Indicatieve koers", fmt_price(result["price"]))
c2.metric("Signaalsterkte (heuristisch)", f"{result['confidence']}/100")
c3.metric("RSI 14", f"{result['rsi']:.1f}")
c4.metric("Hoger timeframe", result["htf"])

c5, c6 = st.columns(2)
c5.metric("Indicatieve stop-loss", fmt_price(result["sl"]))
c6.metric("Indicatieve take-profit", fmt_price(result["tp"]))

st.subheader("Waarom dit signaal?")
for reason in result["reasons"]:
    st.write("• " + reason)

st.subheader("Marktontwikkeling")
st.line_chart(data_i[["Close", "EMA9", "EMA21"]].tail(100), use_container_width=True)

if result["exit_warning"]:
    st.warning("Let op: dit is een vroege waarschuwing op basis van indicatoren. Het is geen bewijs dat de markt daadwerkelijk omkeert.")

st.subheader("Automatische updates")
st.write(f"De app controleert elke **{refresh_seconds} seconden** opnieuw. De tijdlijn registreert wanneer de hoofdstatus verandert.")
if st.session_state.signal_events:
    st.dataframe(pd.DataFrame(st.session_state.signal_events[:20]), use_container_width=True, hide_index=True)
else:
    st.caption("Nog geen signaalwisselingen geregistreerd tijdens deze sessie.")

if show_debug:
    st.subheader("Technische details")
    st.write({
        "Koersbron": used_ticker,
        "BUY-score": result["score_buy"],
        "SELL-score": result["score_sell"],
        "ATR": result["atr"],
        "Laatste candle": str(result["timestamp"])
    })
    st.dataframe(data_i.tail(10), use_container_width=True)

with st.expander("Belangrijke beperkingen en veilig gebruik"):
    st.write(
        "Deze scanner is een regelgebaseerd prototype, geen zelflerend AI-model en geen bewezen winstgevende strategie. "
        "Yahoo Finance-data kan vertraagd, onvolledig of anders dan de koers van jouw MT5-broker zijn. "
        "De SL/TP zijn indicatieve ATR-niveaus en houden geen rekening met spread, slippage, swaps of jouw contractgrootte. "
        "Een signaalsterkte is geen statistische kans op winst. Test eerst op demo en controleer altijd de brokerkoers."
    )
