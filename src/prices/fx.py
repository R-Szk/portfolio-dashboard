"""yfinance を使った USD/JPY 日次レート取得スクリプト

USD/JPY の日次終値を取得して fx_rates_daily テーブルに投入する。
"""

import os
import yfinance as yf
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

CURRENCY_PAIR = "USD/JPY"
YF_TICKER = "JPY=X"  # yfinance での USD/JPY のティッカー


def get_oldest_trade_date(cur):
    """transactions の最も古い trade_datetime の日付を返す"""
    cur.execute("SELECT MIN(trade_datetime)::date FROM transactions")
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    oldest_date = get_oldest_trade_date(cur)
    if oldest_date is None:
        print("取引データがありません")
        return
    
    end_date = date.today() + timedelta(days=1)
    print(f"取得期間: {oldest_date} 〜 {date.today()}")
    
    # yfinance で USD/JPY を取得
    t = yf.Ticker(YF_TICKER)
    df = t.history(start=oldest_date, end=end_date, interval="1d")
    
    if df.empty:
        print("データが取得できませんでした")
        return
    
    print(f"取得行数: {len(df)}")
    
    rows = []
    for idx, row in df.iterrows():
        rate_date = idx.date()
        rate = float(row["Close"])
        rows.append((CURRENCY_PAIR, rate_date, rate))
    
    insert_sql = """
        INSERT INTO fx_rates_daily (currency_pair, rate_date, rate)
        VALUES %s
        ON CONFLICT (currency_pair, rate_date) DO NOTHING
    """
    execute_values(cur, insert_sql, rows)
    print(f"INSERT: {cur.rowcount}件(重複スキップ含む)")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("完了")


if __name__ == "__main__":
    main()