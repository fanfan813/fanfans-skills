#!/usr/bin/env python3
"""Validate that a SQL statement is strictly read-only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass


FORBIDDEN_KEYWORDS = {
    "alter",
    "analyze",
    "attach",
    "call",
    "comment",
    "commit",
    "copy",
    "create",
    "deallocate",
    "delete",
    "detach",
    "do",
    "drop",
    "execute",
    "grant",
    "insert",
    "load",
    "lock",
    "merge",
    "prepare",
    "put",
    "refresh",
    "replace",
    "reset",
    "revoke",
    "rollback",
    "set",
    "truncate",
    "unload",
    "update",
    "upsert",
    "use",
    "vacuum",
}

ALLOWED_START = (
    "select",
    "show",
    "describe",
    "desc",
    "explain",
    "with",
)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of SQL validation."""

    ok: bool
    reason: str
    normalized_sql: str


def strip_sql_comments(sql: str) -> str:
    """Remove line and block comments from SQL text."""

    without_line = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", without_line, flags=re.DOTALL)


def normalize_sql(sql: str) -> str:
    """Normalize SQL for validation."""

    collapsed = re.sub(r"\s+", " ", strip_sql_comments(sql)).strip()
    return collapsed.rstrip(";").strip()


def first_keyword(sql: str) -> str:
    """Return the first SQL keyword."""

    match = re.match(r"([a-zA-Z_]+)", sql)
    return match.group(1).lower() if match else ""


def has_multiple_statements(original_sql: str) -> bool:
    """Reject obvious multi-statement SQL."""

    parts = [part.strip() for part in original_sql.split(";") if part.strip()]
    return len(parts) > 1


def validate_sql(sql: str) -> ValidationResult:
    """Validate that SQL is read-only."""

    if not sql or not sql.strip():
        return ValidationResult(False, "SQL is empty.", "")

    if has_multiple_statements(sql):
        return ValidationResult(False, "Multiple SQL statements are not allowed.", "")

    normalized = normalize_sql(sql)
    keyword = first_keyword(normalized)

    if keyword not in ALLOWED_START:
        return ValidationResult(
            False,
            f"Statement must start with one of {ALLOWED_START}, got {keyword or 'unknown'}.",
            normalized,
        )

    lower_sql = f" {normalized.lower()} "
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lower_sql):
            return ValidationResult(
                False,
                f"Forbidden keyword detected: {keyword}.",
                normalized,
            )

    return ValidationResult(True, "SQL is read-only.", normalized)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="Validate read-only SQL.")
    parser.add_argument("--sql", required=True, help="SQL text to validate")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="json",
        help="Output format",
    )
    return parser


def main() -> int:
    """CLI entry point."""

    args = build_parser().parse_args()
    result = validate_sql(args.sql)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "reason": result.reason,
                    "normalized_sql": result.normalized_sql,
                },
                ensure_ascii=False,
            )
        )
    else:
        status = "OK" if result.ok else "BLOCKED"
        print(f"{status}: {result.reason}")
        if result.normalized_sql:
            print(result.normalized_sql)

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
