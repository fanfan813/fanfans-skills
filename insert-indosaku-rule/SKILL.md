---
name: insert-indosaku-rule
description: End-to-end workflow for Indosaku credit or decision rule delivery from Java development to DB insertion. Use when adding or modifying ruleCode, enforcing ruleCode constraints, registering switch-case dispatch logic, and generating INSERT/UPDATE SQL for credit or decision rule config tables.
---

# Insert Indosaku Rule

将规则从“开发完成”推进到“配置可执行”的标准流程。

## 适用范围

- 新增或修改 `ruleCode`
- 需要同时处理 Java 规则代码与配置表
- 需要生成授信规则或决策规则的入库 SQL
- 需要确认 `special_params_json` / `special_params_json_remarks` 与代码中的 `min/max` 参数顺序

## 关键约束

- `ruleCode` 长度必须 `<= 64`
- 先判定规则类型，再选择代码链路和配置表，禁止默认按授信规则处理所有需求
- 授信规则：`ruleCode` 必须与 `CreditRuleServiceImpl` 方法名一致，并在 `CreditCheckRiskServiceImpl` 中分发
- 决策规则：`ruleCode` 必须与 `GuideInternationalRuleRiskBatch1ServiceImpl` 方法名一致，并在 `CheckRiskServiceImpl` 中分发
- `special_params_json` 使用逗号分隔格式，例如：`fdcL30dAvgLoanAmtCny,modelScore`
- `special_params_json_remarks` 必须同步填写，用中文说明每个参数的含义和顺序，例如：`fdc在前，model在后`
- `special_params_json` 参数名优先使用用户明确指定的名称；用户已指定 `cover` 时，禁止自行改成 `asfSingaCover` 等同义名称
- 当规则逻辑要求“参数顺序”时，代码中的 `min/max` 与 `special_params_json` 顺序必须一致
- 如果规则从 `ruleName` 解析模型名，入库 SQL 必须保证：
  - 单模型规则：`rule_name` 的最后一段为实际模型名
  - 双模型规则：`rule_name` 的最后两段为实际模型名
  - `rule_name` 分隔符必须与代码解析逻辑兼容，例如代码按 `+` 或 `,` 拆分时，SQL 示例也必须使用兼容分隔符

## 开发到落库 SOP

### Step 1: 判定规则类型

根据用户需求、目标 Service、现有规则模板判断规则类型：

- 授信规则（credit）：
  - 目标接口通常是 `CreditRuleService`
  - 实现通常在 `CreditRuleServiceImpl`
  - 分发通常在 `CreditCheckRiskServiceImpl`
  - 默认配置表是 `t_credit_default_rule_setting`
- 决策规则（decision）：
  - 目标接口通常是 `GuideInternationalRuleRiskBatch1Service`
  - 实现通常在 `GuideInternationalRuleRiskBatch1ServiceImpl`
  - 分发通常在 `CheckRiskServiceImpl`
  - 默认配置表是 `t_default_config_risk_rule_setting`
  - 商户模型实际执行列表来自 `t_merchant_risk_rule_setting`，默认配置入库后仍需确认是否同步到目标商户/模型

若用户点名文件，例如 `GuideInternationalRuleRiskBatch1Service.java`，优先按决策规则处理。

### Step 2: 设计 ruleCode 和参数顺序

1. 确认 `ruleCode` 语义清晰且长度 <= 64
2. 确认可配置参数顺序，例如：
   - `fdcL30dAvgLoanAmtCny,modelScore`
   - 对应代码：`min=fdcL30dAvgLoanAmtCny`，`max=modelScore`
3. 对设备品牌、包名、产品类型等硬编码前置条件，命名中要明确体现核心限定词，例如 `DEVICE_BRAND`
4. 区分“固定前置条件”和“可配置阈值字段”：固定条件写进 `ruleCode` / `rule_name` / `rule_describe`，可配置阈值才写入 `special_params_json` 并对应代码 `min/max`

### Step 3A: 代码开发（授信 credit）

必须同时修改：

1. `CreditRuleService` 增加方法签名
2. `CreditRuleServiceImpl` 增加规则方法与私有构建逻辑
3. `CreditCheckRiskServiceImpl` 的 `switch (ruleCode)` 增加 case 分发

