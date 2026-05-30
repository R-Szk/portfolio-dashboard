import urllib.request
import re
import json

funds = {
    "ifree_fang_plus":       "04311181",
    "sbi_jp_high_div":       "8931123C",
    "emaxis_slim_balance_8": "03312175",
    "sbi_v_sp500":           "89311199",
}

for ticker, fund_code in funds.items():
    url = f"https://finance.yahoo.co.jp/quote/{fund_code}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept-Language": "ja,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read().decode("utf-8", errors="replace")

        # fundPrices ブロックを抽出
        m = re.search(r'"fundPrices"\s*:\s*(\{[^}]+\})', raw)
        if m:
            data = json.loads(m.group(1))
            price_str = data.get("price", "")
            update_date = data.get("updateDate", "")
            price = int(price_str.replace(",", ""))
            print(f"{ticker}: {price:,}円 ({update_date})")
        else:
            print(f"{ticker}: fundPrices が見つからない")

    except Exception as e:
        print(f"{ticker}: ERROR {e}")