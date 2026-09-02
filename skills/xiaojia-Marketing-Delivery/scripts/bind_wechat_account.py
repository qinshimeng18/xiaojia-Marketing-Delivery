#!/usr/bin/env python3
import argparse
import json
import sys
import time
import webbrowser

from _common import (
    DEFAULT_REQUEST_TIMEOUT,
    get_default_timeout,
    openapi_wechat_binding_prepare,
    openapi_wechat_binding_status,
    openapi_wechat_bindings_list,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind a WeChat official account to Xiaojia.")
    parser.add_argument("--team-id", type=int, default=None, help="Optional Xiaojia team id.")
    parser.add_argument("--timeout", type=int, default=get_default_timeout())
    parser.add_argument("--poll-interval", type=int, default=3)
    parser.add_argument("--no-open-browser", action="store_true")
    args = parser.parse_args()

    prepared = openapi_wechat_binding_prepare(
        team_id=args.team_id,
        timeout=DEFAULT_REQUEST_TIMEOUT,
    )
    if prepared.get("status") != "ok":
        print(json.dumps(prepared, ensure_ascii=False, indent=2))
        return 1

    authorize_url = str(prepared.get("authorize_url") or "")
    bind_token = str(prepared.get("bind_token") or "")
    print(f"请在 15 分钟内打开并完成公众号授权：\n{authorize_url}", file=sys.stderr, flush=True)
    if authorize_url and not args.no_open_browser:
        webbrowser.open(authorize_url)

    started_at = time.time()
    while time.time() - started_at < args.timeout:
        status = openapi_wechat_binding_status(bind_token, timeout=DEFAULT_REQUEST_TIMEOUT)
        binding_status = status.get("binding_status")
        if status.get("status") != "ok" or binding_status == "expired":
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return 1
        if binding_status == "completed":
            accounts = openapi_wechat_bindings_list(
                team_id=args.team_id,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )
            print(json.dumps(accounts, ensure_ascii=False, indent=2))
            return 0 if accounts.get("status") == "ok" else 1
        time.sleep(max(args.poll_interval, 1))

    prepared["binding_status"] = "pending"
    prepared["message"] = (
        "Binding is still pending. If the administrator already completed authorization, "
        "check the failure message on the WeChat authorization page and start a new binding attempt."
    )
    print(json.dumps(prepared, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
