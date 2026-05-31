USE UMTP_RB;

CREATE TABLE IF NOT EXISTS fraud_store_status_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  store_id VARCHAR(64) NOT NULL,
  checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status ENUM('active','inactive','suspended','deleted','unknown','error') NOT NULL DEFAULT 'unknown',
  is_active TINYINT(1) NOT NULL DEFAULT 0,
  raw_status_text TEXT NULL,
  raw_response_json JSON NULL,
  first_seen_product_id VARCHAR(64) NULL,
  first_seen_sort_date DATETIME NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_store_checked (store_id, checked_at),
  INDEX idx_status_checked (status, checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fraud_store_activity_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  store_id VARCHAR(64) NOT NULL,
  checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  posts_last_1h INT NOT NULL DEFAULT 0,
  posts_last_6h INT NOT NULL DEFAULT 0,
  posts_last_24h INT NOT NULL DEFAULT 0,
  posts_last_7d INT NOT NULL DEFAULT 0,
  visible_product_count INT NULL,
  first_seen_product_id VARCHAR(64) NULL,
  first_seen_sort_date DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_store_checked (store_id, checked_at),
  INDEX idx_checked_at (checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fraud_training_label_candidates (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id VARCHAR(64) NOT NULL,
  store_id VARCHAR(64) NOT NULL,
  listing_sort_date DATETIME NOT NULL,
  discovered_at DATETIME NULL,
  first_inactive_at DATETIME NULL,
  inactive_after_minutes INT NULL,
  label TINYINT NULL,
  label_reason VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_product_id (product_id),
  INDEX idx_store_id (store_id),
  INDEX idx_label (label),
  INDEX idx_listing_sort_date (listing_sort_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
