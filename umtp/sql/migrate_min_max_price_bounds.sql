USE UMTP_RB;

SELECT COUNT(*) INTO @has_user_fair_prices_table
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices';

SELECT COUNT(*) INTO @has_min_price_krw
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices'
  AND column_name = 'min_price_krw';

SET @sql_min_price_krw = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''user_fair_prices table not found''',
  IF(
    @has_min_price_krw = 0,
    'ALTER TABLE user_fair_prices ADD COLUMN min_price_krw INT NULL AFTER target_buy_price_krw',
    'SELECT ''min_price_krw already exists'''
  )
);

PREPARE stmt_min_price_krw FROM @sql_min_price_krw;
EXECUTE stmt_min_price_krw;
DEALLOCATE PREPARE stmt_min_price_krw;

SELECT COUNT(*) INTO @has_max_price_krw
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_fair_prices'
  AND column_name = 'max_price_krw';

SET @sql_max_price_krw = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''user_fair_prices table not found''',
  IF(
    @has_max_price_krw = 0,
    'ALTER TABLE user_fair_prices ADD COLUMN max_price_krw INT NULL AFTER min_price_krw',
    'SELECT ''max_price_krw already exists'''
  )
);

PREPARE stmt_max_price_krw FROM @sql_max_price_krw;
EXECUTE stmt_max_price_krw;
DEALLOCATE PREPARE stmt_max_price_krw;

-- 검증용: 필요 시 수동 확인
-- SHOW CREATE TABLE user_fair_prices;
