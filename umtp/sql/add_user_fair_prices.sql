USE UMTP_RB;

CREATE TABLE IF NOT EXISTS user_fair_prices (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  product_type VARCHAR(100) NOT NULL,
  chip VARCHAR(50) NOT NULL,
  screen_inch INT NOT NULL,
  ram_gb INT NOT NULL,
  ssd_gb INT NOT NULL,
  fair_price_krw INT NOT NULL,
  alert_drop_rate_percent DECIMAL(5,2) NOT NULL,
  alert_price_direction VARCHAR(32) NOT NULL DEFAULT 'BELOW_OR_EQUAL',
  target_buy_price_krw INT
    GENERATED ALWAYS AS (
      ROUND(
        fair_price_krw * (
          1 - (alert_drop_rate_percent / 100)
        )
      )
    ) STORED,
  min_price_krw INT NULL,
  max_price_krw INT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  condition_change_candidate_notice_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  search_keyword VARCHAR(255) NULL,
  poll_interval_seconds INT NOT NULL DEFAULT 60,
  force_poll BOOLEAN NOT NULL DEFAULT FALSE,
  last_poll_requested_at TIMESTAMP NULL,
  last_polled_at TIMESTAMP NULL,
  saved_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_fair_price_spec (
    user_id,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb
  ),
  KEY idx_user_fair_prices_due (enabled, last_polled_at),
  KEY idx_user_fair_prices_force_poll (force_poll)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_saved_at
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'user_fair_prices'
  AND column_name = 'saved_at';
SET @sql_saved_at = IF(
  @has_saved_at = 0,
  'ALTER TABLE user_fair_prices ADD COLUMN saved_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP AFTER last_polled_at',
  'SELECT "saved_at exists"'
);
PREPARE stmt_saved_at FROM @sql_saved_at;
EXECUTE stmt_saved_at;
DEALLOCATE PREPARE stmt_saved_at;

SELECT COUNT(*) INTO @has_condition_change_candidate_notice_enabled
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'user_fair_prices'
  AND column_name = 'condition_change_candidate_notice_enabled';
SET @sql_condition_change_candidate_notice_enabled = IF(
  @has_condition_change_candidate_notice_enabled = 0,
  'ALTER TABLE user_fair_prices ADD COLUMN condition_change_candidate_notice_enabled BOOLEAN NOT NULL DEFAULT FALSE AFTER enabled',
  'SELECT "condition_change_candidate_notice_enabled exists"'
);
PREPARE stmt_condition_change_candidate_notice_enabled FROM @sql_condition_change_candidate_notice_enabled;
EXECUTE stmt_condition_change_candidate_notice_enabled;
DEALLOCATE PREPARE stmt_condition_change_candidate_notice_enabled;

INSERT INTO user_fair_prices (
  user_id,
  product_type,
  chip,
  screen_inch,
  ram_gb,
  ssd_gb,
  fair_price_krw,
  alert_drop_rate_percent,
  alert_price_direction,
  min_price_krw,
  max_price_krw,
  enabled,
  condition_change_candidate_notice_enabled,
  search_keyword,
  poll_interval_seconds,
  force_poll,
  last_poll_requested_at,
  last_polled_at,
  saved_at
)
VALUES (
  'test_user',
  'MacBook Air',
  'M1',
  13,
  8,
  256,
  550000,
  20,
  'BELOW_OR_EQUAL',
  NULL,
  NULL,
  TRUE,
  FALSE,
  'm1맥북에어',
  60,
  TRUE,
  CURRENT_TIMESTAMP,
  NULL,
  CURRENT_TIMESTAMP
)
ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw),
  alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
  alert_price_direction = VALUES(alert_price_direction),
  min_price_krw = VALUES(min_price_krw),
  max_price_krw = VALUES(max_price_krw),
  enabled = VALUES(enabled),
  condition_change_candidate_notice_enabled = VALUES(condition_change_candidate_notice_enabled),
  search_keyword = VALUES(search_keyword),
  poll_interval_seconds = VALUES(poll_interval_seconds),
  force_poll = VALUES(force_poll),
  last_poll_requested_at = VALUES(last_poll_requested_at),
  last_polled_at = VALUES(last_polled_at),
  saved_at = CURRENT_TIMESTAMP;
