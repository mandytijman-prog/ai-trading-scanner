import unittest
import numpy as np
import pandas as pd
from scanner_core import closed_candles, normalize_ohlcv, indicators, analyze

class ScannerTests(unittest.TestCase):
    def sample(self, n=100):
        ix=pd.date_range('2026-10-01',periods=n,freq='15min',tz='UTC')
        v=np.linspace(100,120,n)
        return pd.DataFrame({'Open':v,'High':v+1,'Low':v-1,'Close':v,'Volume':100},index=ix)
    def test_incomplete_candle_excluded(self):
        df=self.sample(4)
        result=closed_candles(df,'15m',pd.Timestamp('2026-10-01 00:50',tz='UTC'))
        self.assertEqual(len(result),3)
    def test_timezone_required(self):
        df=self.sample(2)
        df.index=df.index.tz_localize(None)
        with self.assertRaises(ValueError): closed_candles(df,'15m')
    def test_indicators_valid(self):
        df=indicators(self.sample())
        self.assertTrue(len(df)>30)
        self.assertTrue(np.isfinite(df[['EMA9','EMA21','RSI','ATR']].to_numpy()).all())
    def test_risk_reward(self):
        df=indicators(self.sample())
        result=analyze(df,df,sl_atr=1.5,rr=2)
        self.assertEqual(result['signal'],'BUY SETUP')
        self.assertAlmostEqual((result['tp']-result['price'])/(result['price']-result['sl']),2)
    def test_unknown_higher_trend_fails_closed(self):
        df=indicators(self.sample())
        with self.assertRaises(ValueError): analyze(df,df.head(2))
if __name__=='__main__': unittest.main()