检查命令：

```bash
rg -n "<RULE_CODE>" src/main/java/com/yuctime/service/credit/CreditRuleService.java src/main/java/com/yuctime/service/impl/credit/CreditRuleServiceImpl.java src/main/java/com/yuctime/service/impl/credit/CreditCheckRiskServiceImpl.java
```

### Step 3B: 代码开发（决策 decision）

必须同时修改：

1. `GuideInternationalRuleRiskBatch1Service` 增加方法签名
2. `GuideInternationalRuleRiskBatch1ServiceImpl` 增加规则方法与私有构建逻辑
3. `CheckRiskServiceImpl` 的 `switch (ruleCode)` 增加 case 分发

检查命令：

```bash
rg -n "<RULE_CODE>" src/main/java/com/yuctime/service/rule/GuideInternationalRuleRiskBatch1Service.java src/main/java/com/yuctime/service/impl/rule/GuideInternationalRuleRiskBatch1ServiceImpl.java src/main/java/com/yuctime/service/impl/risk/CheckRiskServiceImpl.java
```

### Step 4: 编译验证

```bash
mvn -q -DskipTests compile
```

### Step 5A: 生成授信 credit 配置 SQL

默认生成显式 `INSERT ... VALUES`，禁止默认使用 `INSERT ... SELECT`。只有用户明确要求“克隆模板”时，才生成 `INSERT ... SELECT`。

生成 SQL 前必须明确每个字段来源，不能凭经验填不确认的字段：

1. 规则业务字段：由当前需求确定
   - `rule_code`
   - `rule_name`
   - `special_params_json`
   - `special_params_json_remarks`
   - `rule_describe`
2. 模板配置字段：必须从目标环境已有相似规则只读查询后继承或由用户明确指定
   - `data_source`
   - `decision_type`
   - `threshold_number`
   - `min`
   - `max`
   - `min_calculate_method`
   - `max_calculate_method`
   - `min_max_connect`
   - `is_config`
   - `increase_level`
   - `score_version`
   - `model_url`
   - `model_url_two`
   - `is_show`
   - `is_start`
   - `min_left`
   - `min_right`
   - `min_left_calculate_method`
   - `min_right_calculate_method`
   - `min_left_right_type`
   - `max_left`
   - `max_right`
   - `max_left_calculate_method`
   - `max_right_calculate_method`
   - `max_left_right_type`
3. 用户明确指定字段：以用户要求为准，例如用户说 `rule_sort` 都用 `1`，则固定为 `1`
4. 无法从需求、用户要求或数据库确认的字段：不要擅自填默认值，必须显式标注为待确认，并在最终交付列出“仍需确认字段”

如果用户要求“参考已有数据”“prod”“indo-prod”，必须先组合使用 `readonly-db-python` 只读查询目标环境：

- 查询相近模板规则真实字段值，例如 `decision_type`、`threshold_number`、`min/max`、计算符、`increase_level`、启停和扩展阈值字段
- 查询目标 `rule_code` 是否已存在，避免重复入库
- 禁止在未查询目标环境前给出带大量默认假设的最终 SQL

常用授信模板参考：

- `firstPeriodRepayCnt + model`：`CURRENT_PRODUCT_FIRST_PERIOD_REPAY_CNT_AND_MODEL`
- `firstProductRepayCnt + double model`：优先找已有 `DOUBLE_MODEL` 同形态规则
- `fdc + model`：优先 `FDC_MAX_TOTAL_AMOUNT_AND_MODEL`
- `device brand + firstProductRepayCnt + model`：优先同类设备品牌规则

### Step 5B: 生成决策 decision 配置 SQL

优先从相同形态的默认决策规则克隆：

- firstProductRepayCnt + model：`CURRENT_PRODUCT_FIRST_PERIOD_REPAY_CNT_AND_MODEL`
- 单特征最近逾期天数：`LAST_15_MAX_OVERDUE_DAY`
- 身份证黑名单：`IDCARDNO_IS_BLACKLIST`
- 设备品牌 + 包名 + model：`DEVICE_BRAND_1_PACKAGE_COVER_AND_MODEL`

默认目标表：

- 默认规则配置：`t_default_config_risk_rule_setting`
- 商户模型实际执行规则：`t_merchant_risk_rule_setting`

