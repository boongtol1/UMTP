USE UMTP_RB;

CREATE TABLE IF NOT EXISTS user_watch_rules (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  product_type VARCHAR(100) NULL,
  chip VARCHAR(20) NULL,
  screen_inch INT NULL,
  ram_gb INT NULL,
  ssd_gb INT NULL,
  search_keyword VARCHAR(255) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  poll_interval_seconds INT NOT NULL DEFAULT 60,
  target_price_krw INT NULL,
  fair_price_krw INT NULL,
  alert_drop_rate_percent DECIMAL(5,2) NULL,
  last_polled_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_user_watch_keyword (user_id, search_keyword),
  KEY idx_user_watch_enabled (enabled),
  KEY idx_user_watch_due (enabled, last_polled_at),
  KEY idx_user_watch_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
