"""SBI証券 投信取引履歴の取込スクリプト

CSVには NISA口座 / 特定口座の取引が混在するため、
「預り」列を見て account_id を振り分ける。
"""

import os
import unicodedata
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import pytz
from dotenv import load_dotenv
from pathlib import Path

# .envから接続情報読み込み
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# プロジェクトルートを基準にパスを解決
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "sbi_tsumitate.csv"

# 銘柄マスタ:CSV内の正規化済み銘柄名 → ticker, 表示名
# CSVの銘柄名は全角英数字を含むので、unicodedata.normalize("NFKC", ...) で正規化した文字列をキーにする
INSTRUMENT_MAPPING = {
    "SBI日本高配当株式(分配)ファンド(年4回決算型)": {
        "ticker": "sbi_jp_high_div",
        "name": "SBI日本高配当株式(分配)ファンド(年4回決算型)",
    },
    "iFreeNEXT FANG+インデックス": {
        "ticker": "ifree_fang_plus",
        "name": "iFreeNEXT FANG+インデックス",
    },
    "SBI・V・S&P500インデックス・ファンド": {
        "ticker": "sbi_v_sp500",
        "name": "SBI・V・S&P500インデックス・ファンド",
    },
    "eMAXIS Slim バランス(8資産均等型)": {
        "ticker": "emaxis_slim_balance_8",
        "name": "eMAXIS Slim バランス(8資産均等型)",
    },
    "楽天・全米株式インデックス・ファンド": {
        "ticker": "rakuten_us_total",
        "name": "楽天・全米株式インデックス・ファンド",
    },
    "イノベーション・インデックス・AI": {
        "ticker": "innovation_index_ai",
        "name": "イノベーション・インデックス・AI",
    },
    "J-REIT・リサーチ・オープン(年2回決算型)": {
        "ticker": "jreit_research_open",
        "name": "J-REIT・リサーチ・オープン(年2回決算型)",
    },
    "ノーロード明治安田社債アクティブ": {
        "ticker": "noload_meiji_yasuda_bond",
        "name": "ノーロード明治安田社債アクティブ",
    },
}

# 取引種別のマッピング
TRADE_TYPE_MAPPING = {
    "投信金額買付": "buy",
    "分配金再投資": "buy",  # 再投資も買付として扱う
    "投信金額解約": "sell",
}

# 「預り」列の値 → account_name の振り分け
# NFKC正規化後の値で判定
DEPOSIT_TO_ACCOUNT = {
    "NISA(成)": "SBI_NISA",
    "NISA(つ)": "SBI_NISA",
    "旧つみたてNISA": "SBI_NISA",
    "特定": "SBI_TOKUTEI",
    "特定/一般": "SBI_TOKUTEI",
}


def normalize_jp_text(s):
    """全角英数字・記号を半角に正規化、前後の空白を除去"""
    if pd.isna(s):
        return s
    return unicodedata.normalize("NFKC", str(s)).strip()


def parse_trade_date(date_str):
    """SBIの日付文字列(2026/04/10)をJST 9:00相当のUTC datetimeに変換"""
    if pd.isna(date_str):
        return None
    naive_dt = datetime.strptime(date_str, "%Y/%m/%d")
    jst = pytz.timezone("Asia/Tokyo")
    aware_dt = jst.localize(naive_dt.replace(hour=9, minute=0, second=0))
    return aware_dt.astimezone(pytz.UTC)


