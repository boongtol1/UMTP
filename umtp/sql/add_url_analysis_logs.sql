USE UMTP_RB;

CREATE TABLE IF NOT EXISTS url_analysis_logs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  url VARCHAR(1000) NOT NULL,
  source VARCHAR(50) NULL,
  title VARCHAR(255) NULL,
  body_text TEXT NULL,
  listing_price_krw INT NULL,
  product_type VARCHAR(100) NULL,
  chip VARCHAR(50) NULL,
  screen_inch INT NULL,
  ram_gb INT NULL,
  ssd_gb INT NULL,
  fair_price_krw INT NULL,
  diff_ratio DECIMAL(10,2) NULL,
  is_alert_target BOOLEAN NULL,
  status VARCHAR(20) NOT NULL,
  reason VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user_url_created_at (user_id, url(255), created_at),
  KEY idx_status_created_at (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
