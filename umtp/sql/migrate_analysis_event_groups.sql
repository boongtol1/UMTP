-- Run against the configured UMTP database before deploying grouped workers.
-- Existing rows and unique recipient identities are preserved.
SET @has_analysis_event_index = (
  SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'analysis_jobs'
    AND INDEX_NAME = 'idx_analysis_jobs_event_status'
);
SET @analysis_event_index_sql = IF(
  @has_analysis_event_index > 0,
  'SELECT ''idx_analysis_jobs_event_status exists''',
  'ALTER TABLE analysis_jobs ADD INDEX idx_analysis_jobs_event_status (source, product_id, change_fingerprint, status)'
);
PREPARE analysis_event_index_stmt FROM @analysis_event_index_sql;
EXECUTE analysis_event_index_stmt;
DEALLOCATE PREPARE analysis_event_index_stmt;