def main():
    # CSV読み込み:先頭8行はメタデータ・空行なのでスキップ、9行目を列名として扱う
    df = pd.read_csv(CSV_PATH, encoding="cp932", skiprows=8)
    print(f"CSV読み込み: {len(df)}件")

    # 銘柄名を正規化
    df["normalized_name"] = df["銘柄"].apply(normalize_jp_text)

    # 預り(口座区分)を正規化
    df["normalized_deposit"] = df["預り"].apply(normalize_jp_text)

    # 取引種別をマッピング
    df["trade_type"] = df["取引"].map(TRADE_TYPE_MAPPING)

    # 約定日をパース
    df["trade_datetime_utc"] = df["約定日"].apply(parse_trade_date)

    # 必須項目チェック
    required_cols = [
        "normalized_name",
        "normalized_deposit",
        "trade_type",
        "trade_datetime_utc",
        "約定数量",
        "約定単価",
        "受渡金額/決済損益",
    ]
    before = len(df)
    df = df.dropna(subset=required_cols).copy()
    after = len(df)
    print(f"必須項目あり: {after}件(除外: {before - after}件)")

    # 銘柄マスタとマッチしないものを警告
    unknown_instruments = df[~df["normalized_name"].isin(INSTRUMENT_MAPPING.keys())]
    if len(unknown_instruments) > 0:
        print(
            f"\n警告: 銘柄マスタに未登録の銘柄が {len(unknown_instruments)} 件あります"
        )
        print(unknown_instruments["normalized_name"].unique())
        print("INSTRUMENT_MAPPING に追加してから再実行してください\n")
        df = df[df["normalized_name"].isin(INSTRUMENT_MAPPING.keys())].copy()

    # 預り(口座)が未登録のものを警告
    unknown_deposits = df[~df["normalized_deposit"].isin(DEPOSIT_TO_ACCOUNT.keys())]
    if len(unknown_deposits) > 0:
        print(
            f"\n警告: 振り分け先口座が未定義の取引が {len(unknown_deposits)} 件あります"
        )
        print(unknown_deposits["normalized_deposit"].unique())
        print("DEPOSIT_TO_ACCOUNT に追加してから再実行してください\n")
        df = df[df["normalized_deposit"].isin(DEPOSIT_TO_ACCOUNT.keys())].copy()

    # ticker と account_name を追加
    df["ticker"] = df["normalized_name"].apply(
        lambda n: INSTRUMENT_MAPPING[n]["ticker"]
    )
    df["account_name"] = df["normalized_deposit"].map(DEPOSIT_TO_ACCOUNT)

    # 振り分け結果のサマリー
    print("\n口座別の取込予定件数:")
    print(df["account_name"].value_counts())

    # DB接続
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # account_name -> account_id マップを取得
    cur.execute("SELECT account_name, account_id FROM accounts")
    account_name_to_id = {name: aid for name, aid in cur.fetchall()}

    # 必要な口座が登録されているか確認
    needed_accounts = set(df["account_name"].unique())
    missing_accounts = needed_accounts - set(account_name_to_id.keys())
    if missing_accounts:
        raise RuntimeError(
            f"以下の口座が accounts テーブルに登録されていません: {missing_accounts}\n"
            "INSERT INTO accounts ... を先に実行してください"
        )

    # instruments のupsert
    inserted_instruments = 0
    for normalized_name, info in INSTRUMENT_MAPPING.items():
        if normalized_name not in df["normalized_name"].values:
            continue
        cur.execute(
            """
            INSERT INTO instruments (ticker, name, instrument_type, currency, price_source)
            VALUES (%s, %s, 'mutual_fund', 'JPY', 'toushin')
            ON CONFLICT (ticker) DO NOTHING
            """,
            (info["ticker"], info["name"]),
        )
        if cur.rowcount > 0:
            inserted_instruments += 1
    print(f"\ninstruments 新規追加: {inserted_instruments}件")

    # ticker -> instrument_id マップ
    cur.execute("SELECT ticker, instrument_id FROM instruments")
    ticker_to_id = {ticker: iid for ticker, iid in cur.fetchall()}

    # transactions のINSERT
    rows_to_insert = []
    for _, row in df.iterrows():
        instrument_id = ticker_to_id.get(row["ticker"])
        account_id = account_name_to_id.get(row["account_name"])
        if instrument_id is None or account_id is None:
            print(f"警告: skip ticker={row['ticker']} account={row['account_name']}")
            continue

        unit_price = float(row["約定単価"])
        quantity = float(row["約定数量"])
        amount = float(row["受渡金額/決済損益"])

        # 手数料は "--" の場合があるのでケア
        fee_raw = row["手数料/諸経費等"]
        fee = (
            0.0
            if pd.isna(fee_raw) or str(fee_raw).strip() == "--"
            else float(fee_raw)
        )

        rows_to_insert.append(
            (
                account_id,
                instrument_id,
                row["trade_datetime_utc"],
                row["trade_type"],
                quantity,
                unit_price,
                amount,
                fee,
                "JPY",
                None,  # fx_rate(JPYなので不要)
            )
        )

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

    print("\n完了")


if __name__ == "__main__":
    main()