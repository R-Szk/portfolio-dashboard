-- instruments.ticker の長さ制限を拡張
-- 理由:eMAXIS Slim シリーズなど、明示的な命名で20文字を超える銘柄に対応するため
ALTER TABLE instruments ALTER COLUMN ticker TYPE VARCHAR(50);