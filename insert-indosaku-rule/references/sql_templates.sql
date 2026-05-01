-- =====================================================
-- Credit Rule Insert Template (t_credit_default_rule_setting)
-- =====================================================
-- Placeholders:
-- ${new_rule_code}
-- ${new_rule_name}
-- ${new_rule_sort}
-- ${new_rule_describe}
-- ${special_params_json}             e.g. fdcL30dAvgLoanAmtCny,modelScore
-- ${special_params_json_remarks}     e.g. fdc在前，model在后
-- ${operator}

SET @operator := '${operator}';
SET @now := NOW();

-- 1) Pre-check templates
SELECT rule_code, rule_name
FROM t_credit_default_rule_setting
WHERE rule_code IN (
  'CURRENT_PRODUCT_FIRST_PERIOD_REPAY_CNT_AND_MODEL',
  'FDC_MAX_TOTAL_AMOUNT_AND_MODEL'
);

-- 2) Insert with fallback template
INSERT INTO t_credit_default_rule_setting (
    rule_code, rule_name, data_source, decision_type,
    threshold_number, min, max, min_calculate_method, max_calculate_method,
    min_max_connect, is_config, increase_level, score_version,
    special_params_json, special_params_json_remarks,
    model_url, model_url_two, rule_sort, rule_describe,
    is_show, is_start, create_date, update_date, creator, updater,
    min_left, min_right, min_left_calculate_method, min_right_calculate_method,
    min_left_right_type, max_left, max_right, max_left_calculate_method,
    max_right_calculate_method, max_left_right_type
)
SELECT
    '${new_rule_code}', '${new_rule_name}',
    t.data_source, t.decision_type,
    t.threshold_number, t.min, t.max, t.min_calculate_method, t.max_calculate_method,
    t.min_max_connect, t.is_config, t.increase_level, t.score_version,
    '${special_params_json}', '${special_params_json_remarks}',
    t.model_url, t.model_url_two,
    ${new_rule_sort}, '${new_rule_describe}',
    t.is_show, t.is_start, @now, @now, @operator, @operator,
    t.min_left, t.min_right, t.min_left_calculate_method, t.min_right_calculate_method,
    t.min_left_right_type, t.max_left, t.max_right, t.max_left_calculate_method,
    t.max_right_calculate_method, t.max_left_right_type
FROM (
  SELECT *
  FROM t_credit_default_rule_setting
  WHERE rule_code IN ('FDC_MAX_TOTAL_AMOUNT_AND_MODEL','CURRENT_PRODUCT_FIRST_PERIOD_REPAY_CNT_AND_MODEL')
  ORDER BY CASE WHEN rule_code='FDC_MAX_TOTAL_AMOUNT_AND_MODEL' THEN 0 ELSE 1 END
  LIMIT 1
) t
WHERE NOT EXISTS (
  SELECT 1 FROM t_credit_default_rule_setting x
  WHERE x.rule_code='${new_rule_code}'
);

-- 3) Post-check
SELECT rule_code, rule_name, special_params_json, threshold_number, min, max, rule_sort
FROM t_credit_default_rule_setting
WHERE rule_code='${new_rule_code}';

-- =====================================================
-- Batch update special_params_json (comma-separated)
-- =====================================================
UPDATE t_credit_default_rule_setting
SET special_params_json='fdcL30dAvgLoanAmtCny,modelScore',
    special_params_json_remarks='fdc在前，model在后',
    update_date=NOW(),
    updater='${operator}'
WHERE rule_code IN (
    'FP_REPAY_EQ0_MODEL_FDC_L30D_AVG_AMT_CNY',
    'FP_REPAY_EQ1_MODEL_FDC_L30D_AVG_AMT_CNY',
    'FP_REPAY_GE2_MODEL_FDC_L30D_AVG_AMT_CNY',
    'FP_REPAY_1TO3_MODEL_FDC_L30D_AVG_AMT_CNY',
    'FP_REPAY_GE4_MODEL_FDC_L30D_AVG_AMT_CNY'
);
