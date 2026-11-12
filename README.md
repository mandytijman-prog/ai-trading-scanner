# AI Trading Scanner v2

Streamlit-signaaldashboard voor XAUUSD (goud) en XAGUSD (zilver).

## Bestanden
- `app.py` — Streamlit-app
- `requirements.txt` — Python-dependencies

## Lokaal starten
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publiceren
Zet `app.py`, `requirements.txt` en `README.md` in de hoofdmap van je GitHub-repository.
Deploy via Streamlit Community Cloud met:
- Branch: `main`
- Main file path: `app.py`

## Functies
- Automatische verversing (30, 60, 120 of 300 seconden)
- BUY SETUP / SELL SETUP / AFWACHTEN
- Exit-waarschuwing bij verzwakkend momentum
- EMA 9/21, RSI, MACD, ATR en hoger-timeframe-filter
- Indicatieve ATR-gebaseerde SL/TP
- Signaalwisselingen-tijdlijn binnen de actieve sessie

## Belangrijk
Dit is een educatief, regelgebaseerd prototype. Het is geen financieel advies, geen gegarandeerd winstgevend systeem en plaatst geen orders. Yahoo Finance-data kan vertraagd zijn en kan afwijken van brokerkoersen. De getoonde signaalsterkte is geen statistische win kans. Test eerst op een demo-account.
