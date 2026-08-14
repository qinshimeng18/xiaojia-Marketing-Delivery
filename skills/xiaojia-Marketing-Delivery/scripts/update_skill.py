#!/usr/bin/env python3
import argparse
import json

from _common import (
    get_default_timeout,
    openapi_get_skill,
    openapi_update_skill,
    parse_bool,
    resolve_prompt_content,
)


def build_payload(args) -> dict:
    payload = {"skill_id": args.skill_id}
    optional_fields = {
        "name": args.name,
        "description": args.description,
        "thumbnail": args.thumbnail,
        "category": args.category,
        "keywords": args.keywords,
        "market_status": args.market_status,
        "review_status": args.review_status,
        "load_strategy": args.load_strategy,
    }
    for key, value in optional_fields.items():
        if value not in (None, ""):
            payload[key] = value
    prompt_content = resolve_prompt_content(
        prompt_content=args.prompt_content,
        prompt_file=args.prompt_file,
        required=False,
    )
    if prompt_content.strip():
        payload["prompt_content"] = prompt_content
    if args.applicable_stage:
        payload["applicable_stages"] = args.applicable_stage
    if args.priority is not None:
        payload["priority"] = args.priority
    share_prompt_visible = parse_bool(args.share_prompt_visible, "--share-prompt-visible")
    if share_prompt_visible is not None:
        payload["share_prompt_visible"] = share_prompt_visible
    market_prompt_visible = parse_bool(args.market_prompt_visible, "--market-prompt-visible")
    if market_prompt_visible is not None:
        payload["market_prompt_visible"] = market_prompt_visible
    if len(payload) == 1:
        raise SystemExit("At least one field besides --skill-id is required.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Update an internal JustAI Skill through OpenAPI.")
    parser.add_argument("--skill-id", required=True, help="Skill ID to update.")
    parser.add_argument("--name", default="", help="Optional new skill name.")
    parser.add_argument("--description", default="", help="Optional new description.")
    parser.add_argument("--prompt-content", default="", help="Optional new prompt content.")
    parser.add_argument("--prompt-file", default="", help="Read new prompt content from a UTF-8 file.")
    parser.add_argument("--thumbnail", default="", help="Optional thumbnail URL.")
    parser.add_argument("--category", default="", help="Optional category.")
    parser.add_argument("--keywords", default="", help="Optional comma-separated keywords.")
    parser.add_argument("--market-status", default="", help="Optional market status: off/listed.")
    parser.add_argument("--review-status", default="", help="Optional review status for admin API keys.")
    parser.add_argument("--share-prompt-visible", default="", help="Optional true/false.")
    parser.add_argument("--market-prompt-visible", default="", help="Optional true/false.")
    parser.add_argument("--load-strategy", default="", help="Optional load strategy: always/on_demand/manual.")
    parser.add_argument(
        "--applicable-stage",
        action="append",
        default=[],
        help="Optional applicable stage. Can be repeated.",
    )
    parser.add_argument("--priority", type=int, default=None, help="Optional priority.")
    parser.add_argument("--verify", action="store_true", help="Fetch detail after update.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    result = openapi_update_skill(build_payload(args), timeout=args.timeout)
    if args.verify and result.get("status") == 0:
        result["verified_detail"] = openapi_get_skill(args.skill_id, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
