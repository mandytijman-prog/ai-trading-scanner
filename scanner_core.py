"""Indicator and signal logic for an EDUCATIONAL signal scanner (no order execution)."""
from __future__ import annotations
import numpy as np
import pandas as pd

REQUIRED = ('Open','High','Low','Close','Volume')

def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=list(REQUIRED))
    d = df.copy()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d.columns = [str(c).title() for c in d.columns]
    if not set(REQUIRED).issubset(d.columns):
        raise ValueError('OHLCV-kolommen ontbreken')
    d = d[list(REQUIRED)].apply(pd.to_numeric, errors='coerce').dropna()
    d = d[~d.index.duplicated(keep='last')].sort_index()
    d = d[(d.High >= d.Low) & (d.High >= d.Open) & (d.High >= d.Close)
          & (d.Low <= d.Open) & (d.Low <= d.Close) & (d.Close > 0)]
    return d

def closed_candles(df: pd.DataFrame, interval: str, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Keep only bars whose start timestamp + interval <= now (UTC)."""
    if df.empty:
        return df.copy()
    durations = {'15m': pd.Timedelta(minutes=15), '1h': pd.Timedelta(hours=1), '1d': pd.Timedelta(days=1)}
    if interval not in durations:
        raise ValueError(f'Onbekend timeframe: {interval}')
    ix = pd.DatetimeIndex(df.index)
    if ix.tz is None:
        raise ValueError('Timestamps zonder timezone zijn niet veilig; bron normaliseren naar UTC.')
    current = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if current.tzinfo is None:
        raise ValueError('now vereist timezone')
    current = current.tz_convert('UTC')
    return df.loc[(ix.tz_convert('UTC') + durations[interval]) <= current].copy()

def indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d['EMA9'] = d.Close.ewm(span=9, adjust=False).mean()
    d['EMA21'] = d.Close.ewm(span=21, adjust=False).mean()
    delta = d.Close.diff()
    gains = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gains / losses.replace(0, np.nan)
    d['RSI'] = 100 - (100 / (1 + rs))
    d.loc[(losses == 0) & (gains > 0), 'RSI'] = 100
    d.loc[(losses == 0) & (gains == 0), 'RSI'] = 50
    fast = d.Close.ewm(span=12, adjust=False).mean()
    slow = d.Close.ewm(span=26, adjust=False).mean()
    d['MACD'] = fast - slow
    d['MACD_Signal'] = d.MACD.ewm(span=9, adjust=False).mean()
    prev = d.Close.shift()
    tr = pd.concat([d.High-d.Low, (d.High-prev).abs(), (d.Low-prev).abs()], axis=1).max(axis=1)
    d['ATR'] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    return d.dropna()

def direction(df: pd.DataFrame) -> str:
    if len(df) < 30:
        return 'ONBEKEND'
    x = df.iloc[-1]
    if x.EMA9 > x.EMA21 and x.Close > x.EMA21: return 'STIJGEND'
    if x.EMA9 < x.EMA21 and x.Close < x.EMA21: return 'DALEND'
    return 'ZIJWAARTS'

def analyze(df: pd.DataFrame, higher: pd.DataFrame, sl_atr: float = 1.5, rr: float = 2.) -> dict:
    if len(df) < 30 or len(higher) < 30:
        raise ValueError('Minimaal 30 gesloten indicatorcandles nodig op beide timeframes')
    last, previous = df.iloc[-1], df.iloc[-2]
    htf = direction(higher)
    buy = sell = 0
    reasons_buy, reasons_sell = [], []
    if last.EMA9 > last.EMA21: buy += 2; reasons_buy.append('EMA9 boven EMA21')
    elif last.EMA9 < last.EMA21: sell += 2; reasons_sell.append('EMA9 onder EMA21')
    if 52 <= last.RSI < 70: buy += 1; reasons_buy.append('RSI opwaarts')
    elif 30 < last.RSI <= 48: sell += 1; reasons_sell.append('RSI neerwaarts')
    if last.MACD > last.MACD_Signal: buy += 1; reasons_buy.append('MACD boven signaal')
    elif last.MACD < last.MACD_Signal: sell += 1; reasons_sell.append('MACD onder signaal')
    if last.Close > last.EMA21: buy += 1; reasons_buy.append('Koers boven EMA21')
    elif last.Close < last.EMA21: sell += 1; reasons_sell.append('Koers onder EMA21')
    if htf == 'STIJGEND': buy += 1; reasons_buy.append('Hoger timeframe stijgend')
    elif htf == 'DALEND': sell += 1; reasons_sell.append('Hoger timeframe dalend')
    if last.RSI >= 70: buy -= 1
    if last.RSI <= 30: sell -= 1
    # A true hard filter: don't trade against HTF trend; sideways = no setup.
    signal, sign, reasons = 'AFWACHTEN', 0, ['Geen setup met voldoende bevestigingen.']
    if htf == 'STIJGEND' and buy >= 4 and buy >= sell + 2:
        signal, sign, reasons = 'BUY SETUP', 1, reasons_buy
    elif htf == 'DALEND' and sell >= 4 and sell >= buy + 2:
        signal, sign, reasons = 'SELL SETUP', -1, reasons_sell
    price, atr = float(last.Close), float(last.ATR)
    stop = price - sign * sl_atr * atr if sign else np.nan
    target = price + sign * sl_atr * atr * rr if sign else np.nan
    warning = bool((sign == 1 and (last.EMA9 < previous.EMA9 or last.MACD < last.MACD_Signal)) or
                   (sign == -1 and (last.EMA9 > previous.EMA9 or last.MACD > last.MACD_Signal)))
    return dict(signal=signal, sign=sign, price=price, sl=stop, tp=target, atr=atr,
                rsi=float(last.RSI), htf=htf, buy_score=buy, sell_score=sell,
                score=max(buy,sell), reasons=reasons, exit_warning=warning,
                candle=str(df.index[-1]), rr=rr)
