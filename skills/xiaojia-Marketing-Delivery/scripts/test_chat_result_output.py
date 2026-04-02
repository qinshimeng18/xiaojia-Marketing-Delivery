#!/usr/bin/env python3
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chat_result


class ChatResultOutputTests(unittest.TestCase):
    def test_main_adds_web_url_to_completed_result(self):
        stdout_buffer = io.StringIO()
        completed_result = {
            "status": "completed",
            "conversation_id": "c7d34bf0-0bd5-4b2c-acd2-5dc2adf729b9",
            "result": {"ok": True},
        }

        with patch.object(
            sys,
            "argv",
            ["chat_result.py", "--conversation-id", "c7d34bf0-0bd5-4b2c-acd2-5dc2adf729b9"],
        ), patch.object(
            chat_result,
            "poll_chat_result",
            return_value=completed_result,
        ), patch(
            "sys.stdout",
            stdout_buffer,
        ):
            exit_code = chat_result.main()

        self.assertEqual(exit_code, 0)
        output = stdout_buffer.getvalue()
        self.assertIn(
            '"web_url": "https://justailab.com/pages/agent/preview?conversation_id=c7d34bf0-0bd5-4b2c-acd2-5dc2adf729b9"',
            output,
        )


if __name__ == "__main__":
    unittest.main()
