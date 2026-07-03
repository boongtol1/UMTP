USE UMTP_RB;

CREATE TABLE IF NOT EXISTS resale_trade_journeys (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NULL,
  source VARCHAR(50) NOT NULL DEFAULT 'joongna',
  product_id VARCHAR(100) NULL,
  url TEXT NULL,

  -- 매물/자동 분석
  title VARCHAR(500) NULL,
  listing_price_krw INT NULL,
  seller_nickname VARCHAR(100) NULL,
  seller_location VARCHAR(255) NULL,
  image_urls LONGTEXT NULL,
  body_text LONGTEXT NULL,
  product_type VARCHAR(100) NULL,
  chip VARCHAR(50) NULL,
  screen_inch INT NULL,
  ram_gb INT NULL,
  ssd_gb INT NULL,
  fair_price_krw INT NULL,
  discount_rate_percent DECIMAL(7,2) NULL,

  -- 구매 진행
  contacted_at DATETIME NULL,
  seller_response_at DATETIME NULL,
  purchased_at DATETIME NULL,
  purchase_price_krw INT NULL,
  purchase_method VARCHAR(20) NULL,
  purchase_location VARCHAR(255) NULL,
  transport_cost_krw INT NULL,
  shipping_cost_krw INT NULL,
  total_cost_krw INT GENERATED ALWAYS AS (
    CASE
      WHEN purchase_price_krw IS NULL
       AND transport_cost_krw IS NULL
       AND shipping_cost_krw IS NULL THEN NULL
      ELSE COALESCE(purchase_price_krw, 0)
         + COALESCE(transport_cost_krw, 0)
         + COALESCE(shipping_cost_krw, 0)
    END
  ) STORED,
  payment_method VARCHAR(50) NULL,

  -- 수동 확인/검수
  serial_number VARCHAR(100) NULL,
  model_number VARCHAR(100) NULL,
  battery_cycle_count INT NULL,
  battery_health_percent INT NULL,
  activation_lock_off BOOLEAN NULL,
  mdm_lock_none BOOLEAN NULL,
  inspection_notes LONGTEXT NULL,

  -- 재판매/판매
  resale_listing_price_krw INT NULL,
  resale_platform VARCHAR(50) NULL,
  resale_url TEXT NULL,
  sold_at DATETIME NULL,
  sale_price_krw INT NULL,
  buyer_nickname VARCHAR(100) NULL,
  sale_method VARCHAR(20) NULL,
  sale_location VARCHAR(255) NULL,
  sale_platform VARCHAR(50) NULL,

  current_stage VARCHAR(40) NOT NULL DEFAULT 'DISCOVERED',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  KEY idx_resale_trade_journeys_user (user_id),
  KEY idx_resale_journey_stage (current_stage),
  KEY idx_resale_journey_source_product (source, product_id),
  KEY idx_resale_trade_journeys_purchased_at (purchased_at),
  KEY idx_resale_trade_journeys_sold_at (sold_at),
  UNIQUE KEY uniq_resale_journey_user_source_product (user_id, source, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();
SET SESSION group_concat_max_len = 65535;

-- 다른 시스템에 남아 있을 수 있는 생성/계산 컬럼은 의존 컬럼보다 먼저 제거한다.
SELECT GROUP_CONCAT(
  CONCAT('DROP COLUMN `', column_name, '`')
  ORDER BY FIELD(
    column_name,
    'response_time_minutes',
    'gross_profit_krw',
    'net_profit_krw',
    'roi_percent',
    'purchase_speed_minutes',
    'sale_duration_hours',
    'total_holding_time_hours',
    'profit_per_day_krw'
  )
  SEPARATOR ', '
)
INTO @generated_drop_clauses
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name IN (
    'response_time_minutes',
    'gross_profit_krw',
    'net_profit_krw',
    'roi_percent',
    'purchase_speed_minutes',
    'sale_duration_hours',
    'total_holding_time_hours',
    'profit_per_day_krw'
  );
SET @sql_drop_generated_columns = IF(
  @generated_drop_clauses IS NULL OR @generated_drop_clauses = '',
  'SELECT ''no generated resale_trade_journeys columns to drop''',
  CONCAT('ALTER TABLE resale_trade_journeys ', @generated_drop_clauses)
);
PREPARE stmt_drop_generated_columns FROM @sql_drop_generated_columns;
EXECUTE stmt_drop_generated_columns;
DEALLOCATE PREPARE stmt_drop_generated_columns;

-- 현재 거래 기록 스키마에서 제거된 컬럼은 새/기존 시스템 모두에서 복구하지 않는다.
SELECT GROUP_CONCAT(CONCAT('DROP COLUMN `', column_name, '`') ORDER BY column_name SEPARATOR ', ')
INTO @obsolete_drop_clauses
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name IN (
    'url_digest',
    'listing_created_at',
    'discovered_at',
    'seller_shop_id',
    'purchase_contact_record',
    'purchase_conversation_text',
    'money_sent_at',
    'money_received_at',
    'purchase_account_number',
    'cpu_core_count',
    'gpu_core_count',
    'applecare_status',
    'minimum_accept_price_krw',
    'resale_listing_created_at',
    'resale_product_id',
    'initial_resale_price_krw',
    'resale_contact_record',
    'resale_conversation_text',
    'resale_account_number',
    'final_shipping_cost_krw',
    'platform_fee_krw',
    'refund_or_claim',
    'expected_profit_krw',
    'risk_score',
    'reason_tags',
    'final_result_notes',
    'contact_record',
    'conversation_text',
    'account_number',
    'seller_answer_text',
    'negotiable',
    'seller_tone',
    'suspicious_points',
    'confirmed_price_krw',
    'decision_at',
    'decision_result',
    'decision_reason',
    'target_purchase_price_krw',
    'expected_sale_price_krw',
    'expected_net_profit_krw',
    'expected_sale_duration_days',
    'battery_condition',
    'truetone_ok',
    'display_condition',
    'keyboard_condition',
    'trackpad_condition',
    'speaker_condition',
    'camera_condition',
    'wifi_bluetooth_ok',
    'exterior_grade',
    'included_items',
    'repair_suspected',
    'cleaned_at',
    'photo_taken_at',
    'resale_title',
    'resale_body_text',
    'resale_photo_count',
    'resale_strategy_notes',
    'upload_time_slot',
    'view_count',
    'favorite_count',
    'inquiry_count',
    'first_inquiry_at',
    'first_inquiry_delay_minutes',
    'negotiation_count',
    'price_drop_count',
    'price_drop_history',
    'buyer_questions',
    'common_objections',
    'color',
    'keyboard_layout'
  );
SET @sql_drop_obsolete_columns = IF(
  @obsolete_drop_clauses IS NULL OR @obsolete_drop_clauses = '',
  'SELECT ''no obsolete resale_trade_journeys columns to drop''',
  CONCAT('ALTER TABLE resale_trade_journeys ', @obsolete_drop_clauses)
);
PREPARE stmt_drop_obsolete_columns FROM @sql_drop_obsolete_columns;
EXECUTE stmt_drop_obsolete_columns;
DEALLOCATE PREPARE stmt_drop_obsolete_columns;

-- 오래된 DB에 핵심 컬럼이 빠져 있으면 현재 스키마의 최소 필드만 보강한다.
SELECT GROUP_CONCAT(add_clause ORDER BY ord SEPARATOR ', ')
INTO @active_add_clauses
FROM (
  SELECT 1 AS ord, 'ADD COLUMN user_id VARCHAR(100) NULL AFTER id' AS add_clause
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'user_id'
  )
  UNION ALL
  SELECT 2, 'ADD COLUMN source VARCHAR(50) NOT NULL DEFAULT ''joongna'' AFTER user_id'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'source'
  )
  UNION ALL
  SELECT 3, 'ADD COLUMN product_id VARCHAR(100) NULL AFTER source'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'product_id'
  )
  UNION ALL
  SELECT 4, 'ADD COLUMN url TEXT NULL AFTER product_id'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'url'
  )
  UNION ALL
  SELECT 5, 'ADD COLUMN title VARCHAR(500) NULL AFTER url'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'title'
  )
  UNION ALL
  SELECT 6, 'ADD COLUMN listing_price_krw INT NULL AFTER title'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'listing_price_krw'
  )
  UNION ALL
  SELECT 7, 'ADD COLUMN seller_nickname VARCHAR(100) NULL AFTER listing_price_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'seller_nickname'
  )
  UNION ALL
  SELECT 8, 'ADD COLUMN seller_location VARCHAR(255) NULL AFTER seller_nickname'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'seller_location'
  )
  UNION ALL
  SELECT 9, 'ADD COLUMN image_urls LONGTEXT NULL AFTER seller_location'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'image_urls'
  )
  UNION ALL
  SELECT 10, 'ADD COLUMN body_text LONGTEXT NULL AFTER image_urls'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'body_text'
  )
  UNION ALL
  SELECT 11, 'ADD COLUMN product_type VARCHAR(100) NULL AFTER body_text'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'product_type'
  )
  UNION ALL
  SELECT 12, 'ADD COLUMN chip VARCHAR(50) NULL AFTER product_type'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'chip'
  )
  UNION ALL
  SELECT 13, 'ADD COLUMN screen_inch INT NULL AFTER chip'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'screen_inch'
  )
  UNION ALL
  SELECT 14, 'ADD COLUMN ram_gb INT NULL AFTER screen_inch'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'ram_gb'
  )
  UNION ALL
  SELECT 15, 'ADD COLUMN ssd_gb INT NULL AFTER ram_gb'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'ssd_gb'
  )
  UNION ALL
  SELECT 16, 'ADD COLUMN fair_price_krw INT NULL AFTER ssd_gb'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'fair_price_krw'
  )
  UNION ALL
  SELECT 17, 'ADD COLUMN discount_rate_percent DECIMAL(7,2) NULL AFTER fair_price_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'discount_rate_percent'
  )
  UNION ALL
  SELECT 20, 'ADD COLUMN contacted_at DATETIME NULL AFTER discount_rate_percent'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'contacted_at'
  )
  UNION ALL
  SELECT 21, 'ADD COLUMN seller_response_at DATETIME NULL AFTER contacted_at'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'seller_response_at'
  )
  UNION ALL
  SELECT 22, 'ADD COLUMN purchased_at DATETIME NULL AFTER seller_response_at'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'purchased_at'
  )
  UNION ALL
  SELECT 23, 'ADD COLUMN purchase_price_krw INT NULL AFTER purchased_at'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'purchase_price_krw'
  )
  UNION ALL
  SELECT 24, 'ADD COLUMN purchase_method VARCHAR(20) NULL AFTER purchase_price_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'purchase_method'
  )
  UNION ALL
  SELECT 25, 'ADD COLUMN purchase_location VARCHAR(255) NULL AFTER purchase_method'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'purchase_location'
  )
  UNION ALL
  SELECT 26, 'ADD COLUMN transport_cost_krw INT NULL AFTER purchase_location'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'transport_cost_krw'
  )
  UNION ALL
  SELECT 27, 'ADD COLUMN shipping_cost_krw INT NULL AFTER transport_cost_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'shipping_cost_krw'
  )
  UNION ALL
  SELECT 28, 'ADD COLUMN payment_method VARCHAR(50) NULL AFTER shipping_cost_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'payment_method'
  )
  UNION ALL
  SELECT 29, 'ADD COLUMN serial_number VARCHAR(100) NULL AFTER payment_method'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'serial_number'
  )
  UNION ALL
  SELECT 30, 'ADD COLUMN model_number VARCHAR(100) NULL AFTER serial_number'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'model_number'
  )
  UNION ALL
  SELECT 31, 'ADD COLUMN battery_cycle_count INT NULL AFTER model_number'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'battery_cycle_count'
  )
  UNION ALL
  SELECT 32, 'ADD COLUMN battery_health_percent INT NULL AFTER battery_cycle_count'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'battery_health_percent'
  )
  UNION ALL
  SELECT 33, 'ADD COLUMN activation_lock_off BOOLEAN NULL AFTER battery_health_percent'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'activation_lock_off'
  )
  UNION ALL
  SELECT 34, 'ADD COLUMN mdm_lock_none BOOLEAN NULL AFTER activation_lock_off'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'mdm_lock_none'
  )
  UNION ALL
  SELECT 35, 'ADD COLUMN inspection_notes LONGTEXT NULL AFTER mdm_lock_none'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'inspection_notes'
  )
  UNION ALL
  SELECT 36, 'ADD COLUMN resale_listing_price_krw INT NULL AFTER inspection_notes'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'resale_listing_price_krw'
  )
  UNION ALL
  SELECT 37, 'ADD COLUMN resale_platform VARCHAR(50) NULL AFTER resale_listing_price_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'resale_platform'
  )
  UNION ALL
  SELECT 38, 'ADD COLUMN resale_url TEXT NULL AFTER resale_platform'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'resale_url'
  )
  UNION ALL
  SELECT 39, 'ADD COLUMN sold_at DATETIME NULL AFTER resale_url'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'sold_at'
  )
  UNION ALL
  SELECT 40, 'ADD COLUMN sale_price_krw INT NULL AFTER sold_at'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'sale_price_krw'
  )
  UNION ALL
  SELECT 41, 'ADD COLUMN buyer_nickname VARCHAR(100) NULL AFTER sale_price_krw'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'buyer_nickname'
  )
  UNION ALL
  SELECT 42, 'ADD COLUMN sale_method VARCHAR(20) NULL AFTER buyer_nickname'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'sale_method'
  )
  UNION ALL
  SELECT 43, 'ADD COLUMN sale_location VARCHAR(255) NULL AFTER sale_method'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'sale_location'
  )
  UNION ALL
  SELECT 44, 'ADD COLUMN sale_platform VARCHAR(50) NULL AFTER sale_location'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'sale_platform'
  )
  UNION ALL
  SELECT 45, 'ADD COLUMN current_stage VARCHAR(40) NOT NULL DEFAULT ''DISCOVERED'' AFTER sale_platform'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'current_stage'
  )
  UNION ALL
  SELECT 46, 'ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER current_stage'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'created_at'
  )
  UNION ALL
  SELECT 47, 'ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'updated_at'
  )
) active_columns;

