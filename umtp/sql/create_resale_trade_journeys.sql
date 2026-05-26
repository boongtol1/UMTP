USE UMTP_RB;

CREATE TABLE IF NOT EXISTS resale_trade_journeys (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NULL,
  source VARCHAR(50) NOT NULL DEFAULT 'joongna',
  product_id VARCHAR(100) NULL,
  url TEXT NULL,
  url_digest CHAR(64) GENERATED ALWAYS AS (SHA2(NULLIF(TRIM(url), ''), 256)) STORED,

  -- 1. 매물 발견
  title VARCHAR(500) NULL,
  listing_created_at DATETIME NULL,
  discovered_at DATETIME NULL,
  listing_price_krw INT NULL,
  seller_nickname VARCHAR(100) NULL,
  seller_shop_id VARCHAR(100) NULL,
  seller_location VARCHAR(255) NULL,
  image_urls LONGTEXT NULL,
  body_text LONGTEXT NULL,

  -- 2. 1차 자동 분석
  product_type VARCHAR(100) NULL,
  chip VARCHAR(50) NULL,
  screen_inch INT NULL,
  ram_gb INT NULL,
  ssd_gb INT NULL,
  fair_price_krw INT NULL,
  discount_rate_percent DECIMAL(7,2) NULL,
  expected_profit_krw INT NULL,
  risk_score INT NULL,
  reason_tags LONGTEXT NULL,

  -- 3. 판매자 연락
  contacted_at DATETIME NULL,
  seller_response_at DATETIME NULL,
  purchase_contact_record VARCHAR(255) NULL,
  purchase_conversation_text LONGTEXT NULL,
  response_time_minutes INT GENERATED ALWAYS AS (
    CASE
      WHEN contacted_at IS NULL OR seller_response_at IS NULL THEN NULL
      ELSE TIMESTAMPDIFF(MINUTE, contacted_at, seller_response_at)
    END
  ) STORED,

  -- 5. 실제 구매
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
  money_sent_at DATETIME NULL,
  money_received_at DATETIME NULL,
  purchase_account_number VARCHAR(100) NULL,

  -- 정확 확인 정보 (수동 입력)
  serial_number VARCHAR(100) NULL,
  model_number VARCHAR(100) NULL,
  cpu_core_count INT NULL,
  gpu_core_count INT NULL,
  battery_cycle_count INT NULL,
  battery_health_percent INT NULL,
  applecare_status VARCHAR(100) NULL,
  activation_lock_off BOOLEAN NULL,
  mdm_lock_none BOOLEAN NULL,

  -- 6. 검수 메모
  inspection_notes LONGTEXT NULL,

  -- 7. 되팔이 준비
  resale_listing_price_krw INT NULL,
  minimum_accept_price_krw INT NULL,
  resale_platform VARCHAR(50) NULL,

  -- 8. 되팔이 글 업로드
  resale_listing_created_at DATETIME NULL,
  resale_url TEXT NULL,
  resale_product_id VARCHAR(100) NULL,
  initial_resale_price_krw INT NULL,

  -- 9. 판매 중 반응
  resale_contact_record VARCHAR(255) NULL,
  resale_conversation_text LONGTEXT NULL,
  resale_account_number VARCHAR(100) NULL,

  -- 10. 판매 완료
  sold_at DATETIME NULL,
  sale_price_krw INT NULL,
  buyer_nickname VARCHAR(100) NULL,
  sale_method VARCHAR(20) NULL,
  sale_location VARCHAR(255) NULL,
  sale_platform VARCHAR(50) NULL,
  final_shipping_cost_krw INT NULL,
  platform_fee_krw INT NULL,
  refund_or_claim VARCHAR(100) NULL,

  -- 11. 최종 정산
  gross_profit_krw INT GENERATED ALWAYS AS (
    CASE
      WHEN sale_price_krw IS NULL THEN NULL
      ELSE sale_price_krw - COALESCE(purchase_price_krw, 0)
    END
  ) STORED,
  net_profit_krw INT GENERATED ALWAYS AS (
    CASE
      WHEN sale_price_krw IS NULL THEN NULL
      ELSE sale_price_krw
           - COALESCE(purchase_price_krw, 0)
           - COALESCE(transport_cost_krw, 0)
           - COALESCE(shipping_cost_krw, 0)
           - COALESCE(final_shipping_cost_krw, 0)
           - COALESCE(platform_fee_krw, 0)
    END
  ) STORED,
  roi_percent DECIMAL(10,2) GENERATED ALWAYS AS (
    CASE
      WHEN (
        COALESCE(purchase_price_krw, 0)
        + COALESCE(transport_cost_krw, 0)
        + COALESCE(shipping_cost_krw, 0)
      ) <= 0 OR sale_price_krw IS NULL THEN NULL
      ELSE ROUND(
        (
          sale_price_krw
          - COALESCE(purchase_price_krw, 0)
          - COALESCE(transport_cost_krw, 0)
          - COALESCE(shipping_cost_krw, 0)
          - COALESCE(final_shipping_cost_krw, 0)
          - COALESCE(platform_fee_krw, 0)
        )
        / (
          COALESCE(purchase_price_krw, 0)
          + COALESCE(transport_cost_krw, 0)
          + COALESCE(shipping_cost_krw, 0)
        )
        * 100,
        2
      )
    END
  ) STORED,
  purchase_speed_minutes INT GENERATED ALWAYS AS (
    CASE
      WHEN listing_created_at IS NULL OR purchased_at IS NULL THEN NULL
      ELSE TIMESTAMPDIFF(MINUTE, listing_created_at, purchased_at)
    END
  ) STORED,
  sale_duration_hours INT GENERATED ALWAYS AS (
    CASE
      WHEN resale_listing_created_at IS NULL OR sold_at IS NULL THEN NULL
      ELSE TIMESTAMPDIFF(HOUR, resale_listing_created_at, sold_at)
    END
  ) STORED,
  total_holding_time_hours INT GENERATED ALWAYS AS (
    CASE
      WHEN purchased_at IS NULL OR sold_at IS NULL THEN NULL
      ELSE TIMESTAMPDIFF(HOUR, purchased_at, sold_at)
    END
  ) STORED,
  profit_per_day_krw INT GENERATED ALWAYS AS (
    CASE
      WHEN purchased_at IS NULL OR sold_at IS NULL OR sale_price_krw IS NULL THEN NULL
      WHEN TIMESTAMPDIFF(HOUR, purchased_at, sold_at) <= 0 THEN NULL
      ELSE ROUND(
        (
          sale_price_krw
          - COALESCE(purchase_price_krw, 0)
          - COALESCE(transport_cost_krw, 0)
          - COALESCE(shipping_cost_krw, 0)
          - COALESCE(final_shipping_cost_krw, 0)
          - COALESCE(platform_fee_krw, 0)
        )
        / (TIMESTAMPDIFF(HOUR, purchased_at, sold_at) / 24.0),
        0
      )
    END
  ) STORED,
  final_result_notes LONGTEXT NULL,

  current_stage VARCHAR(40) NOT NULL DEFAULT 'DISCOVERED',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  KEY idx_resale_trade_journeys_user (user_id),
  KEY idx_resale_journey_stage (current_stage),
  KEY idx_resale_journey_source_product (source, product_id),
  KEY idx_resale_trade_journeys_discovered_at (discovered_at),
  KEY idx_resale_trade_journeys_purchased_at (purchased_at),
  KEY idx_resale_trade_journeys_sold_at (sold_at),
  UNIQUE KEY uniq_resale_journey_user_source_product (user_id, source, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_money_sent_at
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'money_sent_at';
SET @sql_money_sent_at = IF(
  @has_money_sent_at = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN money_sent_at DATETIME NULL AFTER payment_method',
  'SELECT ''resale_trade_journeys.money_sent_at exists'''
);
PREPARE stmt_money_sent_at FROM @sql_money_sent_at;
EXECUTE stmt_money_sent_at;
DEALLOCATE PREPARE stmt_money_sent_at;

SELECT COUNT(*) INTO @has_money_received_at
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'money_received_at';
SET @sql_money_received_at = IF(
  @has_money_received_at = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN money_received_at DATETIME NULL AFTER money_sent_at',
  'SELECT ''resale_trade_journeys.money_received_at exists'''
);
PREPARE stmt_money_received_at FROM @sql_money_received_at;
EXECUTE stmt_money_received_at;
DEALLOCATE PREPARE stmt_money_received_at;

SELECT COUNT(*) INTO @has_purchase_contact_record
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'purchase_contact_record';
SET @sql_purchase_contact_record = IF(
  @has_purchase_contact_record = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN purchase_contact_record VARCHAR(255) NULL AFTER seller_response_at',
  'SELECT ''resale_trade_journeys.purchase_contact_record exists'''
);
PREPARE stmt_purchase_contact_record FROM @sql_purchase_contact_record;
EXECUTE stmt_purchase_contact_record;
DEALLOCATE PREPARE stmt_purchase_contact_record;

SELECT COUNT(*) INTO @has_purchase_conversation_text
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'purchase_conversation_text';
SET @sql_purchase_conversation_text = IF(
  @has_purchase_conversation_text = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN purchase_conversation_text LONGTEXT NULL AFTER purchase_contact_record',
  'SELECT ''resale_trade_journeys.purchase_conversation_text exists'''
);
PREPARE stmt_purchase_conversation_text FROM @sql_purchase_conversation_text;
EXECUTE stmt_purchase_conversation_text;
DEALLOCATE PREPARE stmt_purchase_conversation_text;

SELECT COUNT(*) INTO @has_purchase_account_number
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'purchase_account_number';
SET @sql_purchase_account_number = IF(
  @has_purchase_account_number = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN purchase_account_number VARCHAR(100) NULL AFTER money_received_at',
  'SELECT ''resale_trade_journeys.purchase_account_number exists'''
);
PREPARE stmt_purchase_account_number FROM @sql_purchase_account_number;
EXECUTE stmt_purchase_account_number;
DEALLOCATE PREPARE stmt_purchase_account_number;

SELECT COUNT(*) INTO @has_resale_contact_record
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'resale_contact_record';
SET @sql_resale_contact_record = IF(
  @has_resale_contact_record = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN resale_contact_record VARCHAR(255) NULL AFTER minimum_accept_price_krw',
  'SELECT ''resale_trade_journeys.resale_contact_record exists'''
);
PREPARE stmt_resale_contact_record FROM @sql_resale_contact_record;
EXECUTE stmt_resale_contact_record;
DEALLOCATE PREPARE stmt_resale_contact_record;

SELECT COUNT(*) INTO @has_resale_conversation_text
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'resale_conversation_text';
SET @sql_resale_conversation_text = IF(
  @has_resale_conversation_text = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN resale_conversation_text LONGTEXT NULL AFTER resale_contact_record',
  'SELECT ''resale_trade_journeys.resale_conversation_text exists'''
);
PREPARE stmt_resale_conversation_text FROM @sql_resale_conversation_text;
EXECUTE stmt_resale_conversation_text;
DEALLOCATE PREPARE stmt_resale_conversation_text;

SELECT COUNT(*) INTO @has_resale_account_number
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'resale_account_number';
SET @sql_resale_account_number = IF(
  @has_resale_account_number = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN resale_account_number VARCHAR(100) NULL AFTER resale_conversation_text',
  'SELECT ''resale_trade_journeys.resale_account_number exists'''
);
PREPARE stmt_resale_account_number FROM @sql_resale_account_number;
EXECUTE stmt_resale_account_number;
DEALLOCATE PREPARE stmt_resale_account_number;

SELECT GROUP_CONCAT(add_clause ORDER BY ord SEPARATOR ', ')
INTO @manual_verification_add_clauses
FROM (
  SELECT 1 AS ord, 'ADD COLUMN serial_number VARCHAR(100) NULL AFTER purchase_account_number' AS add_clause
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'serial_number'
  )
  UNION ALL
  SELECT 2, 'ADD COLUMN model_number VARCHAR(100) NULL AFTER serial_number'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'model_number'
  )
  UNION ALL
  SELECT 3, 'ADD COLUMN cpu_core_count INT NULL AFTER model_number'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'cpu_core_count'
  )
  UNION ALL
  SELECT 4, 'ADD COLUMN gpu_core_count INT NULL AFTER cpu_core_count'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'gpu_core_count'
  )
  UNION ALL
  SELECT 5, 'ADD COLUMN battery_cycle_count INT NULL AFTER gpu_core_count'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'battery_cycle_count'
  )
  UNION ALL
  SELECT 6, 'ADD COLUMN battery_health_percent INT NULL AFTER battery_cycle_count'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'battery_health_percent'
  )
  UNION ALL
  SELECT 7, 'ADD COLUMN applecare_status VARCHAR(100) NULL AFTER battery_health_percent'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'applecare_status'
  )
  UNION ALL
  SELECT 8, 'ADD COLUMN activation_lock_off BOOLEAN NULL AFTER applecare_status'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'activation_lock_off'
  )
  UNION ALL
  SELECT 9, 'ADD COLUMN mdm_lock_none BOOLEAN NULL AFTER activation_lock_off'
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = @target_db
      AND table_name = 'resale_trade_journeys'
      AND column_name = 'mdm_lock_none'
  )
) manual_verification_columns;

