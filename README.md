# 個人資産運用ダッシュボード

複数の証券口座(moomoo、SBI証券)を横断した資産運用の可視化と、投資判断の振り返りができる個人向けデータ基盤。

## 構成

- データベース:Neon (Serverless PostgreSQL)
- バッチ処理:Cloud Run + Cloud Scheduler(予定)
- 可視化:Looker Studio(モック、将来的にWeb/Androidアプリへ)

## セットアップ

1. `.env.example` を `.env` にコピーして、Neonの接続情報を入れる
2. 仮想環境を作成し、依存パッケージをインストール:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. スキーマを流し込む:
psql "$DATABASE_URL" -f sql/schema/001_initial.sql
psql "$DATABASE_URL" -f sql/schema/002_trade_datetime.sql

## 取込スクリプト
python -m src.importers.moomoo

## ディレクトリ構成
portfolio-dashboard/
├── sql/         # スキーマ・ビュー定義
├── src/         # 本番コード(取込、価格取得、Cloud Runエントリ)
├── scripts/     # 開発用スクリプト
├── data/        # CSV(Git管理外)
└── docker/      # Cloud Run用Dockerfile