#!/usr/bin/env python3
import argparse
import json
import time
import uuid
from pathlib import Path

from _common import (
    build_image_upload_payload,
    get_default_timeout,
    openapi_generate_image,
    openapi_image_result,
    openapi_upload_image,
)


MODEL_CHOICES = {
    "image-flash": "google/gemini-3.1-flash-image-preview",
    "image-2": "apimart-gpt-image-2",
    "doubao-5.0": "doubao-seedream-5-0-260128",
}
DEFAULT_MODEL = "image-2"
MAX_REFERENCE_IMAGES = 14


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


def build_payload(args, image_urls: list[str] | None = None) -> dict:
    payload = {
        "prompt": resolve_prompt(args.prompt, args.prompt_file),
        "model": args.model,
        "pic_scale": args.pic_scale,
        "template_id": args.template_id,
        "req_key": args.req_key or MODEL_CHOICES[args.model],
        "max_wait_time": args.max_wait_time,
        "poll_interval": args.poll_interval,
        "wait_for_completion": False,
        "prompt_mode": "raw" if getattr(args, "raw_prompt", False) else "enhanced",
        "idempotency_key": (
            str(getattr(args, "idempotency_key", "") or "").strip()
            or uuid.uuid4().hex
        ),
    }
    if args.conversation_id:
        payload["conversation_id"] = args.conversation_id
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt
    resolved_image_urls = (
        image_urls if image_urls is not None else getattr(args, "image_url", [])
    )
    resolved_image_urls = [
        str(url or "").strip()
        for url in (resolved_image_urls or [])
        if str(url or "").strip()
    ]
    if len(resolved_image_urls) > MAX_REFERENCE_IMAGES:
        raise SystemExit(f"At most {MAX_REFERENCE_IMAGES} reference images are supported.")
    if resolved_image_urls:
        payload["image_urls"] = resolved_image_urls
    return payload


def resolve_reference_image_urls(args, timeout: float) -> list[str]:
    image_urls = [
        str(url or "").strip()
        for url in (args.image_url or [])
        if str(url or "").strip()
    ]
    for image_file in args.image_file or []:
        upload_result = openapi_upload_image(
            build_image_upload_payload(image_file),
            timeout=timeout,
        )
        image_url = str(upload_result.get("url") or "").strip()
        if upload_result.get("status") != "ok" or not image_url:
            raise SystemExit(
                upload_result.get("message") or "Failed to upload reference image."
            )
        image_urls.append(image_url)
    if len(image_urls) > MAX_REFERENCE_IMAGES:
        raise SystemExit(f"At most {MAX_REFERENCE_IMAGES} reference images are supported.")
    return image_urls


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
    parser.add_argument(
        "--image-url",
        action="append",
        default=[],
        help="Reference image URL on JustAI COS. Repeat for multiple reference images.",
    )
    parser.add_argument(
        "--image-file",
        action="append",
        default=[],
        help=(
            "Local png/jpeg/webp reference image. It is uploaded to COS "
            "automatically; repeat for multiple images."
        ),
    )
    parser.add_argument(
        "--raw-prompt",
        action="store_true",
        help="Send the prompt without the default AI image-prompt enhancement.",
    )
    parser.add_argument(
        "--idempotency-key",
        default="",
        help="Reuse the same key when retrying the same submission.",
    )
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

    request_timeout = min(max(args.timeout, 1), 20)
    upload_timeout = min(max(args.timeout, 1), 60)
    image_urls = resolve_reference_image_urls(args, timeout=upload_timeout)
    payload = build_payload(args, image_urls=image_urls)
    result = openapi_generate_image(payload, timeout=request_timeout)
    if not args.no_wait and result.get("status") == "ok":
        job_id = str(result.get("job_id") or "").strip()
        generation_status = str(result.get("generation_status") or "").lower()
        deadline = time.monotonic() + args.max_wait_time
        while job_id and generation_status not in {"completed", "failed"}:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(args.poll_interval, remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            result = openapi_image_result(
                job_id,
                timeout=max(min(request_timeout, remaining), 0.1),
            )
            if result.get("status") != "ok":
                break
            generation_status = str(result.get("generation_status") or "").lower()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    generation_status = str(result.get("generation_status") or "")
    ok_statuses = {"completed", "pending", "running"} if args.no_wait else {"completed"}
    return 0 if result.get("status") == "ok" and generation_status in ok_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
