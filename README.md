# Trading Scanner v3 – voorstel voor Mandy

Verbeterde **educatieve** versie op basis van de publiek gedeelde v2-scanner.
De bestaande GitHub-repository is **niet gewijzigd**. Dit pakket is geen bewezen winstgevende bot en **plaatst geen orders**.

## Concrete verbeteringen
- Alleen volledig afgesloten candles, gecontroleerd met UTC-tijdstempels.
- Filter op verouderde marktdata en expliciete waarschuwing bij futures-proxy.
- Hoger timeframe is nu een harde voorwaarde; geen stilzwijgende fallback naar dezelfde candles.
- RSI randgevallen gecorrigeerd, indicators met warm-up periode.
- Instelbare ATR-stop en R:R; standaard 1:2 (niet automatisch een betere strategie).
- Regelscore in punten in plaats van misleidend winstkans-percentage.
- Signaalwisselingen per markt/timeframe/instellingen met CSV-export binnen sessie.
- Faal-veilig: bij ontbrekende of ongeldige data geen signaal.
- Kleine automatische eenheidstests.

## Starten
```bash
pip install -r requirements.txt
python -m unittest -v test_scanner_core.py
streamlit run app.py
```

Voor Streamlit Cloud: upload `app.py`, `scanner_core.py`, `requirements.txt` en `README.md` naar een **aparte testbranch of repository**; main file `app.py`. Niet direct de oude versie overschrijven.

## Bewuste beperkingen
- Dagtimeframe uitgeschakeld omdat er geen apart hoger timeframe in de oorspronkelijke gegevenskeuze beschikbaar is.
- Yahoo Finance is geen uitvoeringsbron voor een funded account.
- Geen echte achtergrondscanner: Streamlit kan inactief worden.
- Historie in sessie is niet duurzaam; CSV-download is handmatig.
- Geen empirische backtest of out-of-sample validatie.
- Geen MT5 orders, accountbeheer, lot sizing, spread/slippage of prop-firm compliance.
- De trendfilter kan voorkomen dat sommige kansen gesignaleerd worden; impact onbekend.

**Volgende stap:** onafhankelijke historische backtests met brokerdata, kosten en out-of-sample tests; daarna langdurig forward-testen op demo, voordat uitvoering zelfs overwogen wordt.