SET @sql_add_manual_verification_columns = IF(
  @manual_verification_add_clauses IS NULL OR LENGTH(@manual_verification_add_clauses) = 0,
  'SELECT ''manual verification columns exist''',
  CONCAT('ALTER TABLE resale_trade_journeys ', @manual_verification_add_clauses)
);
PREPARE stmt_add_manual_verification_columns FROM @sql_add_manual_verification_columns;
EXECUTE stmt_add_manual_verification_columns;
DEALLOCATE PREPARE stmt_add_manual_verification_columns;

-- 기존 공통 필드를 신규 분리 필드로 백필 (legacy 컬럼이 있을 때만)
SELECT COUNT(*) INTO @has_legacy_contact_record
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'contact_record';
SET @sql_backfill_legacy_contact_record = IF(
  @has_legacy_contact_record = 0,
  'SELECT ''legacy contact_record absent''',
  'UPDATE resale_trade_journeys
   SET purchase_contact_record = COALESCE(purchase_contact_record, contact_record),
       resale_contact_record = COALESCE(resale_contact_record, contact_record)
   WHERE contact_record IS NOT NULL
     AND (
       purchase_contact_record IS NULL
       OR resale_contact_record IS NULL
     )'
);
PREPARE stmt_backfill_legacy_contact_record FROM @sql_backfill_legacy_contact_record;
EXECUTE stmt_backfill_legacy_contact_record;
DEALLOCATE PREPARE stmt_backfill_legacy_contact_record;

