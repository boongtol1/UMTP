USE UMTP_RB;

CREATE TABLE IF NOT EXISTS joongna_seen_products (
  seq BIGINT UNSIGNED NOT NULL,
  search_word VARCHAR(255) NOT NULL,
  title VARCHAR(255) NULL,
  price INT NULL,
  product_url VARCHAR(1000) NOT NULL,
  image_url VARCHAR(1000) NULL,
  sort_date VARCHAR(100) NULL,
  first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (seq),
  KEY idx_search_word_first_seen_at (search_word, first_seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
