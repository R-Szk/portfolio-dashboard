-- 現在の保有状況ビュー
-- 各 account × instrument ごとに、保有数量、平均取得単価、評価額、損益を計算
-- 株式は yfinance、投信は対応外(現在価格 NULL)

CREATE OR REPLACE VIEW v_holdings_current AS
WITH
-- 銘柄ごとの累計買付・売却数量、買付額(取引通貨ベース)
trade_summary AS (
    SELECT
        t.account_id,
        t.instrument_id,
        SUM(CASE WHEN t.trade_type = 'buy' THEN t.quantity ELSE 0 END) AS total_buy_qty,
        SUM(CASE WHEN t.trade_type = 'sell' THEN t.quantity ELSE 0 END) AS total_sell_qty,
        -- 買付金額(取引通貨ベース)
        SUM(CASE WHEN t.trade_type = 'buy' THEN t.amount ELSE 0 END) AS total_buy_amount_local,
        -- 売却金額(取引通貨ベース)
        SUM(CASE WHEN t.trade_type = 'sell' THEN t.amount ELSE 0 END) AS total_sell_amount_local,
        -- 買付金額(円換算、約定時の fx_rate を使用)
        SUM(CASE WHEN t.trade_type = 'buy'
                 THEN t.amount * COALESCE(t.fx_rate, 1)
                 ELSE 0 END) AS total_buy_amount_jpy,
        -- 売却金額(円換算)
        SUM(CASE WHEN t.trade_type = 'sell'
                 THEN t.amount * COALESCE(t.fx_rate, 1)
                 ELSE 0 END) AS total_sell_amount_jpy
    FROM transactions t
    GROUP BY t.account_id, t.instrument_id
),
-- 各銘柄の最新価格
latest_prices AS (
    SELECT DISTINCT ON (instrument_id)
        instrument_id,
        close_price AS latest_price,
        price_date AS latest_price_date,
        currency AS price_currency
    FROM prices_daily
    ORDER BY instrument_id, price_date DESC
),
-- 最新のUSD/JPYレート
latest_fx AS (
    SELECT rate AS usd_jpy_rate, rate_date
    FROM fx_rates_daily
    WHERE currency_pair = 'USD/JPY'
    ORDER BY rate_date DESC
    LIMIT 1
)
SELECT
    a.account_name,
    i.ticker,
    i.name AS instrument_name,
    i.instrument_type,
    i.currency AS instrument_currency,
    -- 数量
    ts.total_buy_qty,
    ts.total_sell_qty,
    (ts.total_buy_qty - ts.total_sell_qty) AS net_quantity,
    -- 平均取得単価(取引通貨ベース、全期間買付の加重平均)
    CASE
        WHEN ts.total_buy_qty > 0 THEN ts.total_buy_amount_local / ts.total_buy_qty
        ELSE NULL
    END AS avg_buy_price_local,
    -- 現在価格
    lp.latest_price,
    lp.latest_price_date,
    -- 評価額(取引通貨ベース)
    CASE
        WHEN lp.latest_price IS NOT NULL
        THEN (ts.total_buy_qty - ts.total_sell_qty) * lp.latest_price
        ELSE NULL
    END AS market_value_local,
    -- 評価額(円換算)
    CASE
        WHEN lp.latest_price IS NOT NULL
        THEN
            (ts.total_buy_qty - ts.total_sell_qty) * lp.latest_price
            * CASE WHEN i.currency = 'USD' THEN lf.usd_jpy_rate ELSE 1 END
        ELSE NULL
    END AS market_value_jpy,
    -- 取得原価(円換算、保有分のみ)
    CASE
        WHEN ts.total_buy_qty > 0
        THEN (ts.total_buy_qty - ts.total_sell_qty) * (ts.total_buy_amount_jpy / ts.total_buy_qty)
        ELSE 0
    END AS cost_basis_jpy,
    -- 損益(円換算)= 評価額 - 取得原価
    CASE
        WHEN lp.latest_price IS NOT NULL AND ts.total_buy_qty > 0
        THEN
            (ts.total_buy_qty - ts.total_sell_qty) * lp.latest_price
            * CASE WHEN i.currency = 'USD' THEN lf.usd_jpy_rate ELSE 1 END
            - (ts.total_buy_qty - ts.total_sell_qty) * (ts.total_buy_amount_jpy / ts.total_buy_qty)
        ELSE NULL
    END AS unrealized_pl_jpy,
    -- 累計売却額(円換算、実現損益の参考値として)
    ts.total_sell_amount_jpy,
    -- 累計買付額(円換算)
    ts.total_buy_amount_jpy
FROM trade_summary ts
JOIN accounts a ON ts.account_id = a.account_id
JOIN instruments i ON ts.instrument_id = i.instrument_id
LEFT JOIN latest_prices lp ON ts.instrument_id = lp.instrument_id
CROSS JOIN latest_fx lf
WHERE (ts.total_buy_qty - ts.total_sell_qty) <> 0  -- 保有数量が0のものは除外
ORDER BY a.account_name, i.ticker;