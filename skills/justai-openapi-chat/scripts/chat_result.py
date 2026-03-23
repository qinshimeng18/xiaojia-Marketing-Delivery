#!/usr/bin/env python3
import argparse
import json
import os
from _common import DEFAULT_TIMEOUT, poll_chat_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll JustAI openapi chat_result by conversation_id.")
    parser.add_argument("--conversation-id", required=True, help="Conversation id returned by chat_submit.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("JUSTAI_OPENAPI_TIMEOUT", DEFAULT_TIMEOUT)),
        help="Polling timeout in seconds. Defaults to JUSTAI_OPENAPI_TIMEOUT or 300.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=2,
        help="Polling interval in seconds for chat_result. Defaults to 2.",
    )
    args = parser.parse_args()

    result = poll_chat_result(
        conversation_id=args.conversation_id,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
