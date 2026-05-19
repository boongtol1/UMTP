CREATE TABLE IF NOT EXISTS worker_heartbeats (
  worker_name VARCHAR(100) NOT NULL,
  last_heartbeat_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_status VARCHAR(30) NOT NULL DEFAULT 'ok',
  last_detail VARCHAR(255) NULL,
  last_stats_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (worker_name),
  KEY idx_worker_heartbeats_last_heartbeat_at (last_heartbeat_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
