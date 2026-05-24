"""yfinance を使った個別株(米国・日本)の価格取得スクリプト

instruments テーブルから price_source='yfinance' の銘柄を取得し、
transactions の最も古い取引日から今日までの日次価格を取得して
prices_daily テーブルに投入する。

重複は prices_daily の PRIMARY KEY (instrument_id, price_date) で防止。
"""

import os
import yfinance as yf
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_target_instruments(cur):
    """price_source='yfinance' の銘柄一覧を取得"""
    cur.execute(
        """
        SELECT instrument_id, ticker, currency
        FROM instruments
        WHERE price_source = 'yfinance'
        ORDER BY ticker
        """
    )
    return cur.fetchall()


def get_oldest_trade_date(cur):
    """transactions の最も古い trade_datetime の日付を返す"""
    cur.execute("SELECT MIN(trade_datetime)::date FROM transactions")
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def fetch_prices(ticker, start_date, end_date):
    """指定期間の日次終値を取得
    
    Returns:
        list of (price_date, close_price) tuples
    """
    t = yf.Ticker(ticker)
    df = t.history(start=start_date, end=end_date, interval="1d")
    
    if df.empty:
        return []
    
    results = []
    for idx, row in df.iterrows():
        # idx は タイムゾーン付きの datetime。日付だけ取り出す
        price_date = idx.date()
        close_price = float(row["Close"])
        results.append((price_date, close_price))
    
    return results


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # 対象銘柄を取得
    instruments = get_target_instruments(cur)
    print(f"対象銘柄数: {len(instruments)}")
    
    # 取得開始日を決定
    oldest_date = get_oldest_trade_date(cur)
    if oldest_date is None:
        print("取引データがありません")
        return
    
    # yfinance の end_date は exclusive なので明日の日付を渡す
    end_date = date.today() + timedelta(days=1)
    print(f"取得期間: {oldest_date} 〜 {date.today()}")
    
    total_inserted = 0
    for instrument_id, ticker, currency in instruments:
        try:
            print(f"\n{ticker} (id={instrument_id}, currency={currency}) を取得中...")
            price_data = fetch_prices(ticker, oldest_date, end_date)
            
            if not price_data:
                print(f"  データなし")
                continue
            
            # INSERT用のタプル作成
            rows = [
                (instrument_id, price_date, close_price, currency)
                for price_date, close_price in price_data
            ]
            
            insert_sql = """
                INSERT INTO prices_daily (instrument_id, price_date, close_price, currency)
                VALUES %s
                ON CONFLICT (instrument_id, price_date) DO NOTHING
            """
            execute_values(cur, insert_sql, rows)
            inserted = cur.rowcount
            total_inserted += inserted
            print(f"  取得: {len(price_data)}件、INSERT: {inserted}件(重複スキップ含む)")
        
        except Exception as e:
            print(f"  エラー: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n合計 INSERT: {total_inserted}件")
    print("完了")


if __name__ == "__main__":
    main()