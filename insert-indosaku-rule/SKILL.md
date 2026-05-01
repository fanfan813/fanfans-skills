---
name: insert-indosaku-rule
description: End-to-end workflow for Indosaku rule delivery from Java development to DB insertion. Use when adding or modifying credit/decision rules, enforcing ruleCode constraints, registering dispatch logic, and generating INSERT/UPDATE SQL for rule config tables (especially t_credit_default_rule_setting).
---

# Insert Indosaku Rule

将规则从“开发完成”推进到“配置可执行”的标准流程。

## 适用范围

- 新增或修改 `ruleCode`
- 需要同时处理代码与配置表
- 需要生成 `t_credit_default_rule_setting` 的插入 SQL

## 关键约束

- `ruleCode` 长度必须 `<= 64`
- `ruleCode` 必须与 `CreditRuleServiceImpl` 方法名一致（当前项目按 `switch-case` 分发）
- `special_params_json` 使用逗号分隔格式，例如：`fdcL30dAvgLoanAmtCny,modelScore`
- 当规则逻辑要求“参数顺序”时，代码中的 `min/max` 与 `special_params_json` 顺序必须一致

## 开发到落库 SOP

### Step 1: 设计 ruleCode 和参数顺序

1. 确认 `ruleCode` 语义清晰且长度 <= 64
2. 确认可配置参数顺序，例如：
   - `fdcL30dAvgLoanAmtCny,modelScore`
   - 对应代码：`min=fdcL30dAvgLoanAmtCny`，`max=modelScore`

### Step 2: 代码开发（授信）

必须同时修改：

1. `CreditRuleService` 增加方法签名
2. `CreditRuleServiceImpl` 增加规则方法与私有构建逻辑
3. `CreditCheckRiskServiceImpl` 的 `switch (ruleCode)` 增加 case 分发

检查命令：

```bash
rg -n "<RULE_CODE>" src/main/java/com/yuctime/service/credit/CreditRuleService.java src/main/java/com/yuctime/service/impl/credit/CreditRuleServiceImpl.java src/main/java/com/yuctime/service/impl/credit/CreditCheckRiskServiceImpl.java
```

### Step 3: 编译验证

```bash
mvn -q -DskipTests compile
```

### Step 4: 生成 credit 配置 SQL

优先使用模板克隆：

- 第一类（firstPeriodRepayCnt + model）模板：`CURRENT_PRODUCT_FIRST_PERIOD_REPAY_CNT_AND_MODEL`
- 第二类（fdc + model）模板：优先 `FDC_MAX_TOTAL_AMOUNT_AND_MODEL`，不存在则回退 `CURRENT_PRODUCT_FIRST_PERIOD_REPAY_CNT_AND_MODEL`

参考模板：`references/sql_templates.sql`

### Step 5: 设置 special_params_json

示例：

```sql
UPDATE t_credit_default_rule_setting
SET special_params_json='fdcL30dAvgLoanAmtCny,modelScore',
    special_params_json_remarks='fdc在前，model在后',
    update_date=NOW(),
    updater='codex'
WHERE rule_code='<RULE_CODE>';
```

### Step 6: 数据校验

```sql
SELECT rule_code, rule_name, special_params_json, threshold_number, min, max, rule_sort, is_start, is_show
FROM t_credit_default_rule_setting
WHERE rule_code IN ('<RULE_CODE_1>','<RULE_CODE_2>');
```

## 常见问题排查

- `INSERT 0 rows`：模板 `rule_code` 在目标库不存在
  - 用回退模板（见 `references/sql_templates.sql`）
- 命中但等级不变：检查 `decision_type`
  - `decision_type=2` 是调用不决策，不加等级
- 配置顺序错误：检查 `special_params_json` 与代码 `min/max` 是否一致

## 交付检查清单

- [ ] ruleCode <= 64
- [ ] Service / Impl / switch 三处已同步
- [ ] 编译通过
- [ ] SQL 执行成功
- [ ] `special_params_json` 正确
- [ ] 抽样跑单验证通过