SET @sql_add_active_columns = IF(
  @active_add_clauses IS NULL OR LENGTH(@active_add_clauses) = 0,
  'SELECT ''active resale_trade_journeys columns exist''',
  CONCAT('ALTER TABLE resale_trade_journeys ', @active_add_clauses)
);
PREPARE stmt_add_active_columns FROM @sql_add_active_columns;
EXECUTE stmt_add_active_columns;
DEALLOCATE PREPARE stmt_add_active_columns;

SELECT COUNT(*) INTO @has_total_cost_krw
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'total_cost_krw';
SET @sql_add_total_cost = IF(
  @has_total_cost_krw = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN total_cost_krw INT GENERATED ALWAYS AS (
     CASE
       WHEN purchase_price_krw IS NULL
        AND transport_cost_krw IS NULL
        AND shipping_cost_krw IS NULL THEN NULL
       ELSE COALESCE(purchase_price_krw, 0)
          + COALESCE(transport_cost_krw, 0)
          + COALESCE(shipping_cost_krw, 0)
     END
   ) STORED AFTER shipping_cost_krw',
  'SELECT ''resale_trade_journeys.total_cost_krw exists'''
);
PREPARE stmt_add_total_cost FROM @sql_add_total_cost;
EXECUTE stmt_add_total_cost;
DEALLOCATE PREPARE stmt_add_total_cost;

