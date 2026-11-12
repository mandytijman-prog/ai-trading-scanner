"""AI Trading Scanner v3 - educational scanner; NEVER submits orders."""
import pandas as pd
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
from scanner_core import normalize_ohlcv, closed_candles, indicators, analyze

st.set_page_config(page_title='Trading Scanner v3', page_icon='📈', layout='wide')
st.title('📈 Trading Scanner v3')
st.caption('Educatieve regelgebaseerde scanner — GEEN automatische orders en GEEN bewezen AI-voorspelling.')
with st.sidebar:
    market = st.selectbox('Markt', ['Goud', 'Zilver'])
    timeframe = st.selectbox('Timeframe', ['15m','1h','1d'])
    refresh = st.selectbox('Refresh seconden', [30,60,120,300], index=1)
    sl_atr = st.slider('Stop-loss (× ATR)', 1.0, 3.0, 1.5, .25)
    rr = st.slider('Gewenste risk/reward', 1.0, 4.0, 2.0, .25)
    max_stale_bars = st.slider('Waarschuwing na aantal ontbrekende candles', 2, 12, 3)
    st.info('De koersbron is Yahoo Finance. Data kan vertraagd zijn of afwijken van de broker.')
st_autorefresh(interval=refresh*1000, key='refresh')
SYMBOLS = {'Goud': [('XAUUSD=X','spot'),('GC=F','futures-proxy')],
           'Zilver': [('XAGUSD=X','spot'),('SI=F','futures-proxy')]}
CFG = {'15m':('7d','15m','1h','60d'), '1h':('60d','1h','1d','2y'), '1d':('2y','1d','1d','2y')}
period, interval, higher_interval, higher_period = CFG[timeframe]
@st.cache_data(ttl=45, show_spinner=False)
def fetch(ticker, period, interval):
    raw = yf.download(ticker, period=period, interval=interval, auto_adjust=True,
                      progress=False, threads=False)
    return normalize_ohlcv(raw)

def load_closed(ticker, period, interval):
    return closed_candles(fetch(ticker,period,interval), interval)

try:
    selected = None
    for ticker, source in SYMBOLS[market]:
        d = load_closed(ticker,period,interval)
        if len(d) >= 50:
            selected = ticker, source, d
            break
    if selected is None:
        st.error('Onvoldoende gesloten koerscandles. Er wordt GEEN signaal gemaakt.')
        st.stop()
    ticker, source, prices = selected
    if timeframe == '1d':
        st.warning('Dagtimeframe heeft geen apart hoger timeframe in deze versie; alleen een dagelijks overzicht is beschikbaar.')
        st.stop()
    higher_prices = load_closed(ticker,higher_period,higher_interval)
    if len(higher_prices) < 50:
        st.error('Hoger timeframe ontbreekt; geen betrouwbare trendbevestiging. Geen signaal.')
        st.stop()
    start = pd.Timestamp(prices.index[-1]); now = pd.Timestamp.now(tz='UTC')
    if start.tz is None: raise ValueError('Koerstimestamps ontbreken timezone')
    duration = {'15m':pd.Timedelta(minutes=15),'1h':pd.Timedelta(hours=1)}[timeframe]
    age = now - (start.tz_convert('UTC') + duration)
    if age > duration * max_stale_bars:
        st.error(f'Koersdata is te oud ({age}). Geen signaal of handelsadvies mogelijk.')
        st.stop()
    data = indicators(prices)
    higher = indicators(higher_prices)
    result = analyze(data, higher, sl_atr=sl_atr, rr=rr)
except Exception as ex:
    st.error(f'Dataprobleem: {ex}. Scanner geeft daarom geen signaal.')
    st.stop()

st.caption(f'Bron: {ticker} ({source}) · laatste **afgesloten** candle: {result["candle"]} · {timeframe}')
if source == 'futures-proxy':
    st.warning('Futures-proxy gebruikt: deze prijs is NIET gelijk aan XAUUSD/XAGUSD bij jouw broker.')
if 'events' not in st.session_state: st.session_state.events=[]
if 'last' not in st.session_state: st.session_state.last={}
key=(market,timeframe,sl_atr,rr)
last=st.session_state.last.get(key)
current=(result['candle'],result['signal'])
if last != current:
    if last is not None and last[1] != current[1]:
        st.session_state.events.insert(0, dict(time=pd.Timestamp.now(tz='UTC').isoformat(),market=market,
            timeframe=timeframe,candle=result['candle'],before=last[1],after=result['signal']))
    st.session_state.last[key]=current
st.subheader(result['signal'])
if result['exit_warning']: st.warning('Momentum verzwakt: dit is een WAARSCHUWING, geen automatische exit.')
c1,c2,c3,c4=st.columns(4)
c1.metric('Indicatieve prijs',f'{result["price"]:.3f}')
c2.metric('Regelscore (GEEN winstkans)',f'{result["score"]} punten')
c3.metric('RSI',f'{result["rsi"]:.1f}')
c4.metric('Hoger timeframe',result['htf'])
a,b,c=st.columns(3)
a.metric('Indicatieve stop-loss','—' if pd.isna(result['sl']) else f'{result["sl"]:.3f}')
b.metric('Indicatief koersdoel','—' if pd.isna(result['tp']) else f'{result["tp"]:.3f}')
c.metric('Geplande R:R',f'1:{rr:g}' if result['sign'] else '—')
st.markdown('**Waarom dit signaal?**')
for reason in result['reasons']: st.write('•',reason)
st.line_chart(data[['Close','EMA9','EMA21']].tail(100))
st.subheader('Signaalwisselingen (alleen tijdens deze actieve sessie)')
if st.session_state.events:
    events=pd.DataFrame(st.session_state.events)
    st.dataframe(events,hide_index=True,use_container_width=True)
    st.download_button('Download deze sessie als CSV',events.to_csv(index=False).encode(),
                       file_name='signal-events.csv',mime='text/csv')
else:
    st.caption('Nog geen signaalwisselingen opgeslagen. Sluiten of herstarten kan de tijdlijn wissen.')
with st.expander('Belangrijke beperkingen'):
    st.write('Geen machine-learningmodel, geen statistische winstkans, geen broker-koppeling, '
             'geen 24/7 monitoringgarantie en geen orderuitvoering. Instelbare R:R is een rekenkundig doel, '
             'geen bewijs dat de markt dit doel kan bereiken. Stop-lossniveaus zijn zonder brokercontractgrootte, '
             'spread, slippage of transactiekosten berekend. Test uitvoerig met historische en demo-data.')
