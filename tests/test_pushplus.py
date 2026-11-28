import unittest
from unittest.mock import patch

import requests

from checkin import Config, PushPlusBackend, PushService, Report


class PushPlusTests(unittest.TestCase):
    def setUp(self):
        self.report = Report.failed("配置错误\n请更新 Cookie")
        self.backend = PushPlusBackend("private-test-token")

    @patch("checkin.requests.post")
    def test_submits_report_as_json_with_timeout(self, post):
        post.return_value.json.return_value = {"code": 200, "data": "message-id"}
        self.assertTrue(self.backend.send(self.report))
        post.assert_called_once_with(
            "https://www.pushplus.plus/send",
            json={
                "token": "private-test-token",
                "title": self.report.title,
                "content": "配置错误\n请更新 Cookie",
                "template": "txt",
            },
            timeout=15,
        )
        post.return_value.raise_for_status.assert_called_once()

    @patch("checkin.requests.post")
    def test_rejected_or_malformed_results_do_not_leak_response(self, post):
        for payload in ({"code": 400, "msg": self.backend.token}, [], None, {}, {"code": "200"}):
            with self.subTest(payload=payload):
                post.return_value.json.return_value = payload
                with self.assertLogs(level="ERROR") as logs:
                    self.assertFalse(self.backend.send(self.report))
                self.assertNotIn(self.backend.token, "".join(logs.output))

    @patch("checkin.requests.post")
    def test_request_errors_and_non_json_response_are_contained(self, post):
        for error in (requests.Timeout(self.backend.token), requests.ConnectionError(self.backend.token)):
            with self.subTest(error=type(error).__name__):
                post.side_effect = error
                with self.assertLogs(level="ERROR") as logs:
                    self.assertFalse(self.backend.send(self.report))
                self.assertNotIn(self.backend.token, "".join(logs.output))
        post.side_effect = None
        post.return_value.raise_for_status.side_effect = requests.HTTPError(self.backend.token)
        self.assertFalse(self.backend.send(self.report))
        post.return_value.raise_for_status.side_effect = None
        post.return_value.json.side_effect = ValueError("not JSON")
        self.assertFalse(self.backend.send(self.report))

    @patch("checkin.requests.post")
    def test_missing_or_blank_token_skips_notification(self, post):
        for token in (None, "", "  "):
            env = {} if token is None else {"PUSHPLUS_TOKEN": token}
            self.assertFalse(PushService(Config(env)).send(self.report))
        post.assert_not_called()

    @patch("checkin.requests.post")
    def test_token_loaded_even_when_cookie_configuration_fails(self, post):
        post.return_value.json.return_value = {"code": 200}
        config = Config({"PUSHPLUS_TOKEN": " token ", "GLADOS_COOKIES": "invalid-json"})
        self.assertTrue(config.load_error)
        self.assertEqual(config.pushplus_token, "token")
        self.assertTrue(PushService(config).send(Report.failed(config.load_error)))
        post.assert_called_once()

    @patch("checkin.requests.post")
    def test_old_secrets_do_not_enable_pushplus(self, post):
        config = Config({"PUSHDEER_SENDKEY": "old-key", "SERVERCHAN_SENDKEY": "old-key"})
        self.assertFalse(PushService(config).send(self.report))
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