SELECT COUNT(*) INTO @has_legacy_uq_source_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'uq_resale_trade_journeys_source_product';
SET @sql_drop_legacy_uq_source_product = IF(
  @has_legacy_uq_source_product = 0,
  'SELECT ''uq_resale_trade_journeys_source_product already absent''',
  'ALTER TABLE resale_trade_journeys DROP INDEX uq_resale_trade_journeys_source_product'
);
PREPARE stmt_drop_legacy_uq_source_product FROM @sql_drop_legacy_uq_source_product;
EXECUTE stmt_drop_legacy_uq_source_product;
DEALLOCATE PREPARE stmt_drop_legacy_uq_source_product;

SELECT COUNT(*) INTO @has_legacy_uq_source_url
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'uq_resale_trade_journeys_source_url';
SET @sql_drop_legacy_uq_source_url = IF(
  @has_legacy_uq_source_url = 0,
  'SELECT ''uq_resale_trade_journeys_source_url already absent''',
  'ALTER TABLE resale_trade_journeys DROP INDEX uq_resale_trade_journeys_source_url'
);
PREPARE stmt_drop_legacy_uq_source_url FROM @sql_drop_legacy_uq_source_url;
EXECUTE stmt_drop_legacy_uq_source_url;
DEALLOCATE PREPARE stmt_drop_legacy_uq_source_url;