SELECT COUNT(*) INTO @has_legacy_conversation_text
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'conversation_text';
SET @sql_backfill_legacy_conversation_text = IF(
  @has_legacy_conversation_text = 0,
  'SELECT ''legacy conversation_text absent''',
  'UPDATE resale_trade_journeys
   SET purchase_conversation_text = COALESCE(purchase_conversation_text, conversation_text),
       resale_conversation_text = COALESCE(resale_conversation_text, conversation_text)
   WHERE conversation_text IS NOT NULL
     AND (
       purchase_conversation_text IS NULL
       OR resale_conversation_text IS NULL
     )'
);
PREPARE stmt_backfill_legacy_conversation_text FROM @sql_backfill_legacy_conversation_text;
EXECUTE stmt_backfill_legacy_conversation_text;
DEALLOCATE PREPARE stmt_backfill_legacy_conversation_text;

SELECT COUNT(*) INTO @has_legacy_account_number
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'account_number';
SET @sql_backfill_legacy_account_number = IF(
  @has_legacy_account_number = 0,
  'SELECT ''legacy account_number absent''',
  'UPDATE resale_trade_journeys
   SET purchase_account_number = COALESCE(purchase_account_number, account_number),
       resale_account_number = COALESCE(resale_account_number, account_number)
   WHERE account_number IS NOT NULL
     AND (
       purchase_account_number IS NULL
       OR resale_account_number IS NULL
     )'
);
PREPARE stmt_backfill_legacy_account_number FROM @sql_backfill_legacy_account_number;
EXECUTE stmt_backfill_legacy_account_number;
DEALLOCATE PREPARE stmt_backfill_legacy_account_number;

