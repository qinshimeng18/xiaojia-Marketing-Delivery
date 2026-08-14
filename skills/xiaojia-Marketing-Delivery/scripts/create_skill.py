#!/usr/bin/env python3
import argparse
import json

from _common import (
    build_skill_thumbnail_upload_payload,
    get_default_timeout,
    openapi_create_skill,
    openapi_get_skill,
    parse_bool,
    resolve_prompt_content,
)


def build_payload(args) -> dict:
    payload = {
        "name": args.name,
        "description": args.description,
        "prompt_content": resolve_prompt_content(
            prompt_content=args.prompt_content,
            prompt_file=args.prompt_file,
            required=True,
        ),
    }
    optional_fields = {
        "thumbnail": args.thumbnail,
        "category": args.category,
        "keywords": args.keywords,
        "market_status": args.market_status,
        "load_strategy": args.load_strategy,
    }
    for key, value in optional_fields.items():
        if value not in (None, ""):
            payload[key] = value
    thumbnail_file = str(getattr(args, "thumbnail_file", "") or "").strip()
    if thumbnail_file:
        thumbnail_payload = build_skill_thumbnail_upload_payload(thumbnail_file)
        payload["thumbnail_file_name"] = thumbnail_payload["file_name"]
        payload["thumbnail_file_data"] = thumbnail_payload["file_data"]
        payload["thumbnail_content_type"] = thumbnail_payload["content_type"]
    if args.applicable_stage:
        payload["applicable_stages"] = args.applicable_stage
    if args.priority is not None:
        payload["priority"] = args.priority
    enabled = parse_bool(args.enabled, "--enabled")
    if enabled is not None:
        payload["enabled"] = enabled
    market_prompt_visible = parse_bool(args.market_prompt_visible, "--market-prompt-visible")
    if market_prompt_visible is not None:
        payload["market_prompt_visible"] = market_prompt_visible
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an internal JustAI Skill through OpenAPI.")
    parser.add_argument("--name", required=True, help="Skill name.")
    parser.add_argument("--description", required=True, help="Skill description.")
    parser.add_argument("--prompt-content", default="", help="Skill prompt content.")
    parser.add_argument("--prompt-file", default="", help="Read skill prompt content from a UTF-8 file.")
    thumbnail_group = parser.add_mutually_exclusive_group()
    thumbnail_group.add_argument("--thumbnail", default="", help="Optional thumbnail URL.")
    thumbnail_group.add_argument("--thumbnail-file", default="", help="Attach a local png/webp thumbnail file to create.")
    parser.add_argument("--category", default="", help="Optional category, such as note/article/ppt.")
    parser.add_argument("--keywords", default="", help="Optional comma-separated keywords.")
    parser.add_argument("--market-status", default="", help="Optional market status: off/listed.")
    parser.add_argument("--market-prompt-visible", default="", help="Optional true/false.")
    parser.add_argument("--load-strategy", default="", help="Optional load strategy: always/on_demand/manual.")
    parser.add_argument(
        "--applicable-stage",
        action="append",
        default=[],
        help="Optional applicable stage. Can be repeated.",
    )
    parser.add_argument("--priority", type=int, default=None, help="Optional priority.")
    parser.add_argument("--enabled", default="", help="Optional true/false.")
    parser.add_argument("--verify", action="store_true", help="Fetch detail after create.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    result = openapi_create_skill(build_payload(args), timeout=args.timeout)
    if args.verify and result.get("status") == 0:
        skill_id = ((result.get("data") or {}).get("skill_id") or "").strip()
        if skill_id:
            result["verified_detail"] = openapi_get_skill(skill_id, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
