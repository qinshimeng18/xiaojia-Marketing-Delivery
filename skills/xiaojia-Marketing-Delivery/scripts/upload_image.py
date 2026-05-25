#!/usr/bin/env python3
import argparse
import json

from _common import build_image_upload_payload, get_default_timeout, openapi_upload_image


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a local image through JustAI OpenAPI.")
    parser.add_argument("--file", required=True, help="Local image path. Supports png, jpeg, and webp.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    result = openapi_upload_image(
        build_image_upload_payload(args.file),
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