生成 SQL 时必须说明 SQL 是“默认配置”还是“商户模型执行配置”。如果用户只要求“入库 SQL”且上下文是决策规则，默认先生成 `t_default_config_risk_rule_setting` 的 SQL，并提醒需要同步到目标 `merchant_model_code`。

### Step 6: 设置 special_params_json 与 remarks

`special_params_json` 必须只表达代码实际放入 `min/max` 或多阈值字段的可配置参数，不能把已由代码固定过滤的前置条件重复写成可配置参数。

示例：

```sql
UPDATE t_credit_default_rule_setting
SET special_params_json='fdcL30dAvgLoanAmtCny,modelScore',
    special_params_json_remarks='fdc在前，model在后',
    update_date=NOW(),
    updater='codex'
WHERE rule_code='<RULE_CODE>';
```

决策规则示例：

```sql
UPDATE t_default_config_risk_rule_setting
SET special_params_json='firstProductRepayCnt,modelScore',
    special_params_json_remarks='本产品第一期还款次数在前，模型分在后',
    update_date=NOW(),
    updater='codex'
WHERE rule_code='<RULE_CODE>';
```

对组合规则，`remarks` 要清楚写出 `min/max` 对应关系；例如：

```sql
UPDATE t_default_config_risk_rule_setting
SET special_params_json='idCardBlacklist,last15MaxOverdueDay',
    special_params_json_remarks='身份证黑名单命中值在前，最近15天最大逾期天数在后',
    update_date=NOW(),
    updater='codex'
WHERE rule_code='<RULE_CODE>';
```

### Step 7: 数据校验

授信规则：

```sql
SELECT rule_code, rule_name, special_params_json, special_params_json_remarks, threshold_number, min, max, rule_sort, is_start, is_show
FROM t_credit_default_rule_setting
WHERE rule_code IN ('<RULE_CODE_1>','<RULE_CODE_2>');
```

决策规则：

```sql
SELECT rule_code, rule_name, special_params_json, special_params_json_remarks, threshold_number, min, max, rule_sort, rule_start, is_show
FROM t_default_config_risk_rule_setting
WHERE rule_code IN ('<RULE_CODE_1>','<RULE_CODE_2>');
```

## 常见问题排查

- SQL 里留了过多占位符：先查目标环境相似规则配置；只有模型名、业务阈值等数据库无法推断且用户未提供的值可以保留占位
- 用户指定参数名与 SQL 不一致：以用户指定为准，重新检查 `special_params_json` 和备注
- `INSERT 0 rows`：模板 `rule_code` 在目标库不存在
  - 用回退模板（见 `references/sql_templates.sql`）
- 命中但等级不变：检查 `decision_type`
  - `decision_type=2` 是调用不决策，不加等级
- 配置顺序错误：检查 `special_params_json` 与代码 `min/max` 是否一致
- 参数备注缺失或误导：检查 `special_params_json_remarks` 是否逐项解释参数含义和顺序
- 决策规则已进默认表但不执行：检查目标 `merchant_model_code` 下的 `t_merchant_risk_rule_setting`
- 模型分为空或异常：检查 `rule_name` 最后一段是否为模型名，以及 `model_url` 是否配置

## 交付检查清单

- [ ] ruleCode <= 64
- [ ] 已明确规则类型：credit 或 decision
- [ ] Service / Impl / switch 三处已同步
- [ ] 编译通过
- [ ] 若要求参考 prod/indo-prod，已用 `readonly-db-python` 只读查询目标环境模板配置和新 `ruleCode` 是否存在
- [ ] SQL 目标表正确：credit 用 `t_credit_default_rule_setting`，decision 用 `t_default_config_risk_rule_setting` 或目标商户表
- [ ] SQL 默认使用显式 `INSERT ... VALUES`，未在用户未要求时使用 `INSERT ... SELECT`
- [ ] SQL 中每个非业务字段都有来源：用户指定、目标环境模板查询结果，或明确列为待确认
- [ ] `special_params_json` 正确
- [ ] `special_params_json_remarks` 已填写并准确解释参数顺序
- [ ] 代码 `min/max` 与 `special_params_json` 顺序一致
- [ ] 抽样跑单验证通过
