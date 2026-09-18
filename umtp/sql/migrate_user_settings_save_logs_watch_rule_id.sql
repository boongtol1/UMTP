USE UMTP_RB;

-- Prerequisites: user_fair_prices and user_settings_save_logs already exist.
-- Repair only successful saves for the four added Mac lineups. The actual
-- rule ID is user_fair_prices.id, not an ID from deprecated user_watch_rules.
-- Match the complete unique spec key, never just a search keyword. A rule
-- created after the log may be a replacement for a deleted rule: leave it alone.
-- Preserve request/response JSON as the original historical API exchange.
-- Existing IDs, failed saves, and logs without a confirmed match stay unchanged.
-- This UPDATE is atomic and safe to rerun.
UPDATE user_settings_save_logs AS save_log
JOIN user_fair_prices AS rule
  ON rule.user_id = save_log.user_id
 AND rule.product_type = JSON_UNQUOTE(JSON_EXTRACT(save_log.request_json, '$.product_type'))
 AND rule.chip = JSON_UNQUOTE(JSON_EXTRACT(save_log.request_json, '$.chip'))
 AND rule.screen_inch = JSON_EXTRACT(save_log.request_json, '$.screen_inch')
 AND rule.ram_gb = JSON_EXTRACT(save_log.request_json, '$.ram_gb')
 AND rule.ssd_gb = JSON_EXTRACT(save_log.request_json, '$.ssd_gb')
SET save_log.watch_rule_id = rule.id
WHERE save_log.watch_rule_id IS NULL
  AND save_log.success = 1
  AND save_log.action_type IN ('create_watch_rule', 'update_watch_rule')
  AND rule.product_type IN ('MacBook Pro', 'MacBook Neo', 'iMac', 'Mac Studio')
  AND rule.created_at <= save_log.created_at
  AND JSON_TYPE(JSON_EXTRACT(save_log.request_json, '$.screen_inch')) = 'INTEGER'
  AND JSON_TYPE(JSON_EXTRACT(save_log.request_json, '$.ram_gb')) = 'INTEGER'
  AND JSON_TYPE(JSON_EXTRACT(save_log.request_json, '$.ssd_gb')) = 'INTEGER'
  AND (
    JSON_EXTRACT(save_log.response_json, '$.item.id') IS NULL
    OR JSON_TYPE(JSON_EXTRACT(save_log.response_json, '$.item.id')) = 'NULL'
    OR JSON_EXTRACT(save_log.response_json, '$.item.id') = rule.id
  );

SELECT ROW_COUNT() AS repaired_save_log_count;
