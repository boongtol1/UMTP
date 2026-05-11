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
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_fair_price_spec (
    user_id,
    product_type,
    chip,
    screen_inch,
    ram_gb,
    ssd_gb
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO user_fair_prices (
  user_id,
  product_type,
  chip,
  screen_inch,
  ram_gb,
  ssd_gb,
  fair_price_krw,
  alert_drop_rate_percent
)
VALUES (
  'test_user',
  'MacBook Air',
  'M1',
  13,
  8,
  256,
  550000,
  20
)
ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw),
  alert_drop_rate_percent = VALUES(alert_drop_rate_percent);
