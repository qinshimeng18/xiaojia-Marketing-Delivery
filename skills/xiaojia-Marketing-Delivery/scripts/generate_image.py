#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from _common import get_default_timeout, openapi_generate_image


MODEL_CHOICES = {
    "image-flash": "google/gemini-3.1-flash-image-preview",
    "image-2": "apimart-gpt-image-2",
    "doubao-5.0": "doubao-seedream-5-0-260128",
}
DEFAULT_MODEL = "image-2"


def resolve_prompt(prompt: str = "", prompt_file: str = "") -> str:
    if prompt and prompt_file:
        raise SystemExit("--prompt and --prompt-file cannot be used together.")
    if prompt_file:
        try:
            prompt = Path(prompt_file).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"Failed to read --prompt-file: {exc}") from exc
    prompt = str(prompt or "").strip()
    if not prompt:
        raise SystemExit("--prompt or --prompt-file is required.")
    return prompt


def build_payload(args) -> dict:
    payload = {
        "prompt": resolve_prompt(args.prompt, args.prompt_file),
        "model": args.model,
        "pic_scale": args.pic_scale,
        "template_id": args.template_id,
        "req_key": args.req_key or MODEL_CHOICES[args.model],
        "max_wait_time": args.max_wait_time,
        "poll_interval": args.poll_interval,
        "wait_for_completion": not args.no_wait,
    }
    if args.conversation_id:
        payload["conversation_id"] = args.conversation_id
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an image through the paid Xiaojia OpenAPI skill.")
    parser.add_argument("--prompt", default="", help="Image prompt.")
    parser.add_argument("--prompt-file", default="", help="Read image prompt from a UTF-8 file.")
    parser.add_argument("--pic-scale", default="3:4", help="Image ratio, for example 3:4, 1:1, 4:3.")
    parser.add_argument("--template-id", type=int, default=1, help="Image template id. Defaults to 1.")
    parser.add_argument(
        "--model",
        choices=sorted(MODEL_CHOICES),
        default=DEFAULT_MODEL,
        help="Friendly model choice. Defaults to image-2.",
    )
    parser.add_argument("--req-key", default="", help="Raw image model key. Overrides --model when provided.")
    parser.add_argument("--conversation-id", default="", help="Optional image-generator conversation id.")
    parser.add_argument("--negative-prompt", default="", help="Optional negative prompt.")
    parser.add_argument("--max-wait-time", type=int, default=300, help="Generation wait time in seconds.")
    parser.add_argument("--poll-interval", type=int, default=5, help="Polling interval in seconds.")
    parser.add_argument("--no-wait", action="store_true", help="Submit only and return job_id immediately.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    args = parser.parse_args()

    payload = build_payload(args)
    timeout = args.timeout
    if not args.no_wait:
        timeout = max(timeout, args.max_wait_time + 30)

    result = openapi_generate_image(payload, timeout=timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    generation_status = str(result.get("generation_status") or "")
    ok_statuses = {"completed", "pending"}
    return 0 if result.get("status") == "ok" and generation_status in ok_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