SELECT COUNT(*) INTO @has_uniq_user_source_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'uniq_resale_journey_user_source_product';

SELECT GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')
INTO @uniq_user_source_product_cols
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'uniq_resale_journey_user_source_product';

SET @sql_drop_uniq_user_source_product_mismatch = IF(
  @has_uniq_user_source_product > 0
  AND IFNULL(@uniq_user_source_product_cols, '') <> 'user_id,source,product_id',
  'ALTER TABLE resale_trade_journeys DROP INDEX uniq_resale_journey_user_source_product',
  'SELECT ''uniq_resale_journey_user_source_product definition ok'''
);
PREPARE stmt_drop_uniq_user_source_product_mismatch FROM @sql_drop_uniq_user_source_product_mismatch;
EXECUTE stmt_drop_uniq_user_source_product_mismatch;
DEALLOCATE PREPARE stmt_drop_uniq_user_source_product_mismatch;

SELECT COUNT(*) INTO @has_uniq_user_source_product_after_drop
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'uniq_resale_journey_user_source_product';
SET @sql_add_uniq_user_source_product = IF(
  @has_uniq_user_source_product_after_drop = 0,
  'ALTER TABLE resale_trade_journeys ADD UNIQUE KEY uniq_resale_journey_user_source_product (user_id, source, product_id)',
  'SELECT ''uniq_resale_journey_user_source_product exists'''
);
PREPARE stmt_add_uniq_user_source_product FROM @sql_add_uniq_user_source_product;
EXECUTE stmt_add_uniq_user_source_product;
DEALLOCATE PREPARE stmt_add_uniq_user_source_product;

