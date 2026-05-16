USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_alert_events_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'alert_events';

SET @sql_no_alert_events = IF(
  @has_alert_events_table = 0,
  'SELECT ''alert_events table not found''',
  'SELECT ''alert_events table exists'''
);
PREPARE stmt_no_alert_events FROM @sql_no_alert_events;
EXECUTE stmt_no_alert_events;
DEALLOCATE PREPARE stmt_no_alert_events;

SELECT COUNT(*) INTO @has_source
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'source';
SET @sql_source = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip source''',
  IF(
    @has_source = 0,
    'ALTER TABLE alert_events ADD COLUMN source VARCHAR(50) NULL AFTER product_id',
    'SELECT ''source exists'''
  )
);
PREPARE stmt_source FROM @sql_source;
EXECUTE stmt_source;
DEALLOCATE PREPARE stmt_source;

SELECT COUNT(*) INTO @has_product_type
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'product_type';
SET @sql_product_type = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip product_type''',
  IF(
    @has_product_type = 0,
    'ALTER TABLE alert_events ADD COLUMN product_type VARCHAR(100) NULL AFTER title',
    'SELECT ''product_type exists'''
  )
);
PREPARE stmt_product_type FROM @sql_product_type;
EXECUTE stmt_product_type;
DEALLOCATE PREPARE stmt_product_type;

SELECT COUNT(*) INTO @has_chip
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'chip';
SET @sql_chip = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip chip''',
  IF(
    @has_chip = 0,
    'ALTER TABLE alert_events ADD COLUMN chip VARCHAR(50) NULL AFTER product_type',
    'SELECT ''chip exists'''
  )
);
PREPARE stmt_chip FROM @sql_chip;
EXECUTE stmt_chip;
DEALLOCATE PREPARE stmt_chip;

SELECT COUNT(*) INTO @has_screen_inch
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'screen_inch';
SET @sql_screen_inch = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip screen_inch''',
  IF(
    @has_screen_inch = 0,
    'ALTER TABLE alert_events ADD COLUMN screen_inch INT NULL AFTER chip',
    'SELECT ''screen_inch exists'''
  )
);
PREPARE stmt_screen_inch FROM @sql_screen_inch;
EXECUTE stmt_screen_inch;
DEALLOCATE PREPARE stmt_screen_inch;

SELECT COUNT(*) INTO @has_ram_gb
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'ram_gb';
SET @sql_ram_gb = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip ram_gb''',
  IF(
    @has_ram_gb = 0,
    'ALTER TABLE alert_events ADD COLUMN ram_gb INT NULL AFTER screen_inch',
    'SELECT ''ram_gb exists'''
  )
);
PREPARE stmt_ram_gb FROM @sql_ram_gb;
EXECUTE stmt_ram_gb;
DEALLOCATE PREPARE stmt_ram_gb;

SELECT COUNT(*) INTO @has_ssd_gb
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'ssd_gb';
SET @sql_ssd_gb = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip ssd_gb''',
  IF(
    @has_ssd_gb = 0,
    'ALTER TABLE alert_events ADD COLUMN ssd_gb INT NULL AFTER ram_gb',
    'SELECT ''ssd_gb exists'''
  )
);
PREPARE stmt_ssd_gb FROM @sql_ssd_gb;
EXECUTE stmt_ssd_gb;
DEALLOCATE PREPARE stmt_ssd_gb;

SELECT COUNT(*) INTO @has_alert_drop_rate_percent
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'alert_drop_rate_percent';
SET @sql_alert_drop_rate_percent = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_drop_rate_percent''',
  IF(
    @has_alert_drop_rate_percent = 0,
    'ALTER TABLE alert_events ADD COLUMN alert_drop_rate_percent DECIMAL(6,2) NULL AFTER drop_rate_percent',
    'SELECT ''alert_drop_rate_percent exists'''
  )
);
PREPARE stmt_alert_drop_rate_percent FROM @sql_alert_drop_rate_percent;
EXECUTE stmt_alert_drop_rate_percent;
DEALLOCATE PREPARE stmt_alert_drop_rate_percent;

SELECT COUNT(*) INTO @has_alert_price_direction
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'alert_price_direction';
SET @sql_alert_price_direction = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_price_direction''',
  IF(
    @has_alert_price_direction = 0,
    'ALTER TABLE alert_events ADD COLUMN alert_price_direction VARCHAR(32) NULL AFTER alert_drop_rate_percent',
    'SELECT ''alert_price_direction exists'''
  )
);
PREPARE stmt_alert_price_direction FROM @sql_alert_price_direction;
EXECUTE stmt_alert_price_direction;
DEALLOCATE PREPARE stmt_alert_price_direction;

