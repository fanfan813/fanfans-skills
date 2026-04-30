---
name: readonly-db-python
description: "当用户想要查询数据库数据、检查数据库或表、查看架构详情、检查数据库/会话参数或总结查询结果（特别是当用户提到 SQL、MySQL、PostgreSQL、表结构、数据库参数或要求“查找数据”时）使用此技能。此技能严格仅限只读：它只能执行安全的读取语句，如 SELECT、SHOW、DESCRIBE、DESC、EXPLAIN 和 information_schema 查询。严禁执行 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE、TRUNCATE、REPLACE、MERGE、GRANT、REVOKE、CALL 或任何其他写入、DDL/DCL 语句。如果用户要求修改，请生成 SQL 并解释其影响，但不要运行它。"
---

# Python 数据库只读查询

## 用途

当请求的产出严格为只读时，使用此技能进行数据库检查和查询分析：

- 查询业务数据
- 列出数据库、架构、表、列、索引和视图
- 检查架构元数据
- 检查数据库或会话参数
- 为用户总结查询结果
- 起草数据变更的 SQL（但不执行）

请勿将此技能用于迁移、数据修复、回填、批量导入或任何需要更改数据或架构的任务。

## 安全契约 (Safety Contract)

核心原则：仅限检查，严禁修改。

### 允许的类别：
- `SELECT ...`
- `SHOW ...`
- `DESCRIBE ...` / `DESC ...`
- `EXPLAIN ...`
- 针对 `information_schema` 或 `pg_catalog` 的只读元数据查询
- 引擎特定的参数读取（例如 `SHOW VARIABLES`, `SHOW STATUS`, `SELECT @@version`）

### 严禁的类别：
- 数据修改：`INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `MERGE`, `UPSERT`, `TRUNCATE`
- 架构/系统：`DROP`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`, `SET`, `USE`
- 执行控制：`CALL`, `DO`, 多条 SQL 语句（以 `;` 分隔）

### 关键安全规则：
1. **强制超时**：所有查询必须指定语句超时（例如 30s），以防止资源耗尽。
2. **禁止使用 CLI 工具**：严禁直接使用 `mysql`, `psql` 或其他 CLI 二进制文件。仅限使用 Python 驱动。
3. **禁止泄露凭据**：严禁在任何输出中打印 DSN、密码或原始连接字符串。

## 依赖项 (Dependencies)

请确保环境中可以使用以下 Python 库：
- `mysql-connector-python` 或 `PyMySQL` (用于 MySQL)
- `psycopg2-binary` (用于 PostgreSQL)
- `sqlalchemy` (可选，用于统一访问)
- `tabulate` (用于结果格式化)

## 首选工作流 (Preferred Workflow)

1. **发现连接源**：通过 `scripts/dbhub_sources.py` 读取 `dbhub.properties`。除非明确要求 `prod`，否则默认使用 `test` 环境。
2. **连接预检**：在执行长查询或复杂查询前验证连通性。
3. **引擎识别**：检查显式的 `engine` 字段以适配 SQL 语法（MySQL vs PostgreSQL）。
4. **安全验证**：在任何执行前，务必运行 `scripts/sql_guard.py`。
5. **智能查询**：
   - **默认 LIMIT**：如果未指定 limit，务必加上 `LIMIT 100`（执行聚合操作如 `COUNT(*)` 时除外）。
   - **列选择**：优先选择特定列，而非 `SELECT *`。
6. **执行**：通过带有超时参数的 `scripts/run_readonly_query.py` 运行。
7. **主动洞察**：如果查询较慢，使用 `EXPLAIN` 并提供只读的索引建议。

## 连接源处理

优先使用当前工作区根目录下的 `dbhub.properties`。

```bash
python scripts/dbhub_sources.py --path dbhub.properties
```

- 如果缺少 `dbhub.properties`，请报告缺失，不要进行递归目录扫描。
- 将 `prod` 视为高敏感度；如果上下文模糊，请与用户确认。

## 工具策略 (Tool Strategy)

为了安全和凭据隔离，强制使用 Python 执行。

- **运行时**：优先使用系统 Python 3 或 `pyenv`。确保 Python 3.8+ 可用。
- **执行方式**：通过 `python` 或 `python3` 运行脚本。

```bash
# 安全检查
python scripts/sql_guard.py --sql "SELECT ..."

# 执行示例
python scripts/run_readonly_query.py \
  --dbhub-path dbhub.properties \
  --source-id test \
  --sql "SELECT id, name FROM users LIMIT 10"
```

## 查询模式 (Query Patterns)

### 1. 结构发现 (Structure Discovery)
- **MySQL**: `DESCRIBE users;` 或 `SHOW CREATE TABLE users;`
- **PostgreSQL**: `SELECT * FROM information_schema.columns WHERE table_name = 'users';`

### 2. 复杂分析（只读）
```sql
-- 安全的复杂 JOIN 示例
SELECT u.name, COUNT(o.id) as order_count
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.status = 'active'
GROUP BY u.id
HAVING order_count > 5
LIMIT 20;
```

### 3. 性能检查
```sql
EXPLAIN ANALYZE -- PostgreSQL 
SELECT ...
```

## 结果总结 (Result Summarization)

- **结论先行**：例如 “找到 5 个缺失电子邮件地址的活跃用户。”
- **样本与摘要**：如果行数 > 20，显示前 5 行和最后 1 行，并总结其余部分。
- **可视化**：使用表格进行对齐。
- **中文总结**：结论必须使用简练的中文。

## 处理修改请求

如果用户要求进行写入操作：
1. 声明：“此 Skill 仅限只读操作，无法直接执行修改。”
2. 提供 SQL：`UPDATE users SET ...`
3. 警告：“执行前请务必在测试环境验证，并确保已备份数据。”

## Python 代码规范

- 符合 `PEP 8`。
- 任何辅助脚本必须包含类型注解（Type hints）和文档字符串（Docstrings）。
- 使用 `logging` 而非 `print` 进行内部状态追踪。
