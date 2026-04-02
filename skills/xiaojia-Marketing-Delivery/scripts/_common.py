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
DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_BASE_URL = "https://justailab.com"
DEFAULT_LOGIN_POLL_INTERVAL = 2
MARKETING_PAYMENT_URL = "https://justailab.com/pages/agent/preview"
API_KEY_ENV_NAME = "JUSTAI_OPENAPI_API_KEY"
BASE_URL_ENV_NAME = "JUSTAI_OPENAPI_BASE_URL"
TIMEOUT_ENV_NAME = "JUSTAI_OPENAPI_TIMEOUT"
DEFAULT_CONFIG_FILE_NAMES = (
    "~/.codex/justai-openapi-chat.json",
    "~/.claude/justai-openapi-chat.json",
)
API_KEY_EXPORT_RE = re.compile(
    rf'^\s*export\s+{API_KEY_ENV_NAME}=(?P<quote>["\']?)(?P<value>.*?)(?P=quote)\s*$'
)
BASE_URL_EXPORT_RE = re.compile(
    rf'^\s*export\s+{BASE_URL_ENV_NAME}=(?P<quote>["\']?)(?P<value>.*?)(?P=quote)\s*$'
)
TIMEOUT_EXPORT_RE = re.compile(
    rf'^\s*export\s+{TIMEOUT_ENV_NAME}=(?P<quote>["\']?)(?P<value>.*?)(?P=quote)\s*$'
)


def _candidate_config_paths(home: Path | None = None) -> list[Path]:
    paths = []
    explicit_path = os.environ.get("JUSTAI_OPENAPI_CONFIG", "").strip()
    if explicit_path:
        if explicit_path.startswith("~/") and home is not None:
            paths.append(_get_home(home) / explicit_path[2:])
        else:
            paths.append(Path(explicit_path).expanduser())

    home_dir = _get_home(home)
    for raw_path in DEFAULT_CONFIG_FILE_NAMES:
        if raw_path.startswith("~/"):
            path = home_dir / raw_path[2:]
        else:
            path = Path(raw_path)
            if not path.is_absolute():
                path = home_dir / path
        paths.append(path)
    return paths


def _load_local_config(home: Path | None = None) -> tuple[dict, Path | None]:
    for path in _candidate_config_paths(home=home):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Failed to read local config: {path} ({exc})")
        if isinstance(data, dict):
            return data, path
    return {}, None


def _write_export_line(lines: list[str], pattern: re.Pattern[str], export_line: str) -> list[str]:
    replaced = False
    updated_lines = []
    for line in lines:
        if pattern.match(line):
            if not replaced:
                updated_lines.append(export_line)
                replaced = True
            continue
        updated_lines.append(line)

    if not replaced:
        if updated_lines and not updated_lines[-1].endswith("\n"):
            updated_lines[-1] = f"{updated_lines[-1]}\n"
        updated_lines.append(export_line)
    return updated_lines


def _resolve_value(
    env_name: str,
    config_key: str,
    home: Path | None = None,
    default: str = "",
) -> str:
    env_value = os.environ.get(env_name, "").strip()
    if env_value:
        return env_value

    config, _ = _load_local_config(home=home)
    config_value = str(config.get(config_key, "") or "").strip()
    if config_value:
        return config_value

    return default


def get_base_url() -> str:
    return _resolve_value(BASE_URL_ENV_NAME, "base_url", default=DEFAULT_BASE_URL).rstrip("/")


def get_default_timeout(home: Path | None = None) -> int:
    raw_value = _resolve_value(TIMEOUT_ENV_NAME, "timeout", home=home, default=str(DEFAULT_TIMEOUT))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{TIMEOUT_ENV_NAME} must be an integer.") from exc
    return max(value, DEFAULT_TIMEOUT)


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