SELECT COUNT(*) INTO @has_risk_level
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'risk_level';
SET @sql_risk_level = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip risk_level''',
  IF(
    @has_risk_level = 0,
    'ALTER TABLE alert_events ADD COLUMN risk_level VARCHAR(20) NULL AFTER alert_price_direction',
    'SELECT ''risk_level exists'''
  )
);
PREPARE stmt_risk_level FROM @sql_risk_level;
EXECUTE stmt_risk_level;
DEALLOCATE PREPARE stmt_risk_level;

SELECT COUNT(*) INTO @has_risk_score
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'risk_score';
SET @sql_risk_score = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip risk_score''',
  IF(
    @has_risk_score = 0,
    'ALTER TABLE alert_events ADD COLUMN risk_score INT NULL AFTER risk_level',
    'SELECT ''risk_score exists'''
  )
);
PREPARE stmt_risk_score FROM @sql_risk_score;
EXECUTE stmt_risk_score;
DEALLOCATE PREPARE stmt_risk_score;

SELECT COUNT(*) INTO @has_risk_keywords
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'risk_keywords';
SET @sql_risk_keywords = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip risk_keywords''',
  IF(
    @has_risk_keywords = 0,
    'ALTER TABLE alert_events ADD COLUMN risk_keywords TEXT NULL AFTER risk_score',
    'SELECT ''risk_keywords exists'''
  )
);
PREPARE stmt_risk_keywords FROM @sql_risk_keywords;
EXECUTE stmt_risk_keywords;
DEALLOCATE PREPARE stmt_risk_keywords;

SELECT COUNT(*) INTO @has_is_exchange_post
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'is_exchange_post';
SET @sql_is_exchange_post = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip is_exchange_post''',
  IF(
    @has_is_exchange_post = 0,
    'ALTER TABLE alert_events ADD COLUMN is_exchange_post BOOLEAN NULL AFTER risk_keywords',
    'SELECT ''is_exchange_post exists'''
  )
);
PREPARE stmt_is_exchange_post FROM @sql_is_exchange_post;
EXECUTE stmt_is_exchange_post;
DEALLOCATE PREPARE stmt_is_exchange_post;

SELECT COUNT(*) INTO @has_trade_type
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'trade_type';
SET @sql_trade_type = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip trade_type''',
  IF(
    @has_trade_type = 0,
    'ALTER TABLE alert_events ADD COLUMN trade_type VARCHAR(20) NULL AFTER is_exchange_post',
    'SELECT ''trade_type exists'''
  )
);
PREPARE stmt_trade_type FROM @sql_trade_type;
EXECUTE stmt_trade_type;
DEALLOCATE PREPARE stmt_trade_type;

SELECT COUNT(*) INTO @has_body_excerpt
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'body_excerpt';
SET @sql_body_excerpt = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip body_excerpt''',
  IF(
    @has_body_excerpt = 0,
    'ALTER TABLE alert_events ADD COLUMN body_excerpt TEXT NULL AFTER trade_type',
    'SELECT ''body_excerpt exists'''
  )
);
PREPARE stmt_body_excerpt FROM @sql_body_excerpt;
EXECUTE stmt_body_excerpt;
DEALLOCATE PREPARE stmt_body_excerpt;

SELECT COUNT(*) INTO @has_analyzed_at
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'analyzed_at';
SET @sql_analyzed_at = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip analyzed_at''',
  IF(
    @has_analyzed_at = 0,
    'ALTER TABLE alert_events ADD COLUMN analyzed_at TIMESTAMP NULL AFTER body_excerpt',
    'SELECT ''analyzed_at exists'''
  )
);
PREPARE stmt_analyzed_at FROM @sql_analyzed_at;
EXECUTE stmt_analyzed_at;
DEALLOCATE PREPARE stmt_analyzed_at;

UPDATE alert_events
SET analyzed_at = created_at
WHERE analyzed_at IS NULL;

UPDATE alert_events
SET alert_price_direction = 'BELOW_OR_EQUAL'
WHERE alert_price_direction IS NULL
   OR TRIM(alert_price_direction) = '';

-- 검증용: 필요 시 수동 확인
-- SHOW CREATE TABLE alert_events;
