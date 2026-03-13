# readonly-db-python (只读数据库查询工具)

这是一个专为 AI 助手设计的安全、只读的数据库探测与查询工具。它允许在不冒任何数据修改风险的情况下，安全地进行数据探索、结构检查和性能分析。

## 核心特性

- **绝对只读安全**：严格执行安全契约，仅允许 `SELECT`, `SHOW`, `DESCRIBE` 和 `EXPLAIN` 等读操作。
- **多引擎支持**：兼容 MySQL 和 PostgreSQL 数据库。
- **统一配置管理**：利用 `dbhub.toml` 文件规范化管理多个数据库连接（DSN）。
- **安全优先**：强制执行查询超时控制，并采用 Python 原生驱动执行（避免风险较大的 Shell CLI 方式）。
- **主动洞察**：能够根据执行计划（Execution Plan）自动提供性能优化建议。

## 目录结构

```text
.
├── SKILL.md            # 核心技能定义与安全契约
├── dbhub.toml.example  # 数据库连接标识模板
└── scripts/            # Python 实现脚本
    ├── sql_guard.py           # SQL 安全验证器
    ├── dbhub_sources.py       # 配置文件解析器
    └── run_readonly_query.py  # 查询执行引擎
```

## 快速开始

1. **环境准备**：Python 3.8+
2. **安装依赖**：根据您的数据库类型安装对应的 Python 驱动：
   ```bash
   pip install mysql-connector-python psycopg2-binary
   ```
3. **配置数据库**：根据 `dbhub.toml.example` 创建 `dbhub.toml`：
   ```toml
   [[sources]]
   id = "test"
   dsn = "mysql://user:password@localhost:3306/my_db"
   ```

## 使用说明

当您指示 AI 助手“查询数据”、“检查表结构”或“分析数据库参数”时，AI 会自动调用此技能。

### 内部执行示例
```bash
python scripts/run_readonly_query.py \
  --dbhub-path dbhub.toml \
  --source-id test \
  --sql "SELECT * FROM users LIMIT 10"
```

## 许可说明
个人开发使用。