def persist_local_config(
    api_key: str,
    base_url: str | None = None,
    timeout: int | None = None,
    home: Path | None = None,
) -> Path:
    path = _candidate_config_paths(home=home)[0]
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    existing_config, _ = _load_local_config(home=home)
    config = dict(existing_config)
    config["api_key"] = api_key
    config["base_url"] = (base_url or get_base_url()).rstrip("/")
    if timeout is not None:
        config["timeout"] = max(int(timeout), DEFAULT_TIMEOUT)
    elif "timeout" not in config:
        config["timeout"] = DEFAULT_TIMEOUT

    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def persist_api_key(
    api_key: str,
    shell_env: str | None = None,
    home: Path | None = None,
    base_url: str | None = None,
    timeout: int | None = None,
) -> tuple[Path, Path]:
    rc_path = _get_primary_shell_rc_path(shell_env=shell_env, home=home)
    escaped_api_key = api_key.replace("\\", "\\\\").replace('"', '\\"')
    escaped_base_url = (base_url or get_base_url()).replace("\\", "\\\\").replace('"', '\\"')
    persisted_timeout = max(int(timeout if timeout is not None else get_default_timeout(home=home)), DEFAULT_TIMEOUT)
    export_line = f'export {API_KEY_ENV_NAME}="{escaped_api_key}"\n'
    base_url_line = f'export {BASE_URL_ENV_NAME}="{escaped_base_url}"\n'
    timeout_line = f'export {TIMEOUT_ENV_NAME}="{persisted_timeout}"\n'

    if rc_path.exists():
        lines = rc_path.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = []

    updated_lines = _write_export_line(lines, API_KEY_EXPORT_RE, export_line)
    updated_lines = _write_export_line(updated_lines, BASE_URL_EXPORT_RE, base_url_line)
    updated_lines = _write_export_line(updated_lines, TIMEOUT_EXPORT_RE, timeout_line)

    rc_path.write_text("".join(updated_lines), encoding="utf-8")
    config_path = persist_local_config(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        home=home,
    )
    return rc_path, config_path


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

    config, _ = _load_local_config(home=home)
    config_value = str(config.get("api_key", "") or "").strip()
    if config_value:
        os.environ[API_KEY_ENV_NAME] = config_value
        base_url_value = str(config.get("base_url", "") or "").strip()
        if base_url_value:
            os.environ[BASE_URL_ENV_NAME] = base_url_value
        timeout_value = str(config.get("timeout", "") or "").strip()
        if timeout_value:
            os.environ[TIMEOUT_ENV_NAME] = timeout_value
        return config_value

    persisted_value = _read_api_key_from_shell_rc(shell_env=shell_env, home=home)
    if persisted_value:
        os.environ[API_KEY_ENV_NAME] = persisted_value
        persist_local_config(
            api_key=persisted_value,
            timeout=timeout,
            home=home,
        )
        return persisted_value

    if not auto_login:
        checked_paths = ", ".join(str(path) for path in _candidate_config_paths(home=home))
        raise SystemExit(
            "No login information found. Please complete login first. "
            f"Also checked local config ({checked_paths})."
        )

    login_state = start_login(timeout=timeout)
    login_token = str(login_state.get("login_token", "") or "").strip()
    if login_state.get("status") != "ok" or not login_token:
        raise SystemExit(login_state.get("message", "Failed to start login flow."))

    login_url = f"{get_base_url()}/login?login_token={login_token}"
    print(
        "No login information found yet. Please open this URL and complete login:\n"
        f"{login_url}",
        file=sys.stderr,
    )

    result = poll_login_result(login_token, timeout=timeout, poll_interval=poll_interval)
    if result.get("status") != "success":
        raise SystemExit(result.get("message", "Login did not complete successfully."))

    api_key = str(result.get("api_key", "") or "").strip()
    if not api_key:
        raise SystemExit("Login completed without returning an API key.")

    base_url = get_base_url()
    rc_path, config_path = persist_api_key(
        api_key,
        shell_env=shell_env,
        home=home,
        base_url=base_url,
        timeout=timeout,
    )
    os.environ[API_KEY_ENV_NAME] = api_key
    os.environ[BASE_URL_ENV_NAME] = base_url
    os.environ[TIMEOUT_ENV_NAME] = str(timeout)
    print(f"Saved login information in {rc_path} and {config_path}", file=sys.stderr)
    return api_key


def get_marketing_payment_url() -> str:
    return MARKETING_PAYMENT_URL


def build_marketing_conversation_url(conversation_id: str) -> str:
    return f"{get_marketing_payment_url()}?conversation_id={conversation_id}"


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
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
    poll_interval: int = 2,
    progress_callback=None,
) -> dict:
    start_time = time.time()
    while True:
        result = get_chat_result(conversation_id=conversation_id, timeout=request_timeout)
        status = result.get("status", "")
        if status in {"completed", "failed"}:
            return result
        if callable(progress_callback):
            progress_callback(result)
        if time.time() - start_time >= timeout:
            result.setdefault("message", "Polling timed out before task completed.")
            return result
        time.sleep(max(poll_interval, 1))
