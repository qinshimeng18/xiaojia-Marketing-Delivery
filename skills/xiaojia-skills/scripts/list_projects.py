#!/usr/bin/env python3
import argparse
import json

from _common import build_request, get_api_key, get_default_timeout, open_json


def main() -> int:
    parser = argparse.ArgumentParser(description="List available JustAI projects/folders for the current API key.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    result = open_json(
        build_request("/openapi/projects/list", {}, get_api_key()),
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
