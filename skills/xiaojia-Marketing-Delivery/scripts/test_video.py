import contextlib
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import video


class VideoApprovalTests(unittest.TestCase):
    def run_approve(self, response=None, error=None):
        output = io.StringIO()
        args = ['video.py', 'approve', '--conversation-id', 'c1', '--action-id', 'a1', '--revision', '2', '--confirm']
        with patch('sys.argv', args), patch('video.get_api_key', return_value='test'), patch('video.open_json', return_value=response, side_effect=error) as call, contextlib.redirect_stdout(output):
            code = video.main()
        self.assertEqual(call.call_count, 1)
        return code, json.loads(output.getvalue())

    def test_timeout_means_unknown_not_failed(self):
        code, result = self.run_approve(error=TimeoutError())
        self.assertEqual(code, 2)
        self.assertEqual(result['submission_status'], 'unknown')
        self.assertEqual(result['conversation_id'], 'c1')

    def test_accepted_keeps_job(self):
        code, result = self.run_approve(response={'status': 'accepted', 'job_id': 'j1'})
        self.assertEqual(code, 0)
        self.assertEqual(result['job_id'], 'j1')

    def test_http_rejection_not_hidden(self):
        with self.assertRaises(HTTPError):
            self.run_approve(error=HTTPError('https://example.org', 403, 'forbidden', {}, None))
