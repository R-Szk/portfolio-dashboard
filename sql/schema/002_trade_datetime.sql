-- transactionsテーブルに約定日時カラムを追加(タイムゾーン付き)
ALTER TABLE transactions ADD COLUMN trade_datetime TIMESTAMPTZ;

-- 既存データがあれば trade_date から trade_datetime に値を移す
-- (今は空テーブルなので不要だが、将来のために書いておく形でもOK)
UPDATE transactions SET trade_datetime = trade_date::TIMESTAMPTZ WHERE trade_datetime IS NULL;

-- trade_datetime を NOT NULL に
ALTER TABLE transactions ALTER COLUMN trade_datetime SET NOT NULL;

-- 古い trade_date は削除(まだデータがないので安全)
ALTER TABLE transactions DROP COLUMN trade_date;

-- 自然キーのUNIQUE制約を追加
ALTER TABLE transactions
ADD CONSTRAINT uq_transactions_natural_key
UNIQUE (account_id, instrument_id, trade_datetime, trade_type, quantity, unit_price);