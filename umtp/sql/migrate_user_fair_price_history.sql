USE UMTP_RB;

CREATE TABLE IF NOT EXISTS user_fair_price_history (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_fair_price_id BIGINT UNSIGNED NOT NULL,
  user_id VARCHAR(100) NOT NULL,
  product_type VARCHAR(100) NOT NULL,
  chip VARCHAR(50) NOT NULL,
  screen_inch INT NOT NULL,
  ram_gb INT NOT NULL,
  ssd_gb INT NOT NULL,
  old_fair_price_krw INT NULL,
  new_fair_price_krw INT NULL,
  old_desired_price_krw INT NULL,
  new_desired_price_krw INT NULL,
  old_drop_percent DECIMAL(10,2) NULL,
  new_drop_percent DECIMAL(10,2) NULL,
  change_type VARCHAR(20) NOT NULL DEFAULT 'updated',
  changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user_fair_price_history_rule_time (user_fair_price_id, changed_at),
  KEY idx_user_fair_price_history_user_time (user_id, changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
