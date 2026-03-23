#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.error
import urllib.request


DEFAULT_TIMEOUT = 300


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def get_base_url() -> str:
    return require_env("JUSTAI_OPENAPI_BASE_URL").rstrip("/")


def get_api_key() -> str:
    return require_env("JUSTAI_OPENAPI_API_KEY")


def build_request(path: str, payload: dict, api_key: str) -> urllib.request.Request:
    return urllib.request.Request(
        url=f"{get_base_url()}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


def open_json(request: urllib.request.Request, timeout: int) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(error_body or str(exc), file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(body, file=sys.stderr)
        raise SystemExit(1)


def submit_chat(
    message: str,
    conversation_id: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    project_ids: list[str] | None = None,
    skill_ids: list[str] | None = None,
) -> dict:
    api_key = get_api_key()
    submit_payload = {"message": message}
    if conversation_id:
        submit_payload["conversation_id"] = conversation_id
    if project_ids:
        submit_payload["project_id"] = [item for item in project_ids if item]
    if skill_ids:
        submit_payload["skill_id"] = [item for item in skill_ids if item]

    submit_request = build_request("/openapi/agent/chat_submit", submit_payload, api_key)
    return open_json(submit_request, timeout=timeout)


def get_chat_result(
    conversation_id: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    api_key = get_api_key()
    result_request = build_request(
        "/openapi/agent/chat_result",
        {"conversation_id": conversation_id},
        api_key,
    )
    return open_json(result_request, timeout=timeout)


def poll_chat_result(
    conversation_id: str,
    timeout: int = DEFAULT_TIMEOUT,
    poll_interval: int = 2,
) -> dict:
    start_time = time.time()
    while True:
        result = get_chat_result(conversation_id=conversation_id, timeout=timeout)
        status = result.get("status", "")
        if status in {"completed", "failed"}:
            return result
        if time.time() - start_time >= timeout:
            result.setdefault("message", "Polling timed out before task completed.")
            return result
        time.sleep(max(poll_interval, 1))
