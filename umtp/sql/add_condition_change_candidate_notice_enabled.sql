USE UMTP_RB;

SET @schema_name = DATABASE();

SET @has_condition_change_candidate_notice_enabled = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'condition_change_candidate_notice_enabled'
);
SET @condition_change_candidate_notice_enabled_sql = IF(
  @has_condition_change_candidate_notice_enabled > 0,
  'SELECT ''condition_change_candidate_notice_enabled already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN condition_change_candidate_notice_enabled BOOLEAN NOT NULL DEFAULT FALSE AFTER enabled'
);
PREPARE stmt FROM @condition_change_candidate_notice_enabled_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE user_fair_prices
SET condition_change_candidate_notice_enabled = FALSE
WHERE condition_change_candidate_notice_enabled IS NULL;
