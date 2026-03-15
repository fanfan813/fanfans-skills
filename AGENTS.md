## Cursor Cloud specific instructions

### 项目概述

`readonly-db-python` 是一个安全的只读数据库查询 Python CLI 工具，包含三个脚本：
- `scripts/sql_guard.py` — SQL 安全验证器
- `scripts/dbhub_sources.py` — 数据库连接配置解析器
- `scripts/run_readonly_query.py` — 只读查询执行引擎

详细使用方式见 `readonly-db-python/README.md` 和 `readonly-db-python/SKILL.md`。

### 数据库服务

端到端测试需要 MySQL 和 PostgreSQL。启动方式：

```bash
sudo mysqld --user=mysql --datadir=/var/lib/mysql &
sudo pg_ctlcluster 16 main start
```

测试数据库 `test_db` 已预配置（用户 `testuser` / 密码 `testpass`）。连接配置在 `readonly-db-python/dbhub.toml` 中，source-id 分别为 `test-mysql` 和 `test-pg`。

### 注意事项

- 实际代码使用 `pymysql`（非 README 中的 `mysql-connector-python`）和 `psycopg` v3（非 `psycopg2-binary`）。安装时请使用 `pip install pymysql psycopg`。
- `run_readonly_query.py` 需要从 `scripts/` 目录运行（因为它使用相对导入 `from dbhub_sources import ...`），或将 `scripts/` 加入 `PYTHONPATH`。
- Python 3.12+ 已自带 `tomllib`，无需额外安装 `tomli`，但安装了也无影响。

### 常用命令

```bash
# 代码检查
cd readonly-db-python && ruff check scripts/ && ruff format --check scripts/

# SQL 安全验证
python3 scripts/sql_guard.py --sql "SELECT 1" --format json

# 查看连接源
python3 scripts/dbhub_sources.py --path dbhub.toml

# 执行查询（需在 scripts/ 目录或设置 PYTHONPATH）
cd scripts && python3 run_readonly_query.py --dbhub-path ../dbhub.toml --source-id test-mysql --sql "SELECT * FROM users" --format pretty
```
