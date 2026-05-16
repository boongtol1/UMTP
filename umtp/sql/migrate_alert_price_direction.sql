USE UMTP_RB;

SELECT COUNT(*) INTO @has_user_fair_prices_table
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices';

SELECT COUNT(*) INTO @has_alert_price_direction
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices'
  AND column_name = 'alert_price_direction';

SET @sql_alert_price_direction = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''user_fair_prices table not found''',
  IF(
    @has_alert_price_direction = 0,
    'ALTER TABLE user_fair_prices ADD COLUMN alert_price_direction VARCHAR(32) NOT NULL DEFAULT ''BELOW_OR_EQUAL'' AFTER alert_drop_rate_percent',
    'SELECT ''alert_price_direction already exists'''
  )
);

PREPARE stmt_alert_price_direction FROM @sql_alert_price_direction;
EXECUTE stmt_alert_price_direction;
DEALLOCATE PREPARE stmt_alert_price_direction;

UPDATE user_fair_prices
SET alert_price_direction = 'BELOW_OR_EQUAL'
WHERE alert_price_direction IS NULL
   OR TRIM(alert_price_direction) = ''
   OR UPPER(TRIM(alert_price_direction)) NOT IN ('BELOW_OR_EQUAL', 'ABOVE_OR_EQUAL');

-- 검증용: 필요 시 수동 확인
-- SHOW CREATE TABLE user_fair_prices;
