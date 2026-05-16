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
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  search_keyword VARCHAR(255) NULL,
  poll_interval_seconds INT NOT NULL DEFAULT 60,
  force_poll BOOLEAN NOT NULL DEFAULT FALSE,
  last_poll_requested_at TIMESTAMP NULL,
  last_polled_at TIMESTAMP NULL,
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
  enabled,
  search_keyword,
  poll_interval_seconds,
  force_poll,
  last_poll_requested_at,
  last_polled_at
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
  TRUE,
  'm1맥북에어',
  60,
  TRUE,
  CURRENT_TIMESTAMP,
  NULL
)
ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw),
  alert_drop_rate_percent = VALUES(alert_drop_rate_percent),
  alert_price_direction = VALUES(alert_price_direction),
  enabled = VALUES(enabled),
  search_keyword = VALUES(search_keyword),
  poll_interval_seconds = VALUES(poll_interval_seconds),
  force_poll = VALUES(force_poll),
  last_poll_requested_at = VALUES(last_poll_requested_at),
  last_polled_at = VALUES(last_polled_at);
