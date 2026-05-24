-- 月次の投入額(買付ベース)
-- JST基準で月を計算
CREATE OR REPLACE VIEW v_monthly_investment AS
SELECT
    DATE_TRUNC('month', t.trade_datetime AT TIME ZONE 'Asia/Tokyo')::DATE AS month,
    a.account_name,
    i.currency,
    SUM(CASE WHEN t.trade_type = 'buy' THEN t.amount ELSE 0 END) AS buy_amount,
    SUM(CASE WHEN t.trade_type = 'sell' THEN t.amount ELSE 0 END) AS sell_amount,
    SUM(CASE WHEN t.trade_type = 'buy' THEN t.amount ELSE -t.amount END) AS net_amount,
    COUNT(*) AS trade_count
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
JOIN instruments i ON t.instrument_id = i.instrument_id
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2;