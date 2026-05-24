import pandas as pd
from datetime import datetime
import pytz

CSV_PATH = "data/moomoo取引履歴.csv"

# CSV読み込み
# - encoding は utf-8-sig(BOM付きUTF-8)
# - thousands="," でカンマ区切りの数値を自動でパース
df = pd.read_csv(CSV_PATH, encoding="utf-8-sig", thousands=",")

print(f"読み込み件数: {len(df)}")

# ステップ1: 約定済のみに絞る
# 「約定数量」が NaN(空欄)でない行だけ残す
df_filled = df[df["約定数量"].notna()].copy()
print(f"約定済の件数: {len(df_filled)}")
print(f"除外された件数: {len(df) - len(df_filled)}")


# ステップ2: タイムゾーン付きの約定日時をパースしてUTCに統一
def parse_datetime_with_tz(s):
    """例: '2026/01/19 15:56:46 JST' を timezone-aware な datetime に変換し、UTCに正規化"""
    if pd.isna(s):
        return None
    # 末尾のタイムゾーン文字列を取り出す
    parts = s.rsplit(" ", 1)
    if len(parts) != 2:
        return None
    dt_str, tz_str = parts
    # JST と ET のマッピング
    tz_map = {
        "JST": "Asia/Tokyo",
        "ET": "America/New_York",  # ET は EST/EDT を含む
        "EST": "America/New_York",
        "EDT": "America/New_York",
    }
    tz_name = tz_map.get(tz_str)
    if tz_name is None:
        print(f"警告: 未知のタイムゾーン {tz_str}")
        return None
    naive_dt = datetime.strptime(dt_str, "%Y/%m/%d %H:%M:%S")
    local_tz = pytz.timezone(tz_name)
    aware_dt = local_tz.localize(naive_dt)
    return aware_dt.astimezone(pytz.UTC)


df_filled["約定日時_UTC"] = df_filled["約定日時"].apply(parse_datetime_with_tz)


# ステップ3: 銘柄コード変換(日本株は .T 付与)
def normalize_ticker(row):
    """通貨が JPY なら銘柄コードに .T を付ける"""
    code = str(row["銘柄コード"]).strip()
    if row["通貨"] == "JPY":
        return f"{code}.T"
    return code


df_filled["ticker_normalized"] = df_filled.apply(normalize_ticker, axis=1)


# ステップ4: 売買方向の正規化
trade_type_map = {"買い": "buy", "売り": "sell"}
df_filled["trade_type"] = df_filled["売買方向"].map(trade_type_map)


# 表示
print("\n--- 抽出結果(先頭5件) ---")
display_cols = [
    "ticker_normalized",
    "銘柄名",
    "trade_type",
    "約定数量",
    "約定価格",
    "約定金額",
    "約定日時_UTC",
    "通貨",
    "取引手数料",
]
print(df_filled[display_cols].head(5).to_string())

print("\n--- 通貨ごとの件数 ---")
print(df_filled["通貨"].value_counts())