SELECT COUNT(*) INTO @has_idx_source_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'idx_resale_journey_source_product';
SET @sql_add_idx_source_product = IF(
  @has_idx_source_product = 0,
  'ALTER TABLE resale_trade_journeys ADD INDEX idx_resale_journey_source_product (source, product_id)',
  'SELECT ''idx_resale_journey_source_product exists'''
);
PREPARE stmt_add_idx_source_product FROM @sql_add_idx_source_product;
EXECUTE stmt_add_idx_source_product;
DEALLOCATE PREPARE stmt_add_idx_source_product;

SELECT COUNT(*) INTO @has_idx_stage
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'idx_resale_journey_stage';
SET @sql_add_idx_stage = IF(
  @has_idx_stage = 0,
  'ALTER TABLE resale_trade_journeys ADD INDEX idx_resale_journey_stage (current_stage)',
  'SELECT ''idx_resale_journey_stage exists'''
);
PREPARE stmt_add_idx_stage FROM @sql_add_idx_stage;
EXECUTE stmt_add_idx_stage;
DEALLOCATE PREPARE stmt_add_idx_stage;

SELECT COUNT(*) INTO @has_idx_purchased_at
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'idx_resale_trade_journeys_purchased_at';
SET @sql_add_idx_purchased_at = IF(
  @has_idx_purchased_at = 0,
  'ALTER TABLE resale_trade_journeys ADD INDEX idx_resale_trade_journeys_purchased_at (purchased_at)',
  'SELECT ''idx_resale_trade_journeys_purchased_at exists'''
);
PREPARE stmt_add_idx_purchased_at FROM @sql_add_idx_purchased_at;
EXECUTE stmt_add_idx_purchased_at;
DEALLOCATE PREPARE stmt_add_idx_purchased_at;

SELECT COUNT(*) INTO @has_idx_sold_at
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND index_name = 'idx_resale_trade_journeys_sold_at';
SET @sql_add_idx_sold_at = IF(
  @has_idx_sold_at = 0,
  'ALTER TABLE resale_trade_journeys ADD INDEX idx_resale_trade_journeys_sold_at (sold_at)',
  'SELECT ''idx_resale_trade_journeys_sold_at exists'''
);
PREPARE stmt_add_idx_sold_at FROM @sql_add_idx_sold_at;
EXECUTE stmt_add_idx_sold_at;
DEALLOCATE PREPARE stmt_add_idx_sold_at;
