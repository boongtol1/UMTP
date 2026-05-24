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
  color VARCHAR(50) NULL,
  keyboard_layout VARCHAR(50) NULL,
  fair_price_krw INT NULL,
  discount_rate_percent DECIMAL(7,2) NULL,
  expected_profit_krw INT NULL,
  risk_score INT NULL,
  reason_tags LONGTEXT NULL,

  -- 3. 판매자 연락
  contacted_at DATETIME NULL,
  seller_response_at DATETIME NULL,
  response_time_minutes INT GENERATED ALWAYS AS (
    CASE
      WHEN contacted_at IS NULL OR seller_response_at IS NULL THEN NULL
      ELSE TIMESTAMPDIFF(MINUTE, contacted_at, seller_response_at)
    END
  ) STORED,
  seller_answer_text LONGTEXT NULL,
  negotiable TINYINT(1) NULL,
  seller_tone VARCHAR(50) NULL,
  suspicious_points LONGTEXT NULL,
  confirmed_price_krw INT NULL,

  -- 4. 구매 결정
  decision_at DATETIME NULL,
  decision_result VARCHAR(20) NULL,
  decision_reason LONGTEXT NULL,
  target_purchase_price_krw INT NULL,
  expected_sale_price_krw INT NULL,
  expected_net_profit_krw INT NULL,
  expected_sale_duration_days INT NULL,

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

  -- 6. 실물 검수
  serial_number VARCHAR(100) NULL,
  model_number VARCHAR(100) NULL,
  applecare_status VARCHAR(50) NULL,
  activation_lock_off TINYINT(1) NULL,
  mdm_lock_none TINYINT(1) NULL,
  cpu_core_count INT NULL,
  gpu_core_count INT NULL,
  battery_health_percent INT NULL,
  battery_cycle_count INT NULL,
  battery_condition VARCHAR(50) NULL,
  truetone_ok TINYINT(1) NULL,
  display_condition VARCHAR(100) NULL,
  keyboard_condition VARCHAR(100) NULL,
  trackpad_condition VARCHAR(100) NULL,
  speaker_condition VARCHAR(100) NULL,
  camera_condition VARCHAR(100) NULL,
  wifi_bluetooth_ok TINYINT(1) NULL,
  exterior_grade VARCHAR(50) NULL,
  included_items LONGTEXT NULL,
  repair_suspected TINYINT(1) NULL,
  inspection_notes LONGTEXT NULL,

  -- 7. 되팔이 준비
  cleaned_at DATETIME NULL,
  photo_taken_at DATETIME NULL,
  resale_title VARCHAR(500) NULL,
  resale_body_text LONGTEXT NULL,
  resale_photo_count INT NULL,
  resale_listing_price_krw INT NULL,
  minimum_accept_price_krw INT NULL,
  resale_platform VARCHAR(50) NULL,
  resale_strategy_notes LONGTEXT NULL,

  -- 8. 되팔이 글 업로드
  resale_listing_created_at DATETIME NULL,
  resale_url TEXT NULL,
  resale_product_id VARCHAR(100) NULL,
  initial_resale_price_krw INT NULL,
  upload_time_slot VARCHAR(50) NULL,

  -- 9. 판매 중 반응
  view_count INT NULL,
  favorite_count INT NULL,
  inquiry_count INT NULL,
  first_inquiry_at DATETIME NULL,
  first_inquiry_delay_minutes INT GENERATED ALWAYS AS (
    CASE
      WHEN resale_listing_created_at IS NULL OR first_inquiry_at IS NULL THEN NULL
      ELSE TIMESTAMPDIFF(MINUTE, resale_listing_created_at, first_inquiry_at)
    END
  ) STORED,
  negotiation_count INT NULL,
  price_drop_count INT NULL,
  price_drop_history LONGTEXT NULL,
  buyer_questions LONGTEXT NULL,
  common_objections LONGTEXT NULL,

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
  KEY idx_resale_trade_journeys_stage (current_stage),
  KEY idx_resale_trade_journeys_discovered_at (discovered_at),
  KEY idx_resale_trade_journeys_purchased_at (purchased_at),
  KEY idx_resale_trade_journeys_sold_at (sold_at),
  UNIQUE KEY uq_resale_trade_journeys_source_product (source, product_id),
  UNIQUE KEY uq_resale_trade_journeys_source_url (source, url_digest)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_cpu_core_count
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'cpu_core_count';
SET @sql_cpu_core_count = IF(
  @has_cpu_core_count = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN cpu_core_count INT NULL AFTER mdm_lock_none',
  'SELECT ''resale_trade_journeys.cpu_core_count exists'''
);
PREPARE stmt_cpu_core_count FROM @sql_cpu_core_count;
EXECUTE stmt_cpu_core_count;
DEALLOCATE PREPARE stmt_cpu_core_count;

SELECT COUNT(*) INTO @has_gpu_core_count
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'resale_trade_journeys'
  AND column_name = 'gpu_core_count';
SET @sql_gpu_core_count = IF(
  @has_gpu_core_count = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN gpu_core_count INT NULL AFTER cpu_core_count',
  'SELECT ''resale_trade_journeys.gpu_core_count exists'''
);
PREPARE stmt_gpu_core_count FROM @sql_gpu_core_count;
EXECUTE stmt_gpu_core_count;
DEALLOCATE PREPARE stmt_gpu_core_count;
