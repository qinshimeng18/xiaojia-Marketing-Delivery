#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common


class LoginFlowTests(unittest.TestCase):
    def test_get_api_key_reads_existing_key_from_local_config_when_env_missing(self):
        with TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)
            config_path = home / "justai-openapi-chat.json"
            config_path.write_text(
                json.dumps(
                    {
                        "base_url": "https://config.example.com",
                        "api_key": "config-key",
                        "timeout": 300,
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "SHELL": "/bin/zsh",
                    "JUSTAI_OPENAPI_CONFIG": str(config_path),
                },
                clear=True,
            ):
                api_key = _common.get_api_key(home=home, auto_login=False)
                base_url = _common.get_base_url()
                timeout = _common.get_default_timeout()

        self.assertEqual(api_key, "config-key")
        self.assertEqual(base_url, "https://config.example.com")
        self.assertEqual(timeout, 300)

    def test_get_default_timeout_clamps_too_small_config_values(self):
        with TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)
            config_path = home / "justai-openapi-chat.json"
            config_path.write_text(
                json.dumps(
                    {
                        "base_url": "https://config.example.com",
                        "api_key": "config-key",
                        "timeout": 5,
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "SHELL": "/bin/zsh",
                    "JUSTAI_OPENAPI_CONFIG": str(config_path),
                },
                clear=True,
            ):
                timeout = _common.get_default_timeout()

        self.assertEqual(timeout, _common.DEFAULT_TIMEOUT)

    def test_get_api_key_reads_existing_key_from_shell_rc_when_env_missing(self):
        with TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)
            (home / ".zshrc").write_text(
                'export JUSTAI_OPENAPI_API_KEY="persisted-key"\n',
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"SHELL": "/bin/zsh"}, clear=True):
                api_key = _common.get_api_key(home=home, auto_login=False)

        self.assertEqual(api_key, "persisted-key")

    def test_persist_api_key_updates_existing_export_line(self):
        with TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)
            rc_path = home / ".zshrc"
            rc_path.write_text(
                'export JUSTAI_OPENAPI_API_KEY="old-key"\nexport PATH="/usr/bin"\n',
                encoding="utf-8",
            )

            persisted_path, config_path = _common.persist_api_key(
                "new-key",
                shell_env="/bin/zsh",
                home=home,
            )

            updated_text = rc_path.read_text(encoding="utf-8")
            config_data = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(persisted_path, rc_path)
        self.assertIn('export JUSTAI_OPENAPI_API_KEY="new-key"', updated_text)
        self.assertEqual(updated_text.count("JUSTAI_OPENAPI_API_KEY"), 1)
        self.assertEqual(config_data["api_key"], "new-key")

    def test_get_api_key_auto_login_persists_key_and_sets_process_env(self):
        with TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)

            with patch.dict(os.environ, {"SHELL": "/bin/zsh"}, clear=True), patch(
                "sys.stderr"
            ), patch.object(
                _common,
                "start_login",
                return_value={"status": "ok", "login_token": "token-123", "expires_in": 300},
            ) as start_login, patch.object(
                _common,
                "poll_login_result",
                return_value={"status": "success", "api_key": "fresh-key"},
            ) as poll_login_result:
                api_key = _common.get_api_key(timeout=5, poll_interval=1, home=home)
                persisted_text = (home / ".zshrc").read_text(encoding="utf-8")
                config_data = json.loads((home / ".codex" / "justai-openapi-chat.json").read_text(encoding="utf-8"))
                process_env_value = os.environ["JUSTAI_OPENAPI_API_KEY"]

        self.assertEqual(api_key, "fresh-key")
        self.assertEqual(process_env_value, "fresh-key")
        self.assertIn('export JUSTAI_OPENAPI_API_KEY="fresh-key"', persisted_text)
        self.assertEqual(config_data["api_key"], "fresh-key")
        start_login.assert_called_once_with(timeout=5)
        poll_login_result.assert_called_once_with("token-123", timeout=5, poll_interval=1)

    def test_auto_login_persists_api_key_to_local_config(self):
        with TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)
            config_path = home / "justai-openapi-chat.json"

            with patch.dict(
                os.environ,
                {
                    "SHELL": "/bin/zsh",
                    "JUSTAI_OPENAPI_CONFIG": str(config_path),
                },
                clear=True,
            ), patch("sys.stderr"), patch.object(
                _common,
                "start_login",
                return_value={"status": "ok", "login_token": "token-123", "expires_in": 300},
            ), patch.object(
                _common,
                "poll_login_result",
                return_value={"status": "success", "api_key": "fresh-key"},
            ):
                _common.get_api_key(timeout=5, poll_interval=1, home=home)
                config_data = json.loads(config_path.read_text(encoding="utf-8"))

        self.assertEqual(config_data["api_key"], "fresh-key")

    def test_poll_chat_result_emits_progress_callback_for_running_status(self):
        states = [
            {"status": "running", "branch": "generate_notes"},
            {"status": "completed", "branch": "generate_notes", "result": {"ok": True}},
        ]
        seen = []

        def fake_get_chat_result(conversation_id: str, timeout: int = 300):
            return states.pop(0)

        with patch.object(_common, "get_chat_result", side_effect=fake_get_chat_result), patch.object(
            _common.time,
            "sleep",
        ):
            result = _common.poll_chat_result(
                conversation_id="cvt_test",
                timeout=300,
                poll_interval=20,
                progress_callback=seen.append,
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(seen, [{"status": "running", "branch": "generate_notes"}])

    def test_poll_chat_result_uses_separate_request_timeout_from_poll_timeout(self):
        seen_request_timeouts = []

        def fake_get_chat_result(conversation_id: str, timeout: int = 300):
            seen_request_timeouts.append(timeout)
            return {"status": "running", "branch": "generate_notes"}

        with patch.object(_common, "get_chat_result", side_effect=fake_get_chat_result), patch.object(
            _common.time,
            "time",
            side_effect=[0, 6],
        ), patch.object(
            _common.time,
            "sleep",
        ):
            result = _common.poll_chat_result(
                conversation_id="cvt_test",
                timeout=5,
                poll_interval=2,
            )

        self.assertEqual(seen_request_timeouts, [_common.DEFAULT_REQUEST_TIMEOUT])
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["message"], "Polling timed out before task completed.")


if __name__ == "__main__":
    unittest.main()
