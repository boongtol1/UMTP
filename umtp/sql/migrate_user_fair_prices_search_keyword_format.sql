USE UMTP_RB;

SET @schema_name = DATABASE();

SET @has_user_fair_prices = (
  SELECT COUNT(*)
  FROM information_schema.tables
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
);

SET @has_product_type = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'product_type'
);

SET @has_chip = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'chip'
);

SET @has_search_keyword = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'search_keyword'
);

SET @can_backfill_search_keyword = IF(
  @has_user_fair_prices > 0
  AND @has_product_type > 0
  AND @has_chip > 0
  AND @has_search_keyword > 0,
  1,
  0
);

-- 기존 기본 키워드 패턴(붙여쓰기/영문 product_type+chip)만 정규화한다.
-- 사용자 커스텀 검색어를 덮어쓰지 않기 위해 조건을 제한한다.
SET @air_backfill_sql = IF(
  @can_backfill_search_keyword > 0,
  'UPDATE user_fair_prices
   SET search_keyword = CONCAT(LOWER(REPLACE(TRIM(chip), '' '', '''')), '' 맥북에어'')
   WHERE product_type = ''MacBook Air''
     AND chip IS NOT NULL
     AND TRIM(chip) <> ''''
     AND (
       search_keyword IS NULL
       OR TRIM(search_keyword) = ''''
       OR REPLACE(LOWER(TRIM(search_keyword)), '' '', '''') = CONCAT(LOWER(REPLACE(TRIM(chip), '' '', '''')), ''맥북에어'')
       OR LOWER(TRIM(search_keyword)) = LOWER(CONCAT(TRIM(product_type), '' '', TRIM(chip)))
     )',
  'SELECT ''skip MacBook Air search_keyword format backfill'''
);
PREPARE stmt FROM @air_backfill_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @mini_backfill_sql = IF(
  @can_backfill_search_keyword > 0,
  'UPDATE user_fair_prices
   SET search_keyword = CONCAT(LOWER(REPLACE(TRIM(chip), '' '', '''')), '' 맥미니'')
   WHERE product_type = ''Mac mini''
     AND chip IS NOT NULL
     AND TRIM(chip) <> ''''
     AND (
       search_keyword IS NULL
       OR TRIM(search_keyword) = ''''
       OR REPLACE(LOWER(TRIM(search_keyword)), '' '', '''') = CONCAT(LOWER(REPLACE(TRIM(chip), '' '', '''')), ''맥미니'')
       OR LOWER(TRIM(search_keyword)) = LOWER(CONCAT(TRIM(product_type), '' '', TRIM(chip)))
     )',
  'SELECT ''skip Mac mini search_keyword format backfill'''
);
PREPARE stmt FROM @mini_backfill_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
