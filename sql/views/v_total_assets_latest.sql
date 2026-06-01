-- 総資産の最新値ビュー（KPI用）
CREATE OR REPLACE VIEW v_total_assets_latest AS
SELECT *
FROM v_total_assets_daily
ORDER BY price_date DESC
LIMIT 1;