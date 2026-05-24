-- transactions.fx_rate を約定日の USD/JPY レートで補完
-- 対象:currency = 'USD' かつ fx_rate IS NULL のレコード
-- 約定日のレートが取れなかった場合(週末等)は、その直前の営業日のレートを使う

UPDATE transactions t
SET fx_rate = sub.rate
FROM (
    SELECT
        t.transaction_id,
        (
            SELECT fx.rate
            FROM fx_rates_daily fx
            WHERE fx.currency_pair = 'USD/JPY'
              AND fx.rate_date <= (t.trade_datetime AT TIME ZONE 'Asia/Tokyo')::date
            ORDER BY fx.rate_date DESC
            LIMIT 1
        ) AS rate
    FROM transactions t
    WHERE t.currency = 'USD' AND t.fx_rate IS NULL
) sub
WHERE t.transaction_id = sub.transaction_id
  AND sub.rate IS NOT NULL;