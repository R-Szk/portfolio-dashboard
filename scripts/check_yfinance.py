"""yfinance の動作確認スクリプト
NVDA と 5020.T(ENEOS) の過去30日分の価格を取得してみる
"""

import yfinance as yf
from datetime import datetime, timedelta

# 過去30日分
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

tickers = ["NVDA", "5020.T"]

for ticker in tickers:
    print(f"\n=== {ticker} ===")
    t = yf.Ticker(ticker)
    df = t.history(start=start_date, end=end_date, interval="1d")
    
    if df.empty:
        print("データが取得できませんでした")
        continue
    
    print(f"取得行数: {len(df)}")
    print(f"列: {list(df.columns)}")
    print(f"\n最新3日分:")
    print(df.tail(3)[["Open", "High", "Low", "Close", "Volume"]])