#!/usr/bin/env python3
import argparse
import json

from _common import get_default_timeout, openapi_get_skill


def main() -> int:
    parser = argparse.ArgumentParser(description="Get internal JustAI Skill detail through OpenAPI.")
    parser.add_argument("--skill-id", required=True, help="Skill ID to fetch.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    result = openapi_get_skill(args.skill_id, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
