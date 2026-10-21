#!/usr/bin/env python3
"""Deterministic synthetic file/schema control; no model or private inputs."""

import json
from pathlib import Path


def main() -> int:
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic/dialogue.jsonl"
    records = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
    valid = sum(
        isinstance(record, dict)
        and record.get("synthetic") is True
        and all(isinstance(record.get(key), str) and record[key] for key in ("prompt", "response"))
        for record in records
    )
    print(json.dumps({"fixture_records": len(records), "valid_records": valid}))
    return 0 if records and valid == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