-- 현재 기준에서 불필요/어긋난 legacy 컬럼 정리
SELECT COUNT(*) INTO @has_first_inquiry_delay_minutes
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'first_inquiry_delay_minutes';
SET @sql_drop_first_inquiry_delay_minutes = IF(
  @has_first_inquiry_delay_minutes = 0,
  'SELECT ''first_inquiry_delay_minutes already absent''',
  'ALTER TABLE resale_trade_journeys DROP COLUMN first_inquiry_delay_minutes'
);
PREPARE stmt_drop_first_inquiry_delay_minutes FROM @sql_drop_first_inquiry_delay_minutes;
EXECUTE stmt_drop_first_inquiry_delay_minutes;
DEALLOCATE PREPARE stmt_drop_first_inquiry_delay_minutes;

SET SESSION group_concat_max_len = 65535;

SELECT GROUP_CONCAT(CONCAT('DROP COLUMN `', column_name, '`') ORDER BY column_name SEPARATOR ', ')
INTO @obsolete_drop_clauses
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name IN (
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
  'SELECT ''no obsolete columns to drop''',
  CONCAT('ALTER TABLE resale_trade_journeys ', @obsolete_drop_clauses)
);
PREPARE stmt_drop_obsolete_columns FROM @sql_drop_obsolete_columns;
EXECUTE stmt_drop_obsolete_columns;
DEALLOCATE PREPARE stmt_drop_obsolete_columns;

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

