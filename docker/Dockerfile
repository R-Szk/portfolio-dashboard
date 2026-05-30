# Cloud Run Jobs 用の Dockerfile
# 個別株の価格と USD/JPY レートを yfinance から取得して Neon に投入する

FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# システムパッケージは最小限。psycopg2-binary なのでビルドツールは不要

# 依存パッケージのインストール
# (キャッシュを効かせるため、コードコピー前に依存だけ先にインストール)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー(src/ のみ。scripts/、sql/、data/ は不要)
COPY src/ ./src/

# Cloud Run Jobs のエントリーポイント
CMD ["python", "-m", "src.main"]