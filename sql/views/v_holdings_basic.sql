-- 口座×銘柄ごとの取引サマリー（保有中のみ）
CREATE OR REPLACE VIEW v_holdings_basic AS
SELECT
    a.account_name,
    i.ticker,
    i.name AS instrument_name,
    i.instrument_type,
    i.currency,
    SUM(CASE WHEN t.trade_type = 'buy' THEN t.quantity ELSE 0 END) AS total_buy_quantity,
    SUM(CASE WHEN t.trade_type = 'sell' THEN t.quantity ELSE 0 END) AS total_sell_quantity,
    SUM(CASE WHEN t.trade_type = 'buy' THEN t.quantity ELSE -t.quantity END) AS net_quantity,
    SUM(CASE WHEN t.trade_type = 'buy' THEN t.amount ELSE 0 END) AS total_buy_amount,
    SUM(CASE WHEN t.trade_type = 'sell' THEN t.amount ELSE 0 END) AS total_sell_amount,
    COUNT(*) AS trade_count
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
JOIN instruments i ON t.instrument_id = i.instrument_id
GROUP BY a.account_name, i.ticker, i.name, i.instrument_type, i.currency
HAVING SUM(CASE WHEN t.trade_type = 'buy' THEN t.quantity ELSE -t.quantity END) > 0
ORDER BY a.account_name, i.ticker;