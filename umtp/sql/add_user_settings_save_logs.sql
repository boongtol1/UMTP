USE UMTP_RB;

CREATE TABLE IF NOT EXISTS user_settings_save_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    watch_rule_id BIGINT NULL,
    action_type VARCHAR(64) NOT NULL,
    request_json JSON NULL,
    response_json JSON NULL,
    success TINYINT(1) NOT NULL DEFAULT 0,
    error_code VARCHAR(128) NULL,
    error_message TEXT NULL,
    metadata_json JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user_settings_save_logs_user_created_at (user_id, created_at),
    INDEX idx_user_settings_save_logs_watch_rule_created_at (watch_rule_id, created_at),
    INDEX idx_user_settings_save_logs_action_created_at (action_type, created_at),
    INDEX idx_user_settings_save_logs_success_created_at (success, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
