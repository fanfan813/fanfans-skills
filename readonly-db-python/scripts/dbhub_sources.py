#!/usr/bin/env python3
"""Read and summarize dbhub.toml connection sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib


def redact_netloc(netloc: str) -> str:
    """Redact password information in a DSN netloc."""

    if "@" not in netloc:
        return netloc

    userinfo, hostinfo = netloc.rsplit("@", 1)
    if ":" not in userinfo:
        return f"{userinfo}@{hostinfo}"

    username, _password = userinfo.split(":", 1)
    return f"{username}:***@{hostinfo}"


def parse_dsn(dsn: str) -> dict[str, str]:
    """Parse a database DSN without relying on strict URL escaping."""

    if "://" not in dsn:
        return {}

    scheme, remainder = dsn.split("://", 1)

    if "/" in remainder:
        authority, database = remainder.split("/", 1)
    else:
        authority, database = remainder, ""

    if "@" in authority:
        userinfo, hostinfo = authority.rsplit("@", 1)
    else:
        userinfo, hostinfo = "", authority

    username = userinfo.split(":", 1)[0] if userinfo else ""

    if ":" in hostinfo:
        host, port = hostinfo.rsplit(":", 1)
    else:
        host, port = hostinfo, ""

    return {
        "scheme": scheme,
        "host": host,
        "port": port,
        "database": database,
        "username": username,
        "dsn_redacted": f"{scheme}://{redact_netloc(authority)}/{database}".rstrip("/"),
    }


def summarize_dsn(dsn: str) -> dict[str, str]:
    """Return a safe summary of a DSN."""

    return parse_dsn(dsn)


def load_sources(path: Path) -> list[dict[str, Any]]:
    """Load source definitions from dbhub.toml."""

    with path.open("rb") as file:
        data = tomllib.load(file)
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("`sources` must be a list.")
    return [source for source in sources if isinstance(source, dict)]


def build_output(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create a safe JSON summary for each source."""

    output: list[dict[str, Any]] = []
    for source in sources:
        dsn = str(source.get("dsn", ""))
        summary = summarize_dsn(dsn) if dsn else {}
        output.append(
            {
                "id": source.get("id", ""),
                "connection_timeout": source.get("connection_timeout"),
                **summary,
            }
        )
    return output


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(description="Inspect dbhub.toml sources.")
    parser.add_argument("--path", required=True, help="Path to dbhub.toml")
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
