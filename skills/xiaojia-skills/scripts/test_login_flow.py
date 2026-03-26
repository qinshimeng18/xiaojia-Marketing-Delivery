#!/usr/bin/env python3
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common


class LoginFlowTests(unittest.TestCase):
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

            persisted_path = _common.persist_api_key("new-key", shell_env="/bin/zsh", home=home)

            updated_text = rc_path.read_text(encoding="utf-8")

        self.assertEqual(persisted_path, rc_path)
        self.assertIn('export JUSTAI_OPENAPI_API_KEY="new-key"', updated_text)
        self.assertEqual(updated_text.count("JUSTAI_OPENAPI_API_KEY"), 1)

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
                process_env_value = os.environ["JUSTAI_OPENAPI_API_KEY"]

        self.assertEqual(api_key, "fresh-key")
        self.assertEqual(process_env_value, "fresh-key")
        self.assertIn('export JUSTAI_OPENAPI_API_KEY="fresh-key"', persisted_text)
        start_login.assert_called_once_with(timeout=5)
        poll_login_result.assert_called_once_with("token-123", timeout=5, poll_interval=1)


if __name__ == "__main__":
    unittest.main()
