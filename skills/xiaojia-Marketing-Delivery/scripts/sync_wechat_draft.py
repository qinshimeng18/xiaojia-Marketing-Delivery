#!/usr/bin/env python3
import argparse
import json
import sys
import time

from _common import (
    DEFAULT_REQUEST_TIMEOUT,
    get_chat_result,
    get_default_timeout,
    openapi_wechat_draft_status,
    openapi_wechat_draft_sync,
)


def _result_components(result: dict) -> list[dict]:
    current = result.get("result")
    for _ in range(3):
        if not isinstance(current, dict):
            break
        components = current.get("components")
        if isinstance(components, list):
            return [item for item in components if isinstance(item, dict)]
        current = current.get("result")
    return []


def _image_urls(data: dict) -> list[str]:
    values = data.get("images") or data.get("image_urls") or []
    if not isinstance(values, list):
        return []
    urls = []
    for item in values:
        url = item.get("url") if isinstance(item, dict) else item
        normalized = str(url or "").strip()
        if normalized and normalized not in urls:
            urls.append(normalized)
    return urls


def build_draft_payload(
    result: dict,
    *,
    component_index: int = 1,
    authorizer_appid: str = "",
    team_id: int | None = None,
) -> dict:
    components = []
    for item in _result_components(result):
        data = item.get("data")
        if item.get("type") == "note":
            components.append(item)
            continue
        if isinstance(data, dict) and data.get("title") and (
            data.get("content") or data.get("content_html")
        ):
            components.append(item)
    if not components:
        raise ValueError("当前会话没有可同步的文章结果")
    if component_index <= 0 or component_index > len(components):
        raise ValueError(f"component_index 超出范围，当前共有 {len(components)} 篇文章")

    data = components[component_index - 1].get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("文章组件格式不正确")
    images = _image_urls(data)
    cover_image = str(data.get("cover_image") or "").strip() or (images[0] if images else "")
    payload = {
        "title": str(data.get("title") or "").strip(),
        "content": str(data.get("content") or "").strip(),
        "content_html": str(data.get("content_html") or "").strip(),
        "cover_image": cover_image,
        "image_urls": images,
        "conversation_id": str(result.get("conversation_id") or "").strip(),
    }
    if authorizer_appid:
        payload["authorizer_appid"] = authorizer_appid
    if team_id:
        payload["team_id"] = team_id
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync a Xiaojia article to WeChat draft box.")
    parser.add_argument("--conversation-id", required=True)
    parser.add_argument("--component-index", type=int, default=1, help="1-based article index.")
    parser.add_argument("--authorizer-appid", default="")
    parser.add_argument("--team-id", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=get_default_timeout())
    parser.add_argument("--poll-interval", type=int, default=3)
    args = parser.parse_args()

    result = get_chat_result(args.conversation_id, timeout=DEFAULT_REQUEST_TIMEOUT)
    if result.get("status") != "completed":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    try:
        payload = build_draft_payload(
            result,
            component_index=args.component_index,
            authorizer_appid=args.authorizer_appid,
            team_id=args.team_id,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    submitted = openapi_wechat_draft_sync(payload, timeout=DEFAULT_REQUEST_TIMEOUT)
    if submitted.get("status") != "ok":
        print(json.dumps(submitted, ensure_ascii=False, indent=2))
        return 1

    job_id = submitted.get("job_id")
    started_at = time.time()
    current = submitted
    while time.time() - started_at < args.timeout:
        current = openapi_wechat_draft_status(job_id, timeout=DEFAULT_REQUEST_TIMEOUT)
        if current.get("status") != "ok":
            print(json.dumps(current, ensure_ascii=False, indent=2))
            return 1
        sync_status = current.get("sync_status")
        print(f"[wechat_draft] status={sync_status}", file=sys.stderr, flush=True)
        if sync_status == "done":
            print(json.dumps(current, ensure_ascii=False, indent=2))
            return 0
        if sync_status in {"failed", "unknown"}:
            print(json.dumps(current, ensure_ascii=False, indent=2))
            return 1
        time.sleep(max(args.poll_interval, 1))

    current["message"] = "Draft sync is still running. Query the job again later."
    print(json.dumps(current, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
