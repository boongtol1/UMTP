USE UMTP_RB;

CREATE TABLE IF NOT EXISTS search_queries (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source VARCHAR(50) NOT NULL,
  normalized_keyword VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_polled_at DATETIME NULL,
  last_status VARCHAR(30) NOT NULL DEFAULT 'ok',
  UNIQUE KEY uq_search_queries_source_keyword (source, normalized_keyword),
  KEY idx_search_queries_last_polled_at (last_polled_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS search_results (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  search_query_id BIGINT UNSIGNED NOT NULL,
  product_id VARCHAR(100) NOT NULL,
  title VARCHAR(500) NULL,
  price INT NULL,
  sort_date DATETIME NULL,
  url TEXT NULL,
  raw_json LONGTEXT NULL,
  fetched_at DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_search_results_query_fetched (search_query_id, fetched_at),
  KEY idx_search_results_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
