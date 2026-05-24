-- ============================================================
-- 個人資産運用ダッシュボード スキーマ定義
-- Target: Neon (PostgreSQL 17)
-- ============================================================

-- ------------------------------------------------------------
-- マスタテーブル
-- ------------------------------------------------------------

-- 口座マスタ
CREATE TABLE accounts (
    account_id      SERIAL PRIMARY KEY,
    account_name    VARCHAR(50)  NOT NULL,
    account_type    VARCHAR(20)  NOT NULL,
    broker          VARCHAR(30)  NOT NULL,
    currency        CHAR(3)      NOT NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  accounts                IS '口座マスタ(moomoo、SBI証券など)';
COMMENT ON COLUMN accounts.account_type   IS 'general / nisa_tsumitate など';
COMMENT ON COLUMN accounts.currency       IS '主要取扱通貨(USD / JPY)';

-- 銘柄マスタ
CREATE TABLE instruments (
    instrument_id    SERIAL PRIMARY KEY,
    ticker           VARCHAR(20)  NOT NULL UNIQUE,
    isin_or_code     VARCHAR(20),
    name             VARCHAR(100) NOT NULL,
    instrument_type  VARCHAR(20)  NOT NULL,
    currency         CHAR(3)      NOT NULL,
    price_source     VARCHAR(20)  NOT NULL,
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  instruments                  IS '銘柄マスタ(個別株・投資信託)';
COMMENT ON COLUMN instruments.instrument_type  IS 'stock / mutual_fund';
COMMENT ON COLUMN instruments.price_source     IS 'yfinance / toushin など';

-- ------------------------------------------------------------
-- トランザクションテーブル
-- ------------------------------------------------------------

-- 取引履歴
CREATE TABLE transactions (
    transaction_id   SERIAL PRIMARY KEY,
    account_id       INTEGER       NOT NULL REFERENCES accounts(account_id),
    instrument_id    INTEGER       NOT NULL REFERENCES instruments(instrument_id),
    trade_date       DATE          NOT NULL,
    trade_type       VARCHAR(10)   NOT NULL,
    quantity         NUMERIC(18,6) NOT NULL,
    unit_price       NUMERIC(18,4) NOT NULL,
    amount           NUMERIC(18,2) NOT NULL,
    fee              NUMERIC(18,2) NOT NULL DEFAULT 0,
    currency         CHAR(3)       NOT NULL,
    fx_rate          NUMERIC(10,4),
    created_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_account_instrument ON transactions(account_id, instrument_id);
CREATE INDEX idx_transactions_trade_date         ON transactions(trade_date);

COMMENT ON TABLE  transactions             IS '取引履歴';
COMMENT ON COLUMN transactions.trade_type  IS 'buy / sell';
COMMENT ON COLUMN transactions.quantity    IS '数量(投信は小数点)';
COMMENT ON COLUMN transactions.fx_rate     IS '約定時の円換算レート(外貨時のみ)';

-- 配当履歴
CREATE TABLE dividends (
    dividend_id      SERIAL PRIMARY KEY,
    account_id       INTEGER       NOT NULL REFERENCES accounts(account_id),
    instrument_id    INTEGER       NOT NULL REFERENCES instruments(instrument_id),
    payment_date     DATE          NOT NULL,
    amount           NUMERIC(18,2) NOT NULL,
    currency         CHAR(3)       NOT NULL,
    fx_rate          NUMERIC(10,4),
    tax_withheld     NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dividends_account_instrument ON dividends(account_id, instrument_id);
CREATE INDEX idx_dividends_payment_date       ON dividends(payment_date);

COMMENT ON TABLE  dividends               IS '配当履歴';
COMMENT ON COLUMN dividends.tax_withheld  IS '源泉徴収税(米国株は10%)';

-- ------------------------------------------------------------
-- 時系列テーブル
-- ------------------------------------------------------------

-- 日次価格
CREATE TABLE prices_daily (
    instrument_id    INTEGER       NOT NULL REFERENCES instruments(instrument_id),
    price_date       DATE          NOT NULL,
    close_price      NUMERIC(18,4) NOT NULL,
    currency         CHAR(3)       NOT NULL,
    fetched_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (instrument_id, price_date)
);

COMMENT ON TABLE  prices_daily              IS '日次の終値・基準価額';

-- 為替レート
CREATE TABLE fx_rates_daily (
    currency_pair    VARCHAR(7)    NOT NULL,
    rate_date        DATE          NOT NULL,
    rate             NUMERIC(10,4) NOT NULL,
    fetched_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (currency_pair, rate_date)
);

COMMENT ON TABLE  fx_rates_daily              IS '日次為替レート';
COMMENT ON COLUMN fx_rates_daily.currency_pair IS 'USD/JPY など';

-- ------------------------------------------------------------
-- 判断ジャーナル
-- ------------------------------------------------------------

CREATE TABLE decisions (
    decision_id              SERIAL PRIMARY KEY,
    transaction_id           INTEGER REFERENCES transactions(transaction_id),
    decision_date            DATE          NOT NULL,
    reason                   TEXT          NOT NULL,
    confidence               VARCHAR(10)   NOT NULL,
    expected_holding_period  VARCHAR(20),
    expected_return_pct      NUMERIC(5,2),
    review_date              DATE,
    review_note              TEXT,
    created_at               TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_decisions_transaction_id ON decisions(transaction_id);
CREATE INDEX idx_decisions_decision_date  ON decisions(decision_date);

COMMENT ON TABLE  decisions             IS '判断ジャーナル';
COMMENT ON COLUMN decisions.confidence  IS 'high / mid / low';

-- ------------------------------------------------------------
-- 初期マスタデータ
-- ------------------------------------------------------------

INSERT INTO accounts (account_name, account_type, broker, currency) VALUES
    ('moomoo',    'general',         'moomoo証券', 'USD'),
    ('SBI_NISA',  'nisa_tsumitate',  'SBI証券',    'JPY');