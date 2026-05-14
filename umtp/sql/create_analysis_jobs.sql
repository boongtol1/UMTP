USE UMTP_RB;

CREATE TABLE IF NOT EXISTS analysis_jobs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source VARCHAR(50) NOT NULL DEFAULT 'joongna',
  product_id VARCHAR(100) NULL,
  url TEXT NOT NULL,
  title VARCHAR(500) NULL,
  price_krw INT NULL,
  search_keyword VARCHAR(255) NULL,
  user_id VARCHAR(100) NULL,
  watch_rule_id BIGINT UNSIGNED NULL,
  trigger_reason VARCHAR(100) NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  error_message TEXT NULL,
  attempts INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP NULL,
  processed_at TIMESTAMP NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_analysis_jobs_status (status),
  KEY idx_analysis_jobs_created_at (created_at),
  KEY idx_analysis_jobs_watch_rule (watch_rule_id),
  KEY idx_analysis_jobs_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
