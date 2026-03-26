#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request


DEFAULT_TIMEOUT = 300
DEFAULT_BASE_URL = "https://justailab.com"
DEFAULT_LOGIN_POLL_INTERVAL = 2
MARKETING_PAYMENT_URL = "https://dev.justailab.xyz/marketing"
API_KEY_ENV_NAME = "JUSTAI_OPENAPI_API_KEY"
API_KEY_EXPORT_RE = re.compile(
    rf'^\s*export\s+{API_KEY_ENV_NAME}=(?P<quote>["\']?)(?P<value>.*?)(?P=quote)\s*$'
)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def get_base_url() -> str:
    return os.environ.get("JUSTAI_OPENAPI_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")


def _get_shell_name(shell_env: str | None = None) -> str:
    shell_value = (shell_env or os.environ.get("SHELL", "")).strip()
    return Path(shell_value).name


def _get_home(home: Path | None = None) -> Path:
    return home if home is not None else Path.home()


def _get_shell_rc_candidates(shell_env: str | None = None, home: Path | None = None) -> list[Path]:
    shell_name = _get_shell_name(shell_env)
    home_dir = _get_home(home)

    if shell_name == "zsh":
        filenames = [".zshrc", ".bashrc", ".profile"]
    elif shell_name in {"bash", "sh"}:
        filenames = [".bashrc", ".profile", ".zshrc"]
    else:
        filenames = [".profile", ".zshrc", ".bashrc"]

    return [home_dir / filename for filename in filenames]


def _get_primary_shell_rc_path(shell_env: str | None = None, home: Path | None = None) -> Path:
    return _get_shell_rc_candidates(shell_env=shell_env, home=home)[0]


def _read_api_key_from_shell_rc(shell_env: str | None = None, home: Path | None = None) -> str:
    for rc_path in _get_shell_rc_candidates(shell_env=shell_env, home=home):
        if not rc_path.exists():
            continue
        lines = rc_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            match = API_KEY_EXPORT_RE.match(line)
            if match:
                return match.group("value").strip()
    return ""


def persist_api_key(api_key: str, shell_env: str | None = None, home: Path | None = None) -> Path:
    rc_path = _get_primary_shell_rc_path(shell_env=shell_env, home=home)
    escaped_api_key = api_key.replace("\\", "\\\\").replace('"', '\\"')
    export_line = f'export {API_KEY_ENV_NAME}="{escaped_api_key}"\n'

    if rc_path.exists():
        lines = rc_path.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = []

    replaced = False
    updated_lines = []
    for line in lines:
        if API_KEY_EXPORT_RE.match(line):
            if not replaced:
                updated_lines.append(export_line)
                replaced = True
            continue
        updated_lines.append(line)

    if not replaced:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines[-1] = f"{updated_lines[-1]}\n"
        updated_lines.append(export_line)

    rc_path.write_text("".join(updated_lines), encoding="utf-8")
    return rc_path


def start_login(timeout: int = DEFAULT_TIMEOUT) -> dict:
    request = build_request("/openapi/auth/login/start", {}, api_key="")
    return open_json(request, timeout=timeout)


def get_login_result(login_token: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    request = build_request(
        "/openapi/auth/login/result",
        {"login_token": login_token},
        api_key="",
    )
    return open_json(request, timeout=timeout)


def poll_login_result(
    login_token: str,
    timeout: int = DEFAULT_TIMEOUT,
    poll_interval: int = DEFAULT_LOGIN_POLL_INTERVAL,
) -> dict:
    start_time = time.time()
    while True:
        result = get_login_result(login_token=login_token, timeout=timeout)
        status = result.get("status", "")
        if status in {"success", "failed"}:
            return result
        if time.time() - start_time >= timeout:
            result.setdefault("status", "failed")
            result.setdefault("message", "Polling timed out before login completed.")
            return result
        time.sleep(max(poll_interval, 1))


def get_api_key(
    timeout: int = DEFAULT_TIMEOUT,
    poll_interval: int = DEFAULT_LOGIN_POLL_INTERVAL,
    shell_env: str | None = None,
    home: Path | None = None,
    auto_login: bool = True,
) -> str:
    env_value = os.environ.get(API_KEY_ENV_NAME, "").strip()
    if env_value:
        return env_value

    persisted_value = _read_api_key_from_shell_rc(shell_env=shell_env, home=home)
    if persisted_value:
        os.environ[API_KEY_ENV_NAME] = persisted_value
        return persisted_value

    if not auto_login:
        raise SystemExit(f"Missing required environment variable: {API_KEY_ENV_NAME}")

    login_state = start_login(timeout=timeout)
    login_token = str(login_state.get("login_token", "") or "").strip()
    if login_state.get("status") != "ok" or not login_token:
        raise SystemExit(login_state.get("message", "Failed to start login flow."))

    login_url = f"{get_base_url()}/login?login_token={login_token}"
    print(
        "No API key found. Please open this URL and complete login:\n"
        f"{login_url}",
        file=sys.stderr,
    )

    result = poll_login_result(login_token, timeout=timeout, poll_interval=poll_interval)
    if result.get("status") != "success":
        raise SystemExit(result.get("message", "Login did not complete successfully."))

    api_key = str(result.get("api_key", "") or "").strip()
    if not api_key:
        raise SystemExit("Login completed without returning an API key.")

    rc_path = persist_api_key(api_key, shell_env=shell_env, home=home)
    os.environ[API_KEY_ENV_NAME] = api_key
    print(f"Stored {API_KEY_ENV_NAME} in {rc_path}", file=sys.stderr)
    return api_key


def get_marketing_payment_url() -> str:
    return MARKETING_PAYMENT_URL


def build_request(path: str, payload: dict, api_key: str) -> urllib.request.Request:
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return urllib.request.Request(
        url=f"{get_base_url()}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
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
    form_id: str = "",
    form_data: dict | None = None,
) -> dict:
    api_key = get_api_key(timeout=timeout)
    submit_payload = {}
    if message:
        submit_payload["message"] = message
    if conversation_id:
        submit_payload["conversation_id"] = conversation_id
    if project_ids:
        submit_payload["project_id"] = [item for item in project_ids if item]
    if skill_ids:
        submit_payload["skill_id"] = [item for item in skill_ids if item]
    if form_id:
        submit_payload["form_id"] = form_id
    if form_data:
        submit_payload["form_data"] = form_data

    submit_request = build_request("/openapi/agent/chat_submit", submit_payload, api_key)
    return open_json(submit_request, timeout=timeout)


def get_chat_result(
    conversation_id: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    api_key = get_api_key(timeout=timeout)
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
