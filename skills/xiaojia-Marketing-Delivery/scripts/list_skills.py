#!/usr/bin/env python3
import argparse
import json

from _common import build_request, get_api_key, get_default_timeout, open_json, parse_bool


def normalize_enabled(value):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized == "all":
        return "all"
    return parse_bool(normalized, "--enabled")


def build_payload(args) -> dict:
    payload = {
        "source": args.source,
        "page": args.page,
        "page_size": args.page_size,
    }
    optional_fields = {
        "keyword": args.keyword,
        "category": args.category,
        "sort_by": args.sort_by,
    }
    for key, value in optional_fields.items():
        if value not in (None, ""):
            payload[key] = value
    enabled = normalize_enabled(args.enabled)
    if enabled is not None:
        payload["enabled"] = enabled
    is_featured = parse_bool(args.is_featured, "--is-featured")
    if is_featured is not None:
        payload["is_featured"] = is_featured
    if args.include_details:
        payload["include_details"] = True
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="List available JustAI skills for the current API key.")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "system", "personal", "shared", "market"],
        help="Optional source filter.",
    )
    parser.add_argument("--enabled", default="", help="Optional enabled filter: true, false, or all.")
    parser.add_argument("--keyword", default="", help="Optional keyword filter.")
    parser.add_argument("--category", default="", help="Optional category, such as note/article/ppt.")
    parser.add_argument("--sort-by", default="", choices=["", "hot", "latest"], help="Optional sort: hot/latest.")
    parser.add_argument("--page", type=int, default=1, help="Page number.")
    parser.add_argument("--page-size", type=int, default=20, help="Page size.")
    parser.add_argument("--include-details", action="store_true", help="Return detailed skill fields.")
    parser.add_argument("--is-featured", default="", help="Optional true/false featured filter.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    result = open_json(
        build_request("/openapi/skills/list", build_payload(args), get_api_key()),
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
