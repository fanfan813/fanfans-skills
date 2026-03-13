#!/usr/bin/env python3
"""Execute a validated read-only query from a dbhub.toml source."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dbhub_sources import load_sources, parse_dsn
from sql_guard import validate_sql


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="Run a read-only SQL query.")
    parser.add_argument("--dbhub-path", required=True, help="Path to dbhub.toml")
    parser.add_argument("--source-id", required=True, help="Source id in dbhub.toml")
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--sql", help="Single read-only SQL statement")
    query_group.add_argument("--describe", help="Describe a table or view name")
    parser.add_argument(
        "--schema",
        help="Optional schema name for --describe, mainly used by PostgreSQL",
    )
    parser.add_argument(
        "--format",
        choices=("json", "pretty"),
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=200,
        help="Fail if result row count exceeds this value",
    )
    return parser


def find_source(path: Path, source_id: str) -> dict[str, Any]:
    """Load and return the matching source config."""

    for source in load_sources(path):
        if str(source.get("id", "")) == source_id:
            return source
    raise ValueError(f"Source id not found: {source_id}")


def validate_inputs(sql: str, max_rows: int) -> str:
    """Validate user inputs and return normalized SQL."""

    if max_rows <= 0:
        raise ValueError("--max-rows must be positive.")

    result = validate_sql(sql)
    if not result.ok:
        raise ValueError(result.reason)
    return result.normalized_sql


def validate_identifier(name: str, arg_name: str) -> str:
    """Validate a simple SQL identifier."""

    if not name:
        raise ValueError(f"{arg_name} must not be empty.")
    if not all(char.isalnum() or char == "_" for char in name):
        raise ValueError(f"{arg_name} contains unsupported characters: {name}")
    return name


def build_describe_sql(
    source: dict[str, Any],
    describe_target: str,
    schema: str | None,
) -> str:
    """Build engine-specific SQL for table structure inspection."""

    dsn = str(source.get("dsn", ""))
    parsed_dsn = parse_full_dsn(dsn)
    scheme = parsed_dsn.get("scheme", "").lower()
    table_name = validate_identifier(describe_target, "--describe")

    if scheme in {"mysql", "mariadb"}:
        return f"DESCRIBE `{table_name}`"

    if scheme in {"postgres", "postgresql"}:
        schema_name = validate_identifier(schema or "public", "--schema")
        return (
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            f"WHERE table_schema = '{schema_name}' "
            f"AND table_name = '{table_name}' "
            "ORDER BY ordinal_position"
        )

    raise ValueError(f"Unsupported database scheme: {scheme or 'unknown'}")


def mysql_connect(parsed_dsn: dict[str, str], timeout_seconds: int) -> Any:
    """Create a MySQL connection using PyMySQL."""

    try:
        import pymysql
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyMySQL is required for MySQL sources but is not installed."
        ) from exc

    password = parsed_dsn.get("password", "")
    return pymysql.connect(
        host=parsed_dsn.get("host") or "localhost",
        port=int(parsed_dsn.get("port") or 3306),
        user=parsed_dsn.get("username") or None,
        password=password,
        database=parsed_dsn.get("database") or None,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=timeout_seconds,
        read_timeout=timeout_seconds,
        write_timeout=timeout_seconds,
        autocommit=True,
    )


def postgres_connect(parsed_dsn: dict[str, str], timeout_seconds: int) -> Any:
    """Create a PostgreSQL connection using psycopg."""

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "psycopg is required for PostgreSQL sources but is not installed."
        ) from exc

    conn = psycopg.connect(
        host=parsed_dsn.get("host") or "localhost",
        port=int(parsed_dsn.get("port") or 5432),
        user=parsed_dsn.get("username") or None,
        password=parsed_dsn.get("password") or None,
        dbname=parsed_dsn.get("database") or None,
        connect_timeout=timeout_seconds,
        autocommit=True,
        row_factory=dict_row,
    )
    conn.execute("SET default_transaction_read_only = on")
    return conn


def connect(source: dict[str, Any]) -> Any:
    """Create a connection from a dbhub source definition."""

    dsn = str(source.get("dsn", ""))
    parsed_dsn = parse_full_dsn(dsn)
    scheme = parsed_dsn.get("scheme", "").lower()
    timeout_seconds = int(source.get("connection_timeout") or 60)

    if scheme in {"mysql", "mariadb"}:
        return mysql_connect(parsed_dsn, timeout_seconds)
    if scheme in {"postgres", "postgresql"}:
        return postgres_connect(parsed_dsn, timeout_seconds)
    raise ValueError(f"Unsupported database scheme: {scheme or 'unknown'}")


def parse_full_dsn(dsn: str) -> dict[str, str]:
    """Parse DSN, including password, without printing credentials."""

    parsed = parse_dsn(dsn)
    if "://" not in dsn:
        raise ValueError("Invalid DSN format.")

    _scheme, remainder = dsn.split("://", 1)
    authority = remainder.split("/", 1)[0]
    if "@" in authority:
        userinfo, _hostinfo = authority.rsplit("@", 1)
        if ":" in userinfo:
            _username, password = userinfo.split(":", 1)
            parsed["password"] = password
    return parsed


def execute_query(
    connection: Any,
    sql: str,
    max_rows: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute SQL and return rows."""

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = list(cursor.fetchall())

    if len(rows) > max_rows:
        raise ValueError(
            f"Query returned {len(rows)} rows, exceeding --max-rows={max_rows}."
        )

    if not rows:
        return [], []

    if isinstance(rows[0], dict):
        columns = list(rows[0].keys())
        return columns, rows

    raise RuntimeError("Database driver must return dict-like rows.")


def render_pretty(columns: list[str], rows: list[dict[str, Any]]) -> str:
    """Render a small human-readable table."""

    if not rows:
        return "(0 rows)"

    widths = {column: len(column) for column in columns}
    for row in rows:
        for column in columns:
            widths[column] = max(widths[column], len(str(row.get(column, ""))))

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    separator = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(str(row.get(column, "")).ljust(widths[column]) for column in columns)
        for row in rows
    ]
    return "\n".join([header, separator, *body, f"({len(rows)} rows)"])


def main() -> int:
    """CLI entry point."""

    args = build_parser().parse_args()
    dbhub_path = Path(args.dbhub_path)

    try:
        source = find_source(dbhub_path, args.source_id)
        raw_sql = args.sql or build_describe_sql(source, args.describe, args.schema)
        normalized_sql = validate_inputs(raw_sql, args.max_rows)
        connection = connect(source)
        try:
            columns, rows = execute_query(connection, normalized_sql, args.max_rows)
        finally:
            connection.close()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    payload = {
        "ok": True,
        "source_id": args.source_id,
        "sql": normalized_sql,
        "row_count": len(rows),
        "columns": columns,
        "rows": rows,
    }

    if args.format == "pretty":
        print(render_pretty(columns, rows))
    else:
        print(json.dumps(payload, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