-- 데이터 정규화(기존 행 반영):
-- 1) 구매 맥락(되팔이/판매 정보 없음)에서는 money_received_at -> money_sent_at로 이동
-- 2) 되팔이/판매 맥락 + 구매 정보 없음에서는 money_sent_at -> money_received_at로 이동
-- 3) 이동 후 반대쪽 필드는 NULL 처리
UPDATE resale_trade_journeys
SET money_sent_at = COALESCE(money_sent_at, money_received_at),
    money_received_at = NULL
WHERE money_received_at IS NOT NULL
  AND money_sent_at IS NULL
  AND sold_at IS NULL
  AND sale_price_krw IS NULL
  AND resale_listing_created_at IS NULL
  AND resale_listing_price_krw IS NULL
  AND resale_url IS NULL
  AND resale_platform IS NULL
  AND resale_product_id IS NULL;

UPDATE resale_trade_journeys
SET money_received_at = COALESCE(money_received_at, money_sent_at),
    money_sent_at = NULL
WHERE money_sent_at IS NOT NULL
  AND money_received_at IS NULL
  AND (
    sold_at IS NOT NULL
    OR sale_price_krw IS NOT NULL
    OR resale_listing_created_at IS NOT NULL
    OR resale_listing_price_krw IS NOT NULL
    OR resale_url IS NOT NULL
    OR resale_platform IS NOT NULL
    OR resale_product_id IS NOT NULL
  )
  AND purchased_at IS NULL
  AND purchase_price_krw IS NULL
  AND purchase_method IS NULL
  AND purchase_location IS NULL
  AND transport_cost_krw IS NULL
  AND shipping_cost_krw IS NULL
  AND payment_method IS NULL;
