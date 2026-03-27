#!/usr/bin/env python3
import argparse
import json
import sys
from _common import get_default_timeout, poll_chat_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll JustAI openapi chat_result by conversation_id.")
    parser.add_argument("--conversation-id", required=True, help="Conversation id returned by chat_submit.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="Polling timeout in seconds. Defaults to env/local config or 300.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=2,
        help="Polling interval in seconds for chat_result. Defaults to 2.",
    )
    args = parser.parse_args()

    def on_progress(result: dict) -> None:
        status = str(result.get("status", "") or "")
        branch = str(result.get("branch", "") or "")
        content_type = str(result.get("content_type", "") or "")
        message = f"[chat_result] status={status}"
        if branch:
            message += f" branch={branch}"
        if content_type:
            message += f" content_type={content_type}"
        print(message, file=sys.stderr, flush=True)

    result = poll_chat_result(
        conversation_id=args.conversation_id,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        progress_callback=on_progress,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
