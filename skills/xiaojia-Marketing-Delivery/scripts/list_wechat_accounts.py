#!/usr/bin/env python3
import argparse
import json

from _common import DEFAULT_REQUEST_TIMEOUT, openapi_wechat_bindings_list


def main() -> int:
    parser = argparse.ArgumentParser(description="List WeChat official accounts bound to Xiaojia.")
    parser.add_argument("--team-id", type=int, default=None, help="Optional Xiaojia team id.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT)
    args = parser.parse_args()

    result = openapi_wechat_bindings_list(team_id=args.team_id, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
