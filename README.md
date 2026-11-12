# AI Trading Signal Scanner (gratis prototype)

## Wat zit erin?
- Marktkeuze: XAUUSD (goud) en XAGUSD (zilver)
- Timeframes: 15m, 1h en 1d
- Technische analyse: EMA 9/21, RSI 14, MACD en ATR 14
- Uitkomst: BUY SETUP, SELL SETUP of NO TRADE
- Indicatieve ATR-gebaseerde stop-loss en take-profit
- Grafiek en recente indicatorwaarden
- Alleen signalen: er worden **geen orders** geplaatst

## Belangrijke datanoot
De app probeert eerst Yahoo Finance-symbolen `XAUUSD=X` en `XAGUSD=X`.
Als die niet beschikbaar zijn, gebruikt hij `GC=F` en `SI=F` als futures-proxy.
Futuresprijzen zijn niet exact hetzelfde als spot XAUUSD/XAGUSD-prijzen.
Yahoo Finance-data kan vertraagd of onvolledig zijn. Vergelijk ieder signaal met je brokerkoers.

## Lokaal starten (Windows)
1. Installeer Python 3.10 of nieuwer: https://www.python.org/downloads/
2. Pak de ZIP uit.
3. Open de map in Terminal / Opdrachtprompt.
4. Voer uit:

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

De app opent normaal gesproken in je browser op `http://localhost:8501`.

## Eerste test
- Kies XAUUSD.
- Kies 1h.
- Klik op Vernieuw data.
- Controleer de gebruikte ticker en laatste candle.
- Laat de app minimaal op demo-/observatiestand draaien en noteer elk signaal vóór je beoordeelt wat er daarna gebeurde.

## Beperkingen / volgende ontwikkelstappen
1. Betrouwbare brokerdata-feed en tijdstempelvalidatie.
2. Historische backtest inclusief spread, commissie en slippage.
3. Nieuwsfilter voor CPI, NFP, FOMC en rente-events.
4. Multi-timeframe bevestiging (bijv. 4h trend + 1h setup).
5. Telegrammeldingen en logging van ieder signaal.
6. Paper-trading dashboard en statistieken.

Deze versie geeft technische setups, geen bewezen winstgevende strategie en geen financieel advies.
