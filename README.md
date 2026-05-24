# 個人資産運用ダッシュボード

複数の証券口座(moomoo、SBI証券)を横断した資産運用データを統合・可視化する個人向けデータ基盤。データソースの取得からデータマート構築、BIツールでの可視化まで一気通貫で実装。

## 技術スタック

- **DB**: Neon (Serverless PostgreSQL)
- **取込・バッチ**: Python (pandas, psycopg2, yfinance)
- **可視化**: Looker Studio
- **自動化(予定)**: Cloud Run + Cloud Scheduler

## ディレクトリ構成

```
portfolio-dashboard/
├── sql/
│   ├── schema/       # スキーマDDL
│   ├── views/        # 集計ビュー
│   └── migrations/   # データ補完SQL
├── src/
│   ├── importers/    # 証券会社CSV取込
│   └── prices/       # 価格・為替取得
├── scripts/          # 開発用スクリプト
└── data/             # CSV(Git管理外)
```

## セットアップ

```bash
# 環境変数の設定
cp .env.example .env
# .env を編集して、NeonのDATABASE_URLを設定

# Python仮想環境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# スキーマとビューの投入
source .env
for f in sql/schema/*.sql sql/views/*.sql; do
  psql "$DATABASE_URL" -f "$f"
done
```

## データ取込

```bash
# CSV取込(data/配下にCSVを配置してから)
python -m src.importers.moomoo
python -m src.importers.sbi

# 価格・為替の取得
python -m src.prices.stocks
python -m src.prices.fx
```