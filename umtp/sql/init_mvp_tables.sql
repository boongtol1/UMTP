CREATE DATABASE IF NOT EXISTS UMTP_RB
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE UMTP_RB;

CREATE TABLE IF NOT EXISTS mac_fair_prices (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  product_type VARCHAR(100) NOT NULL,
  chip VARCHAR(50) NOT NULL,
  screen_inch INT NOT NULL,
  ram_gb INT NOT NULL,
  ssd_gb INT NOT NULL,
  fair_price_krw INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_mac_fair_price_spec (product_type, chip, screen_inch, ram_gb, ssd_gb)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS listing_analysis_results (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  body_text TEXT NULL,
  product_type VARCHAR(100) NOT NULL,
  chip VARCHAR(50) NOT NULL,
  screen_inch INT NOT NULL,
  ram_gb INT NOT NULL,
  ssd_gb INT NOT NULL,
  listing_price_krw INT NOT NULL,
  fair_price_krw INT NOT NULL,
  diff_amount_krw INT NOT NULL,
  diff_ratio DECIMAL(10,2) NOT NULL,
  is_alert_target BOOLEAN NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO mac_fair_prices (
  product_type,
  chip,
  screen_inch,
  ram_gb,
  ssd_gb,
  fair_price_krw
)
VALUES (
  'MacBook Air',
  'M1',
  13,
  8,
  256,
  550000
)
ON DUPLICATE KEY UPDATE
  fair_price_krw = VALUES(fair_price_krw);
