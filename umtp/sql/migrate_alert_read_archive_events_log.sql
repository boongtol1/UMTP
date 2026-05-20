USE UMTP_RB;

CREATE TABLE IF NOT EXISTS alert_read_archive_events (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  alert_event_id BIGINT UNSIGNED NULL,
  action_type VARCHAR(50) NOT NULL,
  requested_count INT NULL,
  affected_count INT NULL,
  skipped_count INT NULL,
  not_found_ids_json TEXT NULL,
  reason VARCHAR(100) NULL,
  metadata_json LONGTEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_alert_read_archive_events_user_created_at (user_id, created_at),
  KEY idx_alert_read_archive_events_action_created_at (action_type, created_at),
  KEY idx_alert_read_archive_events_alert_event_id (alert_event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
