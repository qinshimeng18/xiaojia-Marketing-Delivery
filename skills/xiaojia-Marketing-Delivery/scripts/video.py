#!/usr/bin/env python3
"""视频方案/批准/拒绝/结果；生成仍由既有小加 Agent 执行。"""
import argparse
import json
from urllib.error import HTTPError, URLError

from _common import build_request, get_api_key, get_default_timeout, open_json, submit_chat


def main():
    parser = argparse.ArgumentParser(description="小加视频生成：先方案，明确确认后付费生成")
    parser.add_argument("operation", choices=["plan", "result", "approve", "reject"])
    parser.add_argument("--message", default="")
    parser.add_argument("--conversation-id", default="")
    parser.add_argument("--action-id", default="")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--price-token", default="")
    parser.add_argument("--timeout", type=int, default=get_default_timeout())
    args = parser.parse_args()
    if args.operation == "plan":
        if not args.message.strip():
            parser.error("plan 需要 --message")
        payload = {"message": f"请生成视频方案，展示分镜和预计积分，等待确认后再生成视频。需求：{args.message}", "video_plan": True, "stream": False}
        if args.conversation_id:
            payload["conversation_id"] = args.conversation_id
        result = open_json(build_request("/openapi/agent/chat_stream", payload, get_api_key(timeout=args.timeout)), timeout=args.timeout)
    else:
        if not args.conversation_id:
            parser.error("需要 --conversation-id")
        payload = {"conversation_id": args.conversation_id}
        path = "/openapi/videos/result"
        if args.operation in {"approve", "reject"}:
            if not args.action_id:
                parser.error("需要 --action-id")
            action = {"op": f"{args.operation}_pending_action", "action_id": args.action_id}
            if args.operation == "approve":
                if not args.confirm or args.revision is None or args.revision < 1:
                    parser.error("付费生成需用户明确确认，提供 --revision N --confirm")
                action["revision"] = args.revision
                if args.price_token:
                    action["price_confirmation_token"] = args.price_token
            payload["pending_action"] = action
            payload["stream"] = False
            path = "/openapi/agent/chat_stream"
        request = build_request(path, payload, get_api_key(timeout=args.timeout))
        try:
            result = open_json(request, timeout=args.timeout)
        except HTTPError:
            raise
        except (TimeoutError, URLError, ConnectionError):
            if args.operation != "approve":
                raise
            result = {
                "status": "pending", "submission_status": "unknown",
                "conversation_id": args.conversation_id, "action_id": args.action_id,
                "message": "批准响应超时或连接中断，请查询视频结果，不要重复批准。",
            }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "pending":
        return 2
    return 1 if result.get("status") in {"error", "failed"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
