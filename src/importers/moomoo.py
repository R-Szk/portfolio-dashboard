import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import pytz
from dotenv import load_dotenv
from pathlib import Path

# プロジェクトルートを基準にパスを解決
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "moomoo取引履歴.csv"

# .envから接続情報読み込み
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

ACCOUNT_NAME = "moomoo"  # accounts テーブルの account_name で検索する


def parse_datetime_with_tz(s):
    """タイムゾーン付き文字列をUTC datetimeに変換"""
    if pd.isna(s):
        return None
    parts = s.rsplit(" ", 1)
    if len(parts) != 2:
        return None
    dt_str, tz_str = parts
    tz_map = {
        "JST": "Asia/Tokyo",
        "ET": "America/New_York",
        "EST": "America/New_York",
        "EDT": "America/New_York",
    }
    tz_name = tz_map.get(tz_str)
    if tz_name is None:
        return None
    naive_dt = datetime.strptime(dt_str, "%Y/%m/%d %H:%M:%S")
    local_tz = pytz.timezone(tz_name)
    aware_dt = local_tz.localize(naive_dt)
    return aware_dt.astimezone(pytz.UTC)


def normalize_ticker(code, currency):
    """日本株の銘柄コードに .T を付与"""
    code = str(code).strip()
    if currency == "JPY":
        return f"{code}.T"
    return code


def main():
    # CSV読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", thousands=",")
    print(f"CSV読み込み: {len(df)}件")

    # 分割約定対応: 注文情報(銘柄コード、銘柄名、売買方向、通貨)を前行からffillで補完
    # moomooのCSVは1注文が複数回に分かれて約定した場合、2回目以降の行は注文情報が空欄になる
    fill_cols = ["売買方向", "銘柄コード", "銘柄名", "通貨"]
    df[fill_cols] = df[fill_cols].ffill()

    # 約定済かつ必須項目が揃っている行だけを残す
    required_cols = ["約定数量", "銘柄コード", "通貨", "売買方向", "約定日時"]
    before = len(df)
    df = df.dropna(subset=required_cols).copy()
    after = len(df)
    print(f"約定済かつ必須項目あり: {after}件(除外: {before - after}件)")

    # 各種変換
    df["trade_datetime_utc"] = df["約定日時"].apply(parse_datetime_with_tz)
    df["ticker"] = df.apply(
        lambda r: normalize_ticker(r["銘柄コード"], r["通貨"]), axis=1
    )
    df["trade_type"] = df["売買方向"].map({"買い": "buy", "売り": "sell"})

    # DB接続
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # account_id を取得
    cur.execute(
        "SELECT account_id FROM accounts WHERE account_name = %s", (ACCOUNT_NAME,)
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"口座 {ACCOUNT_NAME} が accounts テーブルに見つかりません")
    account_id = row[0]
    print(f"account_id: {account_id}")

    # instruments のupsert(銘柄ごと)
    unique_instruments = df.drop_duplicates(subset=["ticker"])[
        ["ticker", "銘柄名", "通貨"]
    ]

    inserted_instruments = 0
    for _, row in unique_instruments.iterrows():
        ticker = row["ticker"]
        name = row["銘柄名"]
        currency = row["通貨"]
        # 個別株判定: ticker に .T があれば日本株、それ以外は米国株
        # どちらも instrument_type は 'stock'
        cur.execute(
            """
            INSERT INTO instruments (ticker, name, instrument_type, currency, price_source)
            VALUES (%s, %s, 'stock', %s, 'yfinance')
            ON CONFLICT (ticker) DO NOTHING
            """,
            (ticker, name, currency),
        )
        if cur.rowcount > 0:
            inserted_instruments += 1
    print(f"instruments 新規追加: {inserted_instruments}件")

    # ticker -> instrument_id マップを作成
    cur.execute("SELECT ticker, instrument_id FROM instruments")
    ticker_to_id = {ticker: iid for ticker, iid in cur.fetchall()}

    # transactions のINSERT
    rows_to_insert = []
    for _, row in df.iterrows():
        instrument_id = ticker_to_id.get(row["ticker"])
        if instrument_id is None:
            print(f"警告: {row['ticker']} のinstrument_idが見つかりません")
            continue

        rows_to_insert.append(
            (
                account_id,
                instrument_id,
                row["trade_datetime_utc"],
                row["trade_type"],
                float(row["約定数量"]),
                float(row["約定価格"]),
                float(row["約定金額"]),
                float(row["取引手数料"]) if pd.notna(row["取引手数料"]) else 0.0,
                row["通貨"],
                None,  # fx_rate は後で別スクリプトで埋める
            )
        )

    # ON CONFLICT DO NOTHING で重複を避ける
    insert_sql = """
        INSERT INTO transactions (
            account_id, instrument_id, trade_datetime, trade_type,
            quantity, unit_price, amount, fee, currency, fx_rate
        ) VALUES %s
        ON CONFLICT ON CONSTRAINT uq_transactions_natural_key DO NOTHING
    """
    execute_values(cur, insert_sql, rows_to_insert)
    print(f"transactions INSERT: {cur.rowcount}件(重複スキップ含む)")

    conn.commit()
    cur.close()
    conn.close()

    print("完了")


if __name__ == "__main__":
    main()