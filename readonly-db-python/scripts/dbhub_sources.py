#!/usr/bin/env python3
"""Read and summarize dbhub.properties connection sources."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {"engine", "host", "port", "database", "username"}


def parse_properties(path: Path) -> dict[str, str]:
    """Load a simple Java properties file."""

    properties: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith(("#", "!")):
                continue

            separator_index = -1
            for separator in ("=", ":"):
                index = line.find(separator)
                if index != -1:
                    separator_index = index
                    break

            if separator_index == -1:
                raise ValueError(f"Invalid properties line: {raw_line.rstrip()}")

            key = line[:separator_index].strip()
            value = line[separator_index + 1 :].strip()
            if not key:
                raise ValueError(f"Property key must not be empty: {raw_line.rstrip()}")
            properties[key] = value
    return properties


def normalize_source(source_id: str, fields: dict[str, str]) -> dict[str, Any]:
    """Normalize source fields into a validated dict."""

    missing_fields = sorted(field for field in REQUIRED_FIELDS if not fields.get(field))
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Source `{source_id}` missing required fields: {missing}")

    normalized: dict[str, Any] = {
        "id": source_id,
        "engine": fields["engine"],
        "host": fields["host"],
        "port": fields["port"],
        "database": fields["database"],
        "username": fields["username"],
        "password_env": fields.get("password_env", ""),
        "connection_timeout": int(fields.get("connection_timeout", "60")),
        "readonly": fields.get("readonly", "true").lower() == "true",
    }

    password = fields.get("password")
    if password:
        normalized["password"] = password

    return normalized


def load_sources(path: Path) -> list[dict[str, Any]]:
    """Load source definitions from dbhub.properties."""

    properties = parse_properties(path)
    grouped: dict[str, dict[str, str]] = {}

    for key, value in properties.items():
        parts = key.split(".")
        if len(parts) != 3 or parts[0] != "db":
            raise ValueError(
                "Property key must match `db.<source_id>.<field>`: "
                f"{key}"
            )

        _, source_id, field = parts
        grouped.setdefault(source_id, {})[field] = value

    return [normalize_source(source_id, fields) for source_id, fields in grouped.items()]


def resolve_password(source: dict[str, Any]) -> str:
    """Resolve password from inline config or referenced environment variable."""

    inline_password = str(source.get("password", ""))
    if inline_password:
        return inline_password

    password_env = str(source.get("password_env", ""))
    if not password_env:
        return ""

    value = os.getenv(password_env, "")
    if not value:
        raise ValueError(f"Environment variable not found or empty: {password_env}")
    return value


def build_output(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a safe JSON summary for each source."""

    output: list[dict[str, Any]] = []
    for source in sources:
        output.append(
            {
                "id": source.get("id", ""),
                "engine": source.get("engine", ""),
                "host": source.get("host", ""),
                "port": source.get("port", ""),
                "database": source.get("database", ""),
                "username": source.get("username", ""),
                "password_env": source.get("password_env", ""),
                "connection_timeout": source.get("connection_timeout"),
                "readonly": source.get("readonly", True),
            }
        )
    return output


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="Inspect dbhub.properties sources.")
    parser.add_argument("--path", required=True, help="Path to dbhub.properties")
    return parser


def main() -> int:
    """CLI entry point."""

    args = build_parser().parse_args()
    path = Path(args.path)
    sources = load_sources(path)
    print(json.dumps({"sources": build_output(sources)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
