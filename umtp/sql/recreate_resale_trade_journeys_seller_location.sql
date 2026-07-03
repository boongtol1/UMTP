USE UMTP_RB;

SET @target_db = DATABASE();

-- Recreate seller_location in-place while preserving existing values.
SET @has_seller_location = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'seller_location'
);

SET @has_backup = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'seller_location_recreate_backup'
);
SET @has_backup_initial = @has_backup;

SET @has_updated_at = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'updated_at'
);

SET @has_updated_at_backup = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'seller_location_updated_at_recreate_backup'
);
SET @has_updated_at_backup_initial = @has_updated_at_backup;

SET @sql = IF(
  @has_seller_location > 0 AND @has_backup = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN seller_location_recreate_backup VARCHAR(255) NULL AFTER seller_location',
  'SELECT ''seller_location backup column already present or source missing'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_backup = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'seller_location_recreate_backup'
);

SET @sql = IF(
  @has_updated_at > 0 AND @has_updated_at_backup = 0,
  'ALTER TABLE resale_trade_journeys ADD COLUMN seller_location_updated_at_recreate_backup DATETIME NULL',
  'SELECT ''seller_location updated_at backup column already present or source missing'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_updated_at_backup = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'seller_location_updated_at_recreate_backup'
);

SET @sql = IF(
  @has_updated_at > 0 AND @has_updated_at_backup_initial = 0 AND @has_updated_at_backup > 0,
  'UPDATE resale_trade_journeys SET seller_location_updated_at_recreate_backup = updated_at',
  'SELECT ''seller_location updated_at backup copy skipped'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  @has_seller_location > 0 AND @has_backup_initial = 0 AND @has_backup > 0,
  'UPDATE resale_trade_journeys SET seller_location_recreate_backup = seller_location',
  'SELECT ''seller_location backup copy skipped'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  @has_seller_location > 0,
  'ALTER TABLE resale_trade_journeys DROP COLUMN seller_location',
  'SELECT ''seller_location source column already absent'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE resale_trade_journeys
  ADD COLUMN seller_location VARCHAR(255) NULL AFTER seller_nickname;

SET @has_backup = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @target_db
    AND table_name = 'resale_trade_journeys'
    AND column_name = 'seller_location_recreate_backup'
);

SET @sql = IF(
  @has_backup > 0 AND @has_updated_at_backup > 0,
  'UPDATE resale_trade_journeys SET seller_location = seller_location_recreate_backup, updated_at = seller_location_updated_at_recreate_backup',
  IF(
    @has_backup > 0,
    'UPDATE resale_trade_journeys SET seller_location = seller_location_recreate_backup',
    'SELECT ''seller_location restore skipped'''
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  @has_updated_at_backup > 0,
  'ALTER TABLE resale_trade_journeys DROP COLUMN seller_location_updated_at_recreate_backup',
  'SELECT ''seller_location updated_at backup drop skipped'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  @has_backup > 0,
  'ALTER TABLE resale_trade_journeys DROP COLUMN seller_location_recreate_backup',
  'SELECT ''seller_location backup drop skipped'''
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
