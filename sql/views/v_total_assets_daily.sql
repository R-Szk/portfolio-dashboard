-- 日次総資産推移ビュー
-- 各営業日における全銘柄の評価額合計・累積原資額を計算
-- 株式: その日の終値 × 当日時点の保有数量 × 為替レート
-- 投信: 最新基準価額（固定）× 当日時点の保有口数 / 10000
-- 株式価格・為替レートは欠損日を直近値で補完
CREATE OR REPLACE VIEW v_total_assets_daily AS
WITH
-- 株式価格の営業日を日付軸として使用
trading_days AS (
    SELECT DISTINCT price_date AS dt
    FROM prices_daily pd
    JOIN instruments i ON pd.instrument_id = i.instrument_id
    WHERE i.instrument_type = 'stock'
),
-- 各銘柄の各日付時点の保有数量（取引履歴から累計計算）
holdings_per_day AS (
    SELECT
        td.dt,
        t.account_id,
        t.instrument_id,
        SUM(CASE WHEN t.trade_type = 'buy'  THEN t.quantity ELSE 0 END) AS cum_buy_qty,
        SUM(CASE WHEN t.trade_type = 'sell' THEN t.quantity ELSE 0 END) AS cum_sell_qty,
        SUM(CASE WHEN t.trade_type = 'buy'  THEN t.quantity ELSE -t.quantity END) AS net_qty
    FROM trading_days td
    JOIN transactions t ON t.trade_datetime::date <= td.dt
    GROUP BY td.dt, t.account_id, t.instrument_id
    HAVING SUM(CASE WHEN t.trade_type = 'buy' THEN t.quantity ELSE -t.quantity END) > 0
),
-- 全銘柄×全営業日の組み合わせを生成
instrument_days AS (
    SELECT DISTINCT
        td.dt,
        i.instrument_id,
        i.instrument_type,
        i.currency
    FROM trading_days td
    CROSS JOIN instruments i
    WHERE i.instrument_type = 'stock'
),
-- 株式価格を直近値で補完
stock_prices_filled AS (
    SELECT
        id.dt,
        id.instrument_id,
        id.currency,
        (
            SELECT pd.close_price
            FROM prices_daily pd
            WHERE pd.instrument_id = id.instrument_id
              AND pd.price_date <= id.dt
            ORDER BY pd.price_date DESC
            LIMIT 1
        ) AS close_price
    FROM instrument_days id
),
-- 投信の最新価格（全日付で固定）
mutual_fund_prices AS (
    SELECT DISTINCT ON (instrument_id)
        instrument_id,
        close_price,
        currency
    FROM prices_daily
    ORDER BY instrument_id, price_date DESC
),
-- 為替レート（直近値で補完）
fx_per_day AS (
    SELECT DISTINCT ON (td.dt)
        td.dt,
        fx.rate AS usd_jpy_rate
    FROM trading_days td
    LEFT JOIN fx_rates_daily fx ON fx.rate_date <= td.dt
        AND fx.currency_pair = 'USD/JPY'
    ORDER BY td.dt, fx.rate_date DESC
),
-- 日次累積原資額（その日までの累積買付額 - 累積売却額、円換算）
cost_basis_per_day AS (
    SELECT
        td.dt,
        SUM(
            CASE WHEN t.trade_type = 'buy'
                THEN t.amount * COALESCE(t.fx_rate, 1)
                ELSE 0
            END
        ) AS cum_buy_amount_jpy,
        SUM(
            CASE WHEN t.trade_type = 'sell'
                THEN t.amount * COALESCE(t.fx_rate, 1)
                ELSE 0
            END
        ) AS cum_sell_amount_jpy
    FROM trading_days td
    JOIN transactions t ON t.trade_datetime::date <= td.dt
    GROUP BY td.dt
)
SELECT
    hd.dt AS price_date,
    -- 総評価額
    SUM(
        CASE
            WHEN i.instrument_type = 'mutual_fund' THEN
                hd.net_qty / 10000.0 * COALESCE(mfp.close_price, 0)
            WHEN i.currency = 'USD' THEN
                hd.net_qty * COALESCE(spf.close_price, 0) * COALESCE(fx.usd_jpy_rate, 1)
            ELSE
                hd.net_qty * COALESCE(spf.close_price, 0)
        END
    ) AS total_assets_jpy,
    -- 内訳
    SUM(
        CASE
            WHEN i.instrument_type = 'mutual_fund' THEN
                hd.net_qty / 10000.0 * COALESCE(mfp.close_price, 0)
            ELSE 0
        END
    ) AS mutual_fund_value_jpy,
    SUM(
        CASE
            WHEN i.instrument_type = 'stock' AND i.currency = 'JPY' THEN
                hd.net_qty * COALESCE(spf.close_price, 0)
            ELSE 0
        END
    ) AS stock_jpy_value,
    SUM(
        CASE
            WHEN i.instrument_type = 'stock' AND i.currency = 'USD' THEN
                hd.net_qty * COALESCE(spf.close_price, 0) * COALESCE(fx.usd_jpy_rate, 1)
            ELSE 0
        END
    ) AS stock_usd_value_jpy,
    -- 累積原資額（買付額 - 売却額）
    cb.cum_buy_amount_jpy - cb.cum_sell_amount_jpy AS cost_basis_jpy,
    cb.cum_buy_amount_jpy,
    cb.cum_sell_amount_jpy
FROM holdings_per_day hd
JOIN instruments i ON hd.instrument_id = i.instrument_id
LEFT JOIN stock_prices_filled spf ON spf.instrument_id = hd.instrument_id
    AND spf.dt = hd.dt
    AND i.instrument_type = 'stock'
LEFT JOIN mutual_fund_prices mfp ON mfp.instrument_id = hd.instrument_id
    AND i.instrument_type = 'mutual_fund'
LEFT JOIN fx_per_day fx ON fx.dt = hd.dt
JOIN cost_basis_per_day cb ON cb.dt = hd.dt
GROUP BY hd.dt, cb.cum_buy_amount_jpy, cb.cum_sell_amount_jpy
ORDER BY hd.dt;