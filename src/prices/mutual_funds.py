"""Yahoo Finance Japan から投資信託の基準価額を取得するスクリプト
instruments テーブルから price_source='yahoo_jp' の銘柄を取得し、
最新の基準価額を prices_daily テーブルに投入する。
※ Yahoo Finance Japan では最新価格のみ取得可能(履歴は取れない)
重複は prices_daily の UNIQUE (instrument_id, price_date) で防止。
"""
import os
import re
import json
import urllib.request
from datetime import date
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "ja,en;q=0.9",
}

def get_target_instruments(cur):
    """price_source='yahoo_jp' の銘柄一覧を取得"""
    cur.execute(
        """
        SELECT instrument_id, ticker, isin_or_code, currency
        FROM instruments
        WHERE price_source = 'yahoo_jp'
        ORDER BY ticker
        """
    )
    return cur.fetchall()

def fetch_price(isin_or_code):
    """Yahoo Finance Japan から最新の基準価額と基準日を取得

    Returns:
        (price_date, close_price) または None
    """
    url = f"https://finance.yahoo.co.jp/quote/{isin_or_code}"
    req = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(req, timeout=10) as res:
        raw = res.read().decode("utf-8", errors="replace")

    m = re.search(r'"fundPrices"\s*:\s*(\{[^}]+\})', raw)
    if not m:
        return None

    data = json.loads(m.group(1))
    price_str   = data.get("price", "")
    update_date = data.get("updateDate", "")  # 例: "05/29"

    if not price_str or not update_date:
        return None

    price = int(price_str.replace(",", ""))

    # updateDate は "MM/DD" 形式 → 当年の date に変換
    today = date.today()
    month, day = map(int, update_date.split("/"))
    year = today.year if today.month >= month else today.year - 1
    price_date = date(year, month, day)

    return price_date, price

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    instruments = get_target_instruments(cur)
    print(f"対象銘柄数: {len(instruments)}")

    if not instruments:
        print("price_source='yahoo_jp' の銘柄がありません")
        conn.close()
        return

    total_inserted = 0
    for instrument_id, ticker, isin_or_code, currency in instruments:
        try:
            print(f"\n{ticker} (code={isin_or_code}) を取得中...")
            result = fetch_price(isin_or_code)

            if result is None:
                print(f"  価格データ取得失敗")
                continue

            price_date, close_price = result
            print(f"  基準価額: {close_price:,}円 ({price_date})")

            execute_values(cur, """
                INSERT INTO prices_daily (instrument_id, price_date, close_price, currency)
                VALUES %s
                ON CONFLICT (instrument_id, price_date) DO NOTHING
            """, [(instrument_id, price_date, close_price, currency)])

            inserted = cur.rowcount
            total_inserted += inserted
            print(f"  INSERT: {inserted}件(0件は重複スキップ)")

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
