-- 口座別の取引サマリー
CREATE OR REPLACE VIEW v_account_summary AS
SELECT
    a.account_name,
    a.broker,
    a.account_type,
    COUNT(DISTINCT t.instrument_id) AS instrument_count,
    COUNT(*) AS trade_count,
    COUNT(*) FILTER (WHERE t.trade_type = 'buy') AS buy_count,
    COUNT(*) FILTER (WHERE t.trade_type = 'sell') AS sell_count,
    SUM(CASE WHEN t.trade_type = 'buy' THEN t.amount ELSE 0 END) AS total_buy_amount,
    SUM(CASE WHEN t.trade_type = 'sell' THEN t.amount ELSE 0 END) AS total_sell_amount,
    MIN(t.trade_datetime) AS first_trade_at,
    MAX(t.trade_datetime) AS last_trade_at
FROM accounts a
LEFT JOIN transactions t ON a.account_id = t.account_id
GROUP BY a.account_name, a.broker, a.account_type;