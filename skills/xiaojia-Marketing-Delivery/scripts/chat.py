#!/usr/bin/env python3
import argparse
import json
from _common import get_default_timeout, submit_chat


def _load_form_data(form_data_json: str, form_data_file: str) -> dict:
    if form_data_json and form_data_file:
        raise SystemExit("--form-data-json 和 --form-data-file 只能二选一")
    if form_data_json:
        try:
            value = json.loads(form_data_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--form-data-json 不是合法 JSON: {exc}") from exc
    elif form_data_file:
        try:
            with open(form_data_file, "r", encoding="utf-8") as fh:
                value = json.load(fh)
        except OSError as exc:
            raise SystemExit(f"读取表单文件失败: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--form-data-file 不是合法 JSON: {exc}") from exc
    else:
        return {}

    if not isinstance(value, dict):
        raise SystemExit("form_data 必须是 JSON 对象")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit a task to the JustAI openapi chat endpoint.")
    parser.add_argument("--message", default="", help="User message to send.")
    parser.add_argument("--conversation-id", default="", help="Existing conversation id to continue.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=get_default_timeout(),
        help="HTTP timeout in seconds. Defaults to env/local config or 300.",
    )
    parser.add_argument(
        "--project-id",
        action="append",
        default=[],
        help="Optional project/folder id to scope RAG reference. Can be repeated.",
    )
    parser.add_argument(
        "--skill-id",
        action="append",
        default=[],
        help="Optional manual skill id to preload. Can be repeated.",
    )
    parser.add_argument("--form-id", default="", help="Optional form id returned by confirm_info.")
    parser.add_argument(
        "--form-data-json",
        default="",
        help="Optional JSON string used to update the form before continuing.",
    )
    parser.add_argument(
        "--form-data-file",
        default="",
        help="Optional JSON file path used to update the form before continuing.",
    )
    args = parser.parse_args()
    form_data = _load_form_data(args.form_data_json, args.form_data_file)
    if not args.message and not args.form_id:
        raise SystemExit("--message 和 --form-id 至少提供一个")

    result = submit_chat(
        message=args.message,
        conversation_id=args.conversation_id,
        timeout=args.timeout,
        project_ids=args.project_id,
        skill_ids=args.skill_id,
        form_id=args.form_id,
        form_data=form_data,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"accepted", "running"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
