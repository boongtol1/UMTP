USE UMTP_RB;

SELECT COUNT(*) INTO @has_user_fair_prices_table
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices';

SELECT COUNT(*) INTO @has_target_buy_price_krw
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices'
  AND column_name = 'target_buy_price_krw';

SET @sql_target_buy_price_krw = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''user_fair_prices table not found''',
  IF(
    @has_target_buy_price_krw = 0,
    'ALTER TABLE user_fair_prices ADD COLUMN target_buy_price_krw INT GENERATED ALWAYS AS (ROUND(fair_price_krw * (1 - (alert_drop_rate_percent / 100)))) STORED AFTER alert_drop_rate_percent',
    'SELECT ''target_buy_price_krw already exists'''
  )
);

PREPARE stmt_target_buy_price_krw FROM @sql_target_buy_price_krw;
EXECUTE stmt_target_buy_price_krw;
DEALLOCATE PREPARE stmt_target_buy_price_krw;

-- 검증용: 필요 시 수동 확인
-- SHOW CREATE TABLE user_fair_prices;
