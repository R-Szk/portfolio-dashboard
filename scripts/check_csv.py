import chardet
import pandas as pd

CSV_PATH = "data/SaveFile_000001_000108.csv"

# 文字コード判定
with open(CSV_PATH, "rb") as f:
    raw = f.read()
    result = chardet.detect(raw)
    print(f"判定された文字コード: {result['encoding']} (信頼度: {result['confidence']:.2%})")

# 判定結果でCSVを読んでみる
encoding = result['encoding']
df = pd.read_csv(CSV_PATH, encoding=encoding)

print(f"\n行数: {len(df)}")
print(f"列数: {len(df.columns)}")
print(f"\n列名一覧:")
for i, col in enumerate(df.columns):
    print(f"  {i+1}. {col}")

print(f"\n先頭3行のサンプル:")
print(df.head(3).to_string())