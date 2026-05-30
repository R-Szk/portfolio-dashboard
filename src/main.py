"""Cloud Run Jobs のエントリーポイント
日次バッチとして、以下を順番に実行する:
1. 個別株の日次価格を yfinance から取得して prices_daily に投入
2. USD/JPY の日次レートを yfinance から取得して fx_rates_daily に投入
3. 投資信託の基準価額を Yahoo Finance Japan から取得して prices_daily に投入
ローカルでも `python -m src.main` で実行可能。
"""
import sys
import traceback
from datetime import datetime
from src.prices.stocks import main as stocks_main
from src.prices.fx import main as fx_main
from src.prices.mutual_funds import main as mutual_funds_main

def run_job(name, func):
    """個別のジョブを実行し、エラー時もログ出力して継続"""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().isoformat()}] {name} 開始")
    print('=' * 60)
    try:
        func()
        print(f"[{datetime.now().isoformat()}] {name} 完了")
        return True
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] {name} エラー: {e}")
        traceback.print_exc()
        return False

def main():
    print(f"日次バッチ開始: {datetime.now().isoformat()}")

    results = {
        "個別株価格取得":   run_job("個別株価格取得",   stocks_main),
        "為替レート取得":   run_job("為替レート取得",   fx_main),
        "投信基準価額取得": run_job("投信基準価額取得", mutual_funds_main),
    }

    print(f"\n{'='*60}")
    print("日次バッチ結果サマリー")
    print('=' * 60)
    for name, success in results.items():
        status = "成功" if success else "失敗"
        print(f"  {name}: {status}")

    if not all(results.values()):
        print("\n一部のジョブが失敗しました")
        sys.exit(1)

    print(f"\n全ジョブ正常完了: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